# 主干 ⑤：分词 + 向量化（Tokenizer + Embedding）

> 这是离线链路的**收尾**——把 chunk 变成「关键词索引 + 向量」，准备写入文档库。
> 对照你上一个问题「第六步：向量化」，这里的实现就是你该学的生产级 embedding。

## 三问

- **Q1 解决什么问题**：① 给 chunk 做**多路分词**（标题/正文/重要词/问题），支撑关键词检索；② 把 chunk 文本变成**向量**，支撑语义检索。
- **Q2 数据流哪一环**：离线链路第四、五步——上游 Chunker 输出 chunks，这里加 token + vector，输出给文档库写入。
- **Q3 删掉会怎样**：只能纯向量检索（丢关键词召回），或只能关键词检索（丢语义召回）。

---

## 一、Tokenizer 的两个职责

`Tokenizer`（rag/flow/tokenizer/tokenizer.py）一个组件干两件事，由 `search_method` 参数控制：

```python
class TokenizerParam(ProcessParamBase):
    def __init__(self):
        self.search_method = ["full_text", "embedding"]   # ★ 两个都开
        self.filename_embd_weight = 0.1                   # 标题向量权重
        self.fields = ["text"]                            # 对哪些字段 embedding
```

- `"full_text"` → **分词**（tokenize），产出关键词索引。
- `"embedding"` → **向量化**（embed），产出向量。
- `filename_embd_weight` → 标题向量和正文向量按比例加权（0.1 标题 + 0.9 正文）。

---

## 二、分词（full_text 分支）

### _invoke() 里的分词逻辑（tokenizer.py:140-195）

```python
if "full_text" in self._param.search_method:
    for i, ck in enumerate(chunks):
        ck["chunk_order_int"] = i                       # 块序号（还原文档顺序）

        # ★ 标题分词：文件名去掉扩展名
        ck["title_tks"] = rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", from_upstream.name))
        ck["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(ck["title_tks"])

        # ★ 问题/关键词分词（如果 chunk 有 questions/keywords 元数据）
        if ck.get("questions"):
            ck["question_kwd"] = ck["questions"].split("\n")
            ck["question_tks"] = rag_tokenizer.tokenize(str(ck["questions"]))
        if ck.get("keywords"):
            ck["important_kwd"] = ck["keywords"].split(",")
            ck["important_tks"] = rag_tokenizer.tokenize(str(ck["keywords"]))

        # ★ 正文分词（粗粒度 + 细粒度）
        ck["content_ltks"] = rag_tokenizer.tokenize(ck["text"])      # 粗：词
        ck["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(ck["content_ltks"])  # 细：字/子词
```

**作用（关键）**：**多路分词**是 RAGFlow 混合检索的基础：
- `title_tks`（标题词）+ `content_ltks`（正文词）+ `important_kwd`（重要词）+ `question_tks`（问题词）——四路不同的关键词字段，检索时按需加权命中。
- **粗粒度 + 细粒度**两套分词（`tokenize` vs `fine_grained_tokenize`）：中文"细粒度"能把词拆成字，解决分词不准导致的漏召回。

**对照你之前说的**：这就是"关键词索引"的落地——不是简单 `split(" ")`，而是**多字段、粗细两套、带权重**的 tokenize。

---

## 三、向量化（embedding 分支）—— 批处理 + 限流

### _embedding()（tokenizer.py:55-125）—— 生产级 embedding

