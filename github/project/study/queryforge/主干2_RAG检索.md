# QueryForge 主干 2：RAG 检索（知识）

> **这是 QueryForge 的 RAG**——三套语料 + 混合检索 + schema 语料构建 + rerank。
> 对比你的 ai_assistant：你只有"指标文档"单语料，QueryForge 有 schema/示例/文档三套 + schema linking。
>
> **代码位置**：`app/core/rag/`（retriever.py 86行 + schema_corpus.py 152行 + reranker.py 56行 + vectorstore + keyword + embeddings）

---

## 三问

- **Q1 解决什么问题**：Text-to-SQL 需要三类知识（表结构/示例/文档），检索准了 LLM 才能生成对 SQL
- **Q2 数据流哪一环**：LangGraph 的 retrieve 节点——改写后问题 → 检索 → schema_linking
- **Q3 删掉会怎样**：LLM 不知道表结构/示例，生成 SQL 靠猜 → 准确率低

---

## 一、三套语料（关键设计）

```
schema_doc       → 表结构文档（schema linking 用）
fewshot_example  → NL→SQL 示例（few-shot 学习用）
rag_chunk        → 业务文档（业务规则用）
```

**大白话**：RAG 不只检索"文档"，还检索"表结构"和"示例"——三类分开存，各取所需。

**对比你**：你只有指标文档（相当于 rag_chunk），**缺 schema_doc + fewshot_example**。

---

## 二、schema 语料构建（schema_corpus.py 逐段）★ 你缺的

> 把数据库 schema 转成两种东西：可检索文档 + DDL 文本。

### 列信息提取

```python
def _columns_by_table(schema) -> dict:
    """返回 {表索引: [(列原名, 类型), ...]}"""
    cols_orig = schema["column_names_original"]
    types = schema.get("column_types", [])
    for i, (tbl_idx, col_name) in enumerate(cols_orig):
        if tbl_idx < 0:   # "*"（通配）跳过
            continue
        out.setdefault(tbl_idx, []).append((col_name, types[i]))
```

### 可检索的 schema 文档（每表一段）

```python
def build_schema_docs(schema, enriched=False) -> list[dict]:
    """构建 schema_doc 行：库级 1 条 + 每表 1 条"""
    docs = []

    # ① 库级概览（含所有表）
    overview = f"数据库 {db_id}，包含表：" + "、".join(tables)
    docs.append({"doc_type": "db", "content": overview})

    # ② 每表一段（列 + 主键 + 外键）
    for tbl_idx, tbl_name in enumerate(tables):
        col_lines = [f"  - {c_name} ({ctype})[主键]" if is_pk else f"  - {c_name} ({ctype})"]
        fk_lines = [f"  - {col} -> {ref_tbl}.{ref_col}"]   # 外键关系
        content = f"表 {tbl_name}，列：\n" + "\n".join(col_lines)
        if fk_lines:
            content += "\n外键：\n" + "\n".join(fk_lines)
        docs.append({"doc_type": "table", "content": content})
    return docs
```

**大白话**：schema_corpus 把表结构变成"可检索的文档"（含列/主键/外键），灌进向量库供检索。**这就是你 schema_catalog 该升级的方向**——不只存字段，还要变成可检索 + 带主外键。

### DDL 文本（喂给 LLM 的完整 schema）

```python
def build_ddl_text(schema) -> str:
    """构建紧凑 DDL 文本（CREATE TABLE 风格），用于 LLM 生成 SQL 的完整 schema 提示"""
    for tbl_idx, tbl_name in enumerate(tables):
        col_defs = [f"  {c_name} {type}{' PRIMARY KEY' if pk}"]
        fk_defs = [f"  FOREIGN KEY ({col}) REFERENCES {ref_tbl}({ref_col})"]
        lines.append(f"CREATE TABLE {tbl_name} (\n{',\n'.join(col_defs + fk_defs)}\n);")
    return "\n\n".join(lines)
```

**大白话**：另一份紧凑 DDL 文本，直接塞给 LLM 当 schema 提示（生成 SQL 用）。

---

## 三、混合检索（retriever.py 逐段）

### 双通道并发（向量 + 关键词）

```python
async def _one(q) -> list[list[dict]]:
    emb = await embed_query(q)                                # 问题 → 向量
    vec = await vectorstore.vector_search(table, emb, top_k, db_id)  # 向量检索（语义）
    kw = await _keyword_search(table, q, top_k, db_id)         # 关键词检索（精确）
    return [vec, kw]
```

### 多查询并发（扩展问题一起搜）

```python
# 改写 + 扩展成多个相似问，一起并发检索（提高召回）
results = await asyncio.gather(*[_one(q) for q in queries])
```

### RRF 融合

```python
def _rrf_fuse(ranked_lists, k):
    """RRF 融合：score = Σ 1/(k + rank)，排名越前分越高，免调权重"""
    scores = {}
    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked):
            scores[doc["id"]] = scores.get(doc["id"], 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### rerank 精排

```python
if do_rerank and fused:
    fused = await reranker.rerank(primary, fused)   # Qwen rerank 精排
```

---

## 四、完整检索流程（一图）

```
用户问题"上个月逾期率"
  → rewrite（改写）→ expand（扩展成多个相似问）
  → retrieve 节点：
      queries = [改写后问题, 扩展问1, 扩展问2]
      ├─ 并发：每个 query 走 向量 + 关键词
      ├─ RRF 融合 → 去重
      ├─ rerank 精排 → top_n
  → schema_linking（裁剪相关表/列）
  → generate_sql（带 schema 生成 SQL）
```

---

## 五、对照 ai_assistant 的改造动作

```python
# ① 加 few-shot 语料（README 实验证明最稳定收益）
fewshots = fewshot_retriever.search(query)          # 找类似问题的成功 SQL
prompt = build_prompt(query, docs, fewshots)        # 示例增强

# ② schema linking（只给相关表结构，不是整个 catalog）
relevant = schema_catalog.get_relevant(query)       # 裁剪
sql = sql_generator.generate(prompt, relevant)

# ③ 多查询并发
queries = [query, rewrite(query), expand(query)]
docs = await asyncio.gather(*[retriever.search(q) for q in queries])
docs = rrf_fuse(docs)
```

**改造要点**：few-shot 增强 + schema 裁剪 + 多查询并发——三个 RAG 准确率提升关键。

---

## 六、小结

| 学到 | 一句话 |
|------|--------|
| 三套语料 | schema/示例/文档分开存 |
| schema_corpus | 表结构 → 可检索文档 + DDL 文本 |
| 双通道 | 向量 + 关键词并发 |
| 多查询 | 改写+扩展一起搜 |
| RRF | 排名倒数求和，免调权重 |
| rerank | 精排 top-N |
| schema linking | 只给 LLM 相关表/列 |

> **核心心法**：QueryForge RAG = 三套语料 + schema 语料构建 + 混合检索 + schema 裁剪。
> 你的 ai_assistant 最该加 **few-shot 示例检索 + schema 语料构建（带主外键）**——README 实验证明 few-shot 最稳定收益。
