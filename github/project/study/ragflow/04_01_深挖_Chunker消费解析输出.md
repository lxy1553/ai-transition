# 深挖：Chunker 消费 DeepDoc 解析输出（rag/flow/chunker/token_chunker.py）

> 这是主干④的展开——深挖 03_01/03_02 讲完"解析器怎么产出"，这里讲**分块器怎么消费解析输出**：
> 表格 HTML、图片 VLM 描述、PDF 坐标、父/子块结构，是怎么一步步变成最终写入文档库的 chunk。
> 核心问题：**一个"带版面结构的解析结果"怎么变成"可检索的 chunk 集合"**。

- 源码位置：`github/project/ragflow/rag/flow/chunker/token_chunker.py`（TokenChunker）+ `title_chunker/`（TitleChunker）+ `rag/flow/parser/utils.py`（VLM 增强）
- 上游：flow Parser 组件（`rag/flow/parser/parser.py`）；下游：Tokenizer 组件 → executor 落库
- 同名 Go 移植版：`internal/ingestion/component/chunker/`（注释里多处说明与 Go 做 parity）

---

## 三问

- **Q1 解决什么问题**：解析器输出的是一堆"带版面标签的文本块 + 表格 + 图片"，还不是可检索单元。Chunker 决定**哪些文字合一个 chunk、表格/图片怎么变成 chunk、chunk 之间怎么建立父子关系**。
- **Q2 数据流哪一环**：离线链路第③环——上游 flow Parser，下游 Tokenizer（加向量）+ executor（落库）。
- **Q3 删掉会怎样**：解析结果直接全塞给 embedding——检索粒度失控（一段=一页或一文件）、表格图片知识丢失、无父块可回退。

---

## 〇、重要更正：`【表格】/【图片】` 标记是旧版，当前用 `doc_type_kwd`

> 网上很多 RAGFlow 教程讲"分块后文本会包上 `【表格】...【表格】` / `【图片】...【图片】` 标记"——**这是老版本**。
> 我在当前代码库 `git grep` 了 `【表格】`，**全库无匹配，git 历史也无该格式的提交**。
> **当前机制**：解析器给每个块打 `doc_type_kwd` 字段（`"text"` / `"table"` / `"image"`），表格 HTML / 图片 VLM 描述**直接进 chunk 的 `text` 字段**，图片用 `img_id` 关联。媒体块的上下文通过 `context_above`/`context_below` 拼接。

---

## 一、数据流转总览：解析器输出 → 分块 chunk

```
DeepDoc 解析器 (deepdoc/parser/pdf_parser.py)
  │  图片: (img, [caption_txt])                        (pdf_parser.py:1469)
  │  表格: (img, construct_table(html=True))           (pdf_parser.py:1482)  ← return_html=True 时是 HTML 表格
  │  DOCX/Excel/Markdown: (text, image, html) / sections
  ▼
flow Parser 组件 (rag/flow/parser/parser.py)
  │  归一化 bbox → {text, layout_type, doc_type_kwd, image, positions}   (parser.py:747-770)
  │  layout=="table" → doc_type_kwd="table"; figure/image → "image"
  │  ★ enhance_media_sections_with_vision(): 图片/表格用 VLM 生成描述, 追加进 text  (parser/utils.py:210-211)
  │  output_format = "json" | "markdown" | "text" | "html"
  ▼
TokenChunker (rag/flow/chunker/token_chunker.py)
  │  _build_json_chunks: doc_type_kwd → ck_type{text|table|image}         (119-172)
  │    text 块按 delimiter 正则切分; 表格/图片单独成块并保留 img_id + PDF 坐标
  │  _attach_context_to_media_chunks: 给 table/image 填 context_above/below (190-230)
  │  children_delimiters: _split_chunk_docs_by_children → 子块打 mom       (363-385)
  │  _finalize_json_chunks: 去 @@..## 坐标标签, 组最终 doc                 (334-360)
  ▼
（可选）TitleChunker (rag/flow/chunker/title_chunker/)
  │  按标题层级切块; 叶子标题单独成 chunk
  ▼
Tokenizer 组件 (rag/flow/tokenizer/tokenizer.py)
  │  title_tks/content_ltks + 生成 q_{dim}_vec + position_int/page_num_int
  ▼
executor 落库 (rag/svr/task_executor.py:1306 / chunk_service.py:272)
  │  text → content_with_weight
  │  mom → 母块: mom_id=xxhash(mom), content_with_weight=mom, available_int=0
  ▼
ES/Infinity: 子块(可检索) + 母块(不可检索, 供父级召回)
```

