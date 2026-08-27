# RAGFlow 对标 ai_assistant 改造建议

> 把 RAGFlow 学到的东西，落到你的 `ai_assistant`（信贷指标 NL2SQL + RAG）上。
> 核心思路：RAGFlow 是"知识接入（RAG）+ 生产级工程化"的样板，你的 ai_assistant 该从这里补齐。

---

## 一、你的 ai_assistant 现状 vs RAGFlow 差距

| 维度 | 你的 ai_assistant | RAGFlow | 差距 |
|------|------------------|---------|------|
| 数据读取 | 读文本/SQL 结果 | Parser 多引擎 + 队列 | ❌ 该支持 PDF/表格解析 |
| 分块 | 固定分块 | 模板化分块（FACTORY） | ❌ 该按文档类型分块 |
| 向量化 | 单条同步 | 批处理 + 限流 + 标题加权 | ❌ 该批处理 + 限流 |
| 检索 | 纯向量 top-K | 混合检索（向量+BM25）+ Rerank | ❌ 该加关键词 + 重排 |
| 编排 | 8 步 if-else 固定顺序 | Pipeline 组件化 DAG | ❌ 该组件化 |
| 任务调度 | 同步执行 | 队列 + 消费者组 + 限流器 | ❌ 该异步化 |
| 评测 | 55 条端到端 | benchmark 检索评测 | ⚠️ 缺检索评测 |
| 可插拔 | 写死 MockLLM | 五类 LLM 接口 | ⚠️ 该接口化 |

---

## 二、分优先级改造（从易到难）

### 🔴 P0：检索升级（混合检索 + 重排）—— 性价比最高

**现状**：纯向量 top-K 直接喂 LLM。

**改造**：加关键词检索 + 重排，对齐 RAGFlow 的 Dealer + Rerank：

```python
# ① 混合检索：向量 + BM25 加权融合（对标 build_fusion_expr）
def hybrid_search(query, kb_id, topk=50):
    vec_score = vector_search(query_embed(query), topk)      # 向量召回
    kw_score  = bm25_search(tokenize(query), topk)           # 关键词召回
    fused = 0.7 * kw_score + 0.3 * vec_score                # ★ 关键词权重更高
    return top_n(fused, topk)

# ② 重排：用 rerank 模型精排（对标 Rerank Base.similarity）
def rerank(query, candidates):
    scores = rerank_model.similarity(query, [c["text"] for c in candidates])
    return top_n(candidates, k=5, by=scores)
```

**效果**：精确术语（指标名/编号/字段名）召回大幅提升——对你"查信贷指标"场景特别关键（指标名是精确匹配，不是语义相似）。

### 🔴 P0：向量化批处理 + 限流（对标 Tokenizer._embedding）

**现状**：单条同步 embedding。

**改造**：批处理 + 限流 + truncate：

```python
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

@retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(initial=1, max=60))
def embed_batch(texts, model):
    return model.encode([truncate(t, model.max_length - 10) for t in texts])

# 分批 + 限流（对标 EMBEDDING_BATCH_SIZE + embed_limiter）
for i in range(0, len(texts), BATCH_SIZE):
    with embed_limiter:
        vectors.extend(embed_batch(texts[i:i+BATCH_SIZE], model))
```

### 🟡 P1：分块模板化（对标 FACTORY + Chunker）

**现状**：所有文档一刀切分块。

**改造**：按文档类型分流（指标定义文档 / SQL 样例 / 业务规则分开切）：

```python
FACTORY = {
    "indicator_definition": chunk_by_definition,   # 指标口径文档：按"指标名"切
    "sql_example":         chunk_by_sql,           # SQL 样例：按"问题-SQL"对切
    "business_rule":       chunk_by_rule,          # 业务规则：按条款切
}
```

### 🟡 P1：组件化编排（对标 Pipeline + ProcessBase）

**现状**：8 步 if-else 固定顺序。

**改造**：拆成组件，每个组件统一 `invoke`（超时/异常/回调）：

```python
class Component(ABC):
    async def invoke(self, **kwargs):
        try:
            await asyncio.wait_for(self._invoke(**kwargs), timeout=self.timeout)
        except Exception as e:
            self.set_output("_ERROR", str(e))   # 异常兜底

class QueryIndicator(Component): ...    # 查指标
class ExplainDefinition(Component): ...  # 解释口径
class TraceLineage(Component): ...      # 血缘追溯
```

### 🟢 P2：任务队列异步化（对标 TaskExecutor）

**现状**：上传文档同步解析。

**改造**：Redis 队列 + 消费者组 + 限流器，让离线解析异步、可恢复、可扩展。

---

## 三、你的差异化优势（保留，别丢）

| 你的优势 | 说明 | RAGFlow 反而没有 |
|---------|------|-----------------|
| **指标级权限** | 比 RAGFlow 的租户级更细 | RAGFlow 是 kb 级，你是指标级 |
| **血缘追溯** | catalog.get_lineage | RAGFlow 无 SQL 血缘 |
| **55 条端到端评测** | eval_qa.py | RAGFlow 只有检索评测 |
| **信贷业务理解** | XGBoost + 特征工程 | RAGFlow 通用，不懂信贷 |

**结论**：你不是要"变成 RAGFlow"，而是**把 RAGFlow 的工程化能力（混合检索/批处理/组件化/队列）补进你已经领先的业务深度（信贷指标/血缘/评测）**。

---

## 四、一句话总结

> **RAGFlow 教你"知识接入怎么做扎实"，你用它补齐检索 + 向量化 + 编排；但"懂信贷业务 + 指标权限 + 血缘"是你的护城河，别丢。**
>
> 落地顺序：**先混合检索+重排（P0）→ 再批处理 embedding（P0）→ 再分块模板化 + 组件化（P1）→ 最后队列异步化（P2）**。
