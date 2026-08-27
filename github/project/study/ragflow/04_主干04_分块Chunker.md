# 主干 ④：分块（Chunker）

> 这是 RAG 质量最敏感的一环——分块大小、重叠、边界直接决定召回效果。
> 对照你上一个问题「第三步：分块」，TokenChunker 就是生产级的实现。

## 三问

- **Q1 解决什么问题**：把解析出的文本，切成语义自洽、长度匹配 embedding 模型的 chunk。
- **Q2 数据流哪一环**：离线链路第三步——上游 Parser 输出 sections/tables，这里切成 chunks。
- **Q3 删掉会怎样**：要么整篇一个 chunk（召回不准），要么切在句子中间（语义断裂）。

---

## 一、两种分块模式

`TokenChunker`（rag/flow/chunker/token_chunker.py）支持两种模式，由 `delimiter_mode` 控制：

| 模式 | 策略 | 适用 |
|------|------|------|
| `delimiter` | 按分隔符（`\n`/标题等）切，保留边界 | 结构化文档（有明确段落/标题） |
| `token_size`（已并入 delimiter） | 按 token 数合并相邻文本，带 overlap | 无明确边界的文本流 |

---

## 二、核心代码详解

### ① 参数定义 TokenChunkerParam（token_chunker.py:49）

```python
class TokenChunkerParam(ProcessParamBase):
    def __init__(self):
        self.delimiter_mode = "delimiter"    # 分块模式
        self.chunk_token_size = 512          # 每个 chunk 的 token 数上限
        self.delimiters = ["\n"]             # 主分隔符
        self.overlapped_percent = 0          # 重叠百分比 [0,1)
        self.children_delimiters = []        # 二级分隔符（更细粒度）
        self.table_context_size = 0          # 表格上下文窗口（前后各多少 token）
        self.image_context_size = 0          # 图片上下文窗口
```

**作用**：这些参数就是前端"分块配置"能调的旋钮——`chunk_token_size` 决定块大小，`overlapped_percent` 决定重叠，`table_context_size` 决定表格前后带多少文字。

### ② 按分隔符切分 _split_text_by_pattern（token_chunker.py:102）

```python
def _split_text_by_pattern(text, pattern):
    """按分隔符正则切分，丢弃分隔符本身，保留非空段"""
    if not pattern:
        return [text or ""]
    split_texts = re.split("(" + pattern + ")", text or "", flags=re.DOTALL)
    chunks = []
    for i in range(0, len(split_texts), 2):   # 偶数位是内容，奇数位是分隔符
        chunk = split_texts[i]
        if chunk:
            chunks.append(chunk)
    return chunks
```

### ③ 按 token 数合并 _merge_text_chunks_by_token_size（token_chunker.py:264）

```python
def _merge_text_chunks_by_token_size(chunks, chunk_token_size, overlapped_percent):
    merged = []
    prev_text_idx = -1
    # ★ 阈值：达到这个 token 数就开始新的 chunk（留出 overlap 的空间）
    threshold = chunk_token_size * (100 - overlapped_percent) / 100.0

    for chunk in chunks:
        if chunk["ck_type"] != "text":        # 表格/图片不参与合并
            merged.append(deepcopy(chunk)); continue

        current = deepcopy(chunk)
        # ★ 超过预算的单块单独成 chunk，不合并（避免超长）
        should_start_new = prev_text_idx < 0 or merged[prev_text_idx]["tk_nums"] > threshold
        if current["tk_nums"] > chunk_token_size:
            should_start_new = True

        if should_start_new:
            if prev_text_idx >= 0 and overlapped_percent > 0:
                # ★ overlap：上一个 chunk 的尾部拼到当前 chunk 头部
                visible = remove_tag(merged[prev_text_idx]["text"])
                overlap_start = int(len(visible) * (100 - overlapped_percent) / 100.0)
                overlap_text = visible[overlap_start:]
                current["text"] = overlap_text + current["text"]   # 尾部→头部
            merged.append(current)
            prev_text_idx = len(merged) - 1
            continue

        # 否则：合并到上一个 chunk（用 \n 连接，避免 "hello"+"world"→"helloworld"）
        merged[prev_text_idx]["text"] += "\n" + current["text"]
        merged[prev_text_idx]["tk_nums"] += current["tk_nums"]

    return merged
```