---

## 二、媒体块识别 `_build_json_chunks`（token_chunker.py:119-172）

```python
def _build_json_chunks(json_result, delimiter_pattern):
    chunks = []
    for item in json_result:
        # ① doc_type_kwd → chunk 类型：table/image/text
        doc_type = str(item.get("doc_type_kwd") or "").strip().lower()
        if doc_type == "table":   ck_type = "table"
        elif doc_type == "image": ck_type = "image"
        else:                     ck_type = "text"

        text = item.get("text")
        if not isinstance(text, str):
            text = item.get("content_with_weight")   # 兼容旧字段名
        # ★ PDF 坐标保留为内部预览字段（不对外泄漏两种坐标格式）
        preview_positions = extract_pdf_positions(item)
        img_id = item.get("img_id")

        if ck_type == "text":
            # 文本块：按 delimiter 正则切段
            text_segments = _split_text_by_pattern(text, delimiter_pattern) if delimiter_pattern else [text]
            for segment in text_segments:
                if not segment or not segment.strip(): continue
                chunks.append({"text": segment, "doc_type_kwd": "text", "ck_type": "text",
                               PDF_POSITIONS_KEY: deepcopy(preview_positions),
                               "tk_nums": num_tokens_from_string(segment)})
            continue

        # 表格/图片块：单独成一个 chunk，携带 img_id + 预留给 context 的字段
        chunks.append({"text": text or "", "doc_type_kwd": ck_type, "ck_type": ck_type,
                       "img_id": img_id, PDF_POSITIONS_KEY: deepcopy(preview_positions),
                       "tk_nums": num_tokens_from_string(text or ""),
                       "context_above": "", "context_below": ""})
    return chunks
```

**作用（关键）**：
- **媒体块 = 独立 chunk**：表格/图片不掺进正文文本流，单独成 chunk——下游能对它们单独做 embedding、单独检索、单独附上下文。
- **`text` 里已经有表格 HTML / 图描述**（上游 Parser 拼好的），chunker 直接透传。
- **`PDF_POSITIONS_KEY`（`_pdf_positions`）内部暂存**：坐标是内部字段，最终才转成公共坐标格式（避免泄漏两种坐标格式）。

---

## 三、图片 VLM 描述怎么进 `text`（rag/flow/parser/utils.py:162-213）

```python
def enhance_media_sections_with_vision(sections, tenant_id, vlm_conf=None, callback=None, lang="English"):
    # ① 解析 VLM 模型配置（tenant 默认视觉模型）→ LLMBundle
    vision_model = LLMBundle(tenant_id, vision_model_config, lang=lang)

    for item in sections:
        if item.get("doc_type_kwd") not in {"image", "table"}: continue   # 只处理图片/表格
        if item.get("image") is None: continue
        text = item.get("text") or ""
        # ② 用 VisionFigureParser 调 VLM 看图生成描述
        parsed = VisionFigureParser(
            vision_model=vision_model,
            figures_data=[((item["image"], [""]), [(0, 0, 0, 0, 0)])],
            context_size=0, lang=lang,
        )(callback=callback)
        parsed_text = str(parsed[0][0][1] or "").strip()
        # ③ ★ VLM 描述拼回 item 的 text
        if parsed_text:
            item["text"] = f"{text}\n{parsed_text}" if text else parsed_text
    return sections
```

**作用（关键）**：**图片知识进 RAG** 的地方——版面识别出"这是图"，图里有没有字、表达什么，全靠 VLM 看图描述，然后把描述拼进 `text`。这样下游 embedding/检索能命中图片内容。**这是"图片型知识"进入知识库的唯一通道**。

