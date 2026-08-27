# QueryForge 阶段 C：数据入库（RAG 的前置）

> **这是"RAG 前的数据准备"**——把 schema/few-shot/文档切块 → 向量化 → 入库。
> 对比你 ai_assistant：你学了检索，但没学"入库"（怎么把数据灌进向量库）。
>
> **代码位置**：`eval/ingest_cspider.py` + `app/core/rag/ingest.py` + `app/services/ingest.py`

---

## 三问

- **Q1 解决什么问题**：RAG 检索前，数据得先切块、向量化、入库——否则检索不到
- **Q2 数据流哪一环**：RAG 前置——离线入库 → 向量库 → 在线检索
- **Q3 删掉会怎样**：向量库空的，检索不到任何东西，RAG 失效

---

## 一、入库两种数据（ingest_cspider.py）

### Schema 入库（表结构）

```python
async def ingest_schemas(enriched=False, replace=False):
    tables = load_tables()                     # 读 CSpider tables.json
    for db_id, schema in tables.items():
        docs = build_schema_docs(schema)        # schema → 可检索文档（主干2）
        total += await upsert_schema_docs(docs) # 写入向量库（upsert）
    return total
```

**大白话**：把每张表结构（列/主键/外键）变成文档，写进向量库。**upsert = 有则更新，无则插入**。

### Few-shot 入库（NL→SQL 示例）

```python
async def ingest_fewshots(limit):
    examples = load_examples("train")[:limit]   # 取训练集前 N 条
    rows = [{"db_id", "question", "sql"} for e in examples]
    # 分批写（每批 100 条），避免单次 embedding 请求过大
    for i in range(0, len(rows), batch):
        total += await upsert_fewshots(rows[i:i+batch])
    return total
```

**大白话**：把"问题 → SQL"示例写进向量库（few-shot 语料）。**分批写**——一次 100 条，防 embedding 请求超限。

---

## 二、切块：ingest.py（文档怎么切）

```python
# 三种 chunk 类型
# table：表结构文档（按表切）
# text：按 Markdown 标题切分，标题下内容为一个 chunk；超长先按段落（语义）切
# summary：按页/小节汇总，metadata 存覆盖的 chunk_id 集合

def _split_long(text, max_chars):
    """超长文本按段落切"""
    for para in re.split(r"\n\s*\n", text):   # 按空行（段落）切
        ...
```

**大白话**：文档切块策略——
- 短文档：直接一个 chunk
- 长文档：按标题/段落切（语义完整）
- summary：先汇总再存（metadata 记 chunk_id 集合）

**对比你学的 Vanna**：Vanna 没讲 chunk，QueryForge 明确讲了（按标题/段落/语义切）。

---

## 三、doc_retriever 的 summary 特殊展开

```python
# 命中 summary 块后，不用其文本，而是读 metadata.chunk_ids 回表取整页原文
```

**大白话**：摘要块只是个"索引"——命中后回去取完整原文。**这比直接给摘要更准确**。

---

## 四、完整入库流程（一图）

```
schema（tables.json）→ build_schema_docs → upsert_schema_docs
few-shot（train）    → rows[{question, sql}] → upsert_fewshots（分批）
文档                 → chunk（按标题/段落切） → upsert（含 embedding）
      ↓
向量库（pgvector）
      ↓
在线检索（retriever.hybrid_search）
```

**大白话**：三类数据（schema/示例/文档）各自切块向量化入库 → 向量库 → 在线检索用。

---

## 五、对照 ai_assistant 的改造动作

```python
# ① 你的指标文档入库（切块 + 向量化）
def ingest_indicators():
    docs = []
    for indicator in indicators:
        text = f"指标 {indicator.name}：{indicator.description}"
        docs.append({"content": text, "metadata": {"id": indicator.id}})
    # 向量化入库（ChromaDB）
    collection.add(documents=[d["content"] for d in docs],
                   metadatas=[d["metadata"] for d in docs])

# ② 加 few-shot 语料
def ingest_fewshots(examples):
    for ex in examples:
        collection.add(documents=[ex["question"]],
                       metadatas=[{"sql": ex["sql"]}])   # 存问题 + SQL

# ③ 切块（长文档按段落切）
def chunk_text(text, max_chars=1000):
    paras = re.split(r"\n\s*\n", text)   # 按段落切
    return [p for p in paras if p.strip()]
```

**改造要点**：指标文档入库 + few-shot 入库 + 切块——RAG 前数据准备。

---

## 六、小结

| 学到 | 一句话 |
|------|--------|
| schema 入库 | 表结构 → 向量库 |
| few-shot 入库 | 问题→SQL 示例 → 向量库 |
| 分批写 | 防 embedding 请求超限 |
| 切块 | 按标题/段落切（语义完整）|
| summary 展开 | 摘要当索引，命中取原文 |

> **核心心法**：RAG 前要先入库——schema/few-shot/文档切块向量化。你 ai_assistant 最该加 **few-shot 入库 + 文档切块**（README 实验证明 few-shot 最稳定收益）。