**作用（关键）**：
1. **token 粒度控制**：按 `num_tokens_from_string` 精确计算 token 数，达到 `chunk_token_size` 才断。
2. **overlap 重叠**：新 chunk 的头部带上一个 chunk 的尾部（`overlapped_percent` 比例），保证边界信息不丢。
3. **超长单元单独成块**：超过预算的单块不硬切、不合并，保持语义完整（否则切在句子中间）。
4. **表格/图片不参与合并**：它们单独成 chunk，走各自的上下文逻辑。

### ④ 给表格/图片附上下文 _attach_context_to_media_chunks（token_chunker.py:190）

```python
def _attach_context_to_media_chunks(chunks, table_context_size, image_context_size):
    """给表格/图片 chunk 附上前后文本上下文（按 token 预算）"""
    for i, chunk in enumerate(chunks):
        if chunk["ck_type"] not in {"table", "image"}:
            continue
        context_size = image_context_size if chunk["ck_type"] == "image" else table_context_size
        if context_size <= 0:
            continue
        # 向前找文本 chunk，凑够 context_size token → context_above
        # 向后找文本 chunk，凑够 context_size token → context_below
        chunk["context_above"] = "".join(parts_above)
        chunk["context_below"] = "".join(parts_below)
```

**作用**：表格/图片本身文本很少，检索时容易丢语义。给它们附上**前后文本上下文**（`context_above`/`context_below`），最终 chunk 文本 = 上文 + 表格 + 下文，让 LLM 能理解"这个表格在讲什么"。

### ⑤ 最终输出 _finalize_json_chunks（token_chunker.py:334）

```python
def _finalize_json_chunks(chunks):
    docs = []
    for chunk in chunks:
        # ★ 剥离坐标标签 @@...##，最终文本 = 上文 + 文本 + 下文
        text = remove_tag((chunk.get("context_above") or "") +
                          (chunk.get("text") or "") +
                          (chunk.get("context_below") or ""))
        if not text.strip():
            continue
        doc = {"text": text, "doc_type_kwd": chunk.get("doc_type_kwd", "text")}
        # 保留 PDF 位置坐标（供前端高亮引用）
        if chunk.get(PDF_POSITIONS_KEY):
            doc[PDF_POSITIONS_KEY] = deepcopy(chunk[PDF_POSITIONS_KEY])
        docs.append(finalize_pdf_chunk(doc))
    return docs
```

**作用**：
- **坐标标签剥离**：解析阶段打的 `@@页\t坐标##` 标签不进 embedding/index（否则污染向量），坐标单独存 `PDF_POSITIONS_KEY` 字段供前端高亮。
- **最终 chunk = 上文 + 文本 + 下文**：表格/图片的上下文在这里拼接。

---

## 三、对照你上一个问题的分块要点

| 你之前说的 | RAGFlow 的实现 |
|-----------|---------------|
| 块大小匹配 embedding 模型 | `chunk_token_size`（默认 512）+ token 精确计算 |
| 重叠 50-150 token | `overlapped_percent` 比例重叠 |
| 结构感知分块 | `delimiter` 按标题/段落边界 + `children_delimiters` 二级切分 |
| 表格特殊处理 | `_attach_context_to_media_chunks` 附上下文 |
| 代码按函数切 | 模板层（book/laws/paper）各自实现 |
| chunk 大小按上下文窗口倒推 | `chunk_token_size` 可配 |

---

## 四、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 参数 | `token_chunker.py:49` | 分块可配置（大小/重叠/上下文） |
| 分隔符切分 | `_split_text_by_pattern` | delimiter 模式 |
| token 合并 | `_merge_text_chunks_by_token_size` | token_size 模式 + overlap |
| 媒体上下文 | `_attach_context_to_media_chunks` | 表格/图片附前后文 |
| 最终输出 | `_finalize_json_chunks` | 剥离坐标标签 + 拼接上下文 |

**核心心法**：分块不是"一刀切"，是**「分隔符边界 + token 上限 + overlap + 表格特殊处理」**的组合。
RAGFlow 的 TokenChunker 把这几件事解耦成独立函数，可读、可测、可调。你的 ai_assistant 分块如果只是 `text[i:i+512]`，就该换成这个思路。