> 坑：`doc_type_kwd` 必须是 `image`/`table` 且 `image` 不为空才走 VLM；VLM 配置解析失败会静默返回原 sections（不阻塞主流程）——**增强是可选的后处理，解析失败不致命**。

---

## 四、媒体块上下文 `_attach_context_to_media_chunks`（token_chunker.py:190-230）

```python
def _attach_context_to_media_chunks(chunks, table_context_size, image_context_size):
    for i, chunk in enumerate(chunks):
        if chunk["ck_type"] not in {"table", "image"}: continue     # 只处理媒体块
        context_size = image_context_size if chunk["ck_type"] == "image" else table_context_size
        if context_size <= 0: continue                              # 参数=0 表示不附加

        remain_above, remain_below = context_size, context_size
        parts_above, parts_below = [], []

        prev = i - 1                                                # ① 向前扫描相邻 text 块
        while prev >= 0 and remain_above > 0:
            prev_chunk = chunks[prev]
            if prev_chunk["ck_type"] == "text":
                if prev_chunk["tk_nums"] >= remain_above:           # 超过预算 → 按句子截取
                    parts_above.insert(0, _take_sentences(prev_chunk["text"], remain_above, from_end=True))
                    remain_above = 0; break
                parts_above.insert(0, prev_chunk["text"])           # 预算够 → 整块取走
                remain_above -= prev_chunk["tk_nums"]
            prev -= 1
        # ② 同理向后扫描 after，取 parts_below ...
        chunk["context_above"] = "".join(parts_above)
        chunk["context_below"] = "".join(parts_below)
```

```python
def _take_sentences(text, need_tokens, from_end=False):
    # 按句子边界切分，从头/尾累加直到达到 token 预算
    texts = re.split(SENTENCE_BOUNDARY_PATTERN, text or "", flags=re.DOTALL)
    ...
    for sentence in sentences:
        collected += sentence
        if num_tokens_from_string(collected) >= need_tokens: break
    return collected
```

**作用（关键）**：表格/图片 chunk 没有上下文读不懂（"这张表是什么的表"）。**向前/向后各取 `table_context_size` / `image_context_size` 个 token 的相邻文本**（按句子边界，不截半句），存进 `context_above`/`context_below`——最终拼接进 `text`，让媒体 chunk 的 embedding 带上上下文语义。对应主干④说的"表格上下文"。

---

## 五、最终组装 `_finalize_json_chunks`（token_chunker.py:334-360）

```python
def _finalize_json_chunks(chunks):
    docs = []
    for chunk in chunks:
        # ① ★ 去坐标标签：context_above + text + context_below 拼起来后 remove_tag
        #    坐标标签 @@页码\tx y## 永远不会进入 embedding/index（已存结构化字段）
        text = remove_tag((chunk.get("context_above") or "") + (chunk.get("text") or "") + (chunk.get("context_below") or ""))
        if not text.strip(): continue
        doc = {"text": text, "doc_type_kwd": chunk.get("doc_type_kwd", "text")}
        if chunk.get(PDF_POSITIONS_KEY): doc[PDF_POSITIONS_KEY] = deepcopy(chunk[PDF_POSITIONS_KEY])
        if chunk.get("mom"): doc["mom"] = chunk["mom"]        # ★ 父文本透传
        if chunk.get("img_id"): doc["img_id"] = chunk["img_id"]
        docs.append(finalize_pdf_chunk(doc))                   # ② 坐标转公共字段 position_int/page_num_int
    return docs
```

**作用**：
- **媒体上下文在此刻拼进 `text`**（`context_above + text + context_below`）。
- **坐标标签剥离**：解析器打的 `@@页码\tx y w h##` 标签在 `remove_tag`（正则 `@@[\t0-9.-]+?##`）剥掉，坐标数据已经在 `_pdf_positions` 里，`finalize_pdf_chunk` 转成 `position_int`/`page_num_int`/`top_int` 三个 ES 字段——**文本干净，坐标结构化保留**（前端引用定位的数据）。
- `q_{dim}_vec` 不在这里产生，是下游 Tokenizer 组件加的。

---