```python
async def _embedding(self, name, chunks):
    if not chunks:
        return [], 0
    # ① 解析 tenant 的 embedding 模型配置
    embd_model_config = resolve_model_config(tenant_id, LLMType.EMBEDDING, kb.embd_id)
    embedding_model = LLMBundle(tenant_id, embd_model_config)

    # ② 拼出要 embedding 的文本（fields 指定的字段拼接）
    texts = []
    for c in chunks:
        txt = ""
        for f in self._param.fields:          # 默认 ["text"]
            txt += c.get(f)
        txt = re.sub(r"</?(table|td|caption|tr|th)...>", " ", txt).strip()  # 剥离 HTML 标签
        if not txt:
            continue
        texts.append(txt)

    # ③ 标题向量（整个文档名只 embed 一次，然后平铺）
    vts, c = embedding_model.encode([name])
    tts = np.tile(vts[0], (len(texts), 1))   # 标题向量 → 复制 N 份

    # ④ 正文向量：分批 + 限流 + 线程池
    def batch_encode(txts):
        return embedding_model.encode([truncate(c, embedding_model.max_length - 10) for c in txts])

    for i in range(0, len(texts), settings.EMBEDDING_BATCH_SIZE):
        async with embed_limiter:            # ★ 限流：防打爆 LLM API
            vts, c = await thread_pool_exec(batch_encode,
                texts[i : i + settings.EMBEDDING_BATCH_SIZE])   # 分批
        cnts_batches.append(vts)
        token_count += c

    # ⑤ 标题向量 + 正文向量加权融合
    title_w = float(self._param.filename_embd_weight)   # 默认 0.1
    vects = (title_w * tts + (1 - title_w) * cnts)      # 0.1*标题 + 0.9*正文

    # ⑥ 写回 chunk 的 q_{dim}_vec 字段（动态维度）
    for i, (_, ck) in enumerate(valid_pairs):
        ck["q_%d_vec" % len(v)] = v
```

**作用（这段是 embedding 的精华，全部对应你之前说的坑）**：

| 你之前说的坑 | RAGFlow 的实现 |
|-------------|---------------|
| 限流按 token 不按请求 | `embed_limiter` 信号量限流 + 分批 |
| batch 大小 | `EMBEDDING_BATCH_SIZE` 分批 |
| truncate 超长 | `truncate(c, max_length - 10)` |
| 标题加权 | `title_w * tts + (1-title_w) * cnts`（标题向量 + 正文向量融合） |
| 维度一致性 | `q_{dim}_vec` 动态字段，换模型维度变了字段名也变 |
| 单条坏数据隔离 | `if not txt: continue` 跳过空文本 |

**关键设计**：
- **标题向量 + 正文向量加权融合**：`0.1 * 标题向量 + 0.9 * 正文向量`。这样"文件名相关"也能被语义检索命中（RAGFlow 的独有技巧）。
- **动态向量字段** `q_{dim}_vec`：维度写进字段名，换 embedding 模型（维度变了）不会和旧向量冲突。

---

## 四、Embedding 抽象（rag/llm/embedding_model.py）

### Base 接口（embedding_model.py:147）

```python
class Base(ABC):
    def encode(self, texts: list):
        """文档向量：输入文本列表，输出向量列表"""
        raise NotImplementedError("Please implement encode method!")

    def encode_queries(self, text: str):
        """查询向量：输入单条 query，输出向量"""
        raise NotImplementedError("Please implement encode method!")
```

**作用**：**文档向量和查询向量分开**（`encode` vs `encode_queries`）——很多 embedding 模型对文档和查询用不同的编码方式（非对称检索，如 BGE 系列），能显著提升检索质量。

### 统一异常 EmbeddingError（embedding_model.py:49）

```python
class EmbeddingError(ModelException):
    """所有 embedding 失败统一抛这个异常（无论底层是 OpenAI/DashScope/Ollama）"""
```

**作用**：30+ provider 的失败，统一成一种异常，调用方不用关心底层 SDK 差异（对照 Vanna 的 LlmService 统一接口）。

---

## 五、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 多路分词 | `tokenizer.py:145-160` | title/content/important/question 四路 token |
| 粗+细粒度分词 | `tokenize` / `fine_grained_tokenize` | 解决中文分词漏召回 |
| 批处理 embedding | `tokenizer.py:105-112` | EMBEDDING_BATCH_SIZE 分批 |
| 限流 | `embed_limiter` | 信号量限流 |
| truncate | `truncate(c, max_length-10)` | 超长截断 |
| 标题加权 | `tokenizer.py:119` | 0.1 标题 + 0.9 正文 |
| 动态维度字段 | `q_{dim}_vec` | 换模型维度不冲突 |
| 文档/查询分离 | `encode` / `encode_queries` | 非对称检索 |

**核心心法**：生产级 embedding 不是 `model.encode(texts)` 一行，而是**「分批 + 限流 + truncate + 标题加权 + 多路分词 + 维度管理」**的组合。你的 ai_assistant 如果是单条同步 embedding，就该按这个模板改造。