## 六、父/子块结构：`mom` 由 chunker 打，母块由 executor 建

### ① chunker 打 `mom`：`_split_chunk_docs_by_children`（token_chunker.py:363-385）

```python
def _split_chunk_docs_by_children(chunks, pattern):
    # 用 children_delimiters（二级分隔符）对已合并的文本块二次切分
    for chunk in chunks:
        if chunk.get("doc_type_kwd", "text") != "text":   # 媒体块不切
            docs.append(chunk); continue
        split_texts = _split_text_by_pattern(chunk.get("text", ""), pattern)
        mom = chunk.get("text", "").removeprefix("\n")    # ★ 父文本 = 整段未切的内容
        for text in split_texts:
            child = deepcopy(chunk)
            child["mom"] = mom                            # ★ 子块记录父文本
            child["text"] = text
            docs.append(child)
    return docs
```

纯文本路径（无 children_delimiters）也会设：`docs.append({"text": text, "mom": c.removeprefix("\n")})`（:431）。

### ② executor 建母块：`task_executor.py:1306-1322` / `chunk_service.py:272-306`

```python
mom = ck.get("mom") or ck.get("mom_with_weight") or ""   # mom_with_weight 是老路径字段名
if not mom: continue
id = xxhash.xxh64(mom.encode("utf-8")).hexdigest()       # ★ 内容哈希 → 稳定母块 ID
ck["mom_id"] = id                                        # 子块记录父块 ID
if id in mother_ids: continue
mother_ids.add(id)
mom_ck = copy.deepcopy(ck)
mom_ck["id"] = id
mom_ck["content_with_weight"] = mom                      # 母块存整段父文本
mom_ck["available_int"] = 0                              # ★ 母块不可检索
# 只保留白名单字段（id/content_with_weight/doc_id/docnm_kwd/kb_id/position_int...）
```

**作用（关键）**：**父子文档 = 两个字段 + 两条写入**——
- chunker 用二级分隔符把"大块"切成"小块"，**小块带 `mom`（父文本）**；
- executor 落库时对每个 `mom` 建**母块**（`mom_id = xxhash(内容)` 幂等），母块 `available_int=0` **不参与检索**；
- 检索命中子块 → 取回母块的完整上下文喂 LLM（"检索用小块、喂 LLM 用大块"的落库实现，对应 08 索引写入的 `insert_chunks`）。

**`mom_with_weight` 是旧路径名字**（`rag/nlp/__init__.py` 的 `tokenize_*` 设置），executor 用 `ck.get("mom") or ck.get("mom_with_weight")` 兼容两条路径。

---

## 七、`TokenChunkerParam` 参数（token_chunker.py:49-90）

```python
class TokenChunkerParam(ProcessParamBase):
    def __init__(self):
        super().__init__()
        self.delimiter_mode = "delimiter"    # "delimiter"(按分隔符) | "one"(整篇一个chunk)
        self.chunk_token_size = 512          # 对应旧名 token_num
        self.delimiters = ["\n"]             # 主分隔符，支持 `反引号` 包裹的自定义分隔符
        self.overlapped_percent = 0          # ★ 重叠比例 [0,1)，旧的固定重叠 token 数已废弃
        self.children_delimiters = []        # 二级分隔符 → 触发 mom 子块切分
        self.table_context_size = 0          # 表格上下文 token 数（0=不附加）
        self.image_context_size = 0          # 图片上下文 token 数
```

`check()`（:60-87）：`token_size→delimiter` 向后兼容；str→list 分隔符归一；`chunk_token_size` 正整数、`overlapped_percent` [0,1) 十进制、context_size 非负校验。

**delimiter 生效规则**（`_invoke` :391-437）：
- **有有效自定义分隔符** → 按正则切文本（`_split_text_by_pattern`）；
- **没有分隔符** → 退化为按 token 数合并（`naive_merge` 文本路径 / `_merge_text_chunks_by_token_size` JSON 路径，`threshold = chunk_token_size * (100-overlapped_percent)/100`）；
- **`delimiter_mode="one"`** → 整篇并成一个 chunk。

---

## 八、TitleChunker —— 按标题层级切块（rag/flow/chunker/title_chunker/）

`TitleChunker` 是与 TokenChunker 平级的独立 flow 组件（参数类 `TitleChunkerParam`，common.py:49-77）：

```python
self.levels = []                      # 每级标题的正则族 [[...],[...],...]
self.hierarchy = None                 # 取第几级标题作为切块目标级
self.include_heading_content = False  # 标题是否并入正文块
self.root_chunk_as_heading = False    # 首块文本是否拼到后续所有块前
self.chunk_token_cap = 512            # 每块 token 硬上限，超了按句子再切
```

**标题从哪来**（不是独立参数）——`extract_line_records`（common.py:237-272）把上游记录归一化成 `{text, doc_type_kwd, img_id, layout, _pdf_positions}` 记录流，然后三选一判定标题级：
1. **正则族匹配** `match_regex_level`（:282-289）——如 `^#[^#]` 是 H1，`^##[^#]` 是 H2；
2. **PDF 书签 outline** `resolve_outline_levels`（:335-357）——与书签相似度 >0.8 判定；
3. **布局标签** `match_layout_level`（:321-326）——layout 含 `section|title|head`。

**标题怎么单独成 chunk**——`HierarchyTitleChunker._ChunkNode._dfs`（hierarchy_chunker.py:56-74）：

```python
elif not self.children and 1 <= self.level <= depth:
    chunk_paths.append(path_titles)    # 叶子标题在目标深度内且无正文 → 标题路径单独成 chunk
```

超限块 `_enforce_token_cap`（common.py:209-235）按句子边界重切（媒体块跳过）。

---

## 九、对照 ai_assistant

| RAGFlow | 你的 ai_assistant | 差距 |
|---------|------------------|------|
| `doc_type_kwd` 区分 text/table/image chunk | 文本一律纯文本 | ⚠️ 表格/图片该单独成块 |
| VLM 生成图片描述进 text | 图片知识丢失 | ❌ 该加视觉理解 |
| `context_above/below` 媒体上下文 | 无 | ⚠️ 表格 chunk 缺上下文语义 |
| `mom` + 母块（子检索/父喂 LLM） | 无父子结构 | ❌ 大小块结合检索 |
| `children_delimiters` 二级切分 | 无 | ⚠️ 结构化文档的二级粒度 |
| TitleChunker 按标题层级切块 | 无标题感知 | ⚠️ 长文档检索粒度 |
| `_pdf_positions` → position_int/page_num_int | 无坐标 | ❌ 引用定位 |

**落地优先级**：
- **P0**：**媒体块单独成 chunk + `doc_type_kwd`**——成本极低，表格/图片不再污染正文。
- **P1**：**父/子块结构**——`mom` 字段 + 母块落库，检索质量提升明显（小块命中、大块喂 LLM）。
- **P2**：媒体上下文（context_above/below）+ VLM 图片描述——需要 VLM 资源，最后上。

---

## 十、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 媒体块识别 | `_build_json_chunks`（119） | doc_type_kwd → ck_type，媒体块独立成 chunk |
| 图片描述 | `enhance_media_sections_with_vision`（utils.py:162） | VLM 看图 → 描述拼进 text |
| 媒体上下文 | `_attach_context_to_media_chunks`（190） | 前后文按 token 预算拼 context_above/below |
| 最终组装 | `_finalize_json_chunks`（334） | 拼 context + 去坐标标签 + 组字段 |
| 父子结构 | `_split_chunk_docs_by_children`（363）+ executor:1306 | chunker 打 mom，executor 建母块 |
| 参数 | `TokenChunkerParam`（49） | delimiter/overlap/children/context 全可配 |
| 标题切块 | TitleChunker（title_chunker/） | 正则/outline/layout 三法定级 |

**一句话心法**：**Chunker 不是"切文本"，是"结构化"**——媒体块独立成 chunk、图片补 VLM 描述、媒体补上下文、父子块建立层级、坐标剥离但保留。每一层处理都让"被检索的东西"更接近"人类理解的知识单元"。**注意别信旧教程的 `【表格】` 标记写法，当前代码用 `doc_type_kwd`。**
