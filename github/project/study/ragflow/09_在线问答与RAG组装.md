# 在线阶段 ⑧：在线问答与 RAG 组装

> 这是在线链路的**最后一环**——检索 + 重排拿到 top-K chunk 后，怎么拼成 prompt 喂 LLM、怎么带引用、怎么流式返回。
> 对照你上一个问题「在线链路：query → 召回 → 重排 → 拼上下文 → LLM 生成」。

## 三问

- **Q1 解决什么问题**：把「检索到的 top-K chunk」变成「带引用的高质量答案」。
- **Q2 数据流哪一环**：在线链路终点——上游 Dealer 检索 + Rerank 重排，这里组装生成。
- **Q3 删掉会怎样**：有知识库但不会用，答案不带引用 → 幻觉 + 不可信。

---

## 一、在线问答数据流图

```
用户 query
  │
  ▼
① retriever.retrieval(query, emb_mdl, tenant_id, [kb_id], ...)   ← rag/nlp/search.py
  │   Dealer.search（混合检索：向量+BM25 fusion）→ Dealer.rerank_by_model（重排）
  │   返回 top-K chunks（含 text + page_num_int + position_int + similarity）
  ▼
② 组装 context
  │   top-K chunk 文本 → <context> 块，每条带 ID
  ▼
③ LLM 生成（带引用）
  │   citation_prompt 规定引用格式 [ID:45]，禁止编造
  ▼
④ SSE 流式返回前端 → 前端高亮引用，点开看原文
```

---

## 二、检索入口 retrieval（rag/nlp/search.py）

从 `benchmark.py` 能看到检索服务怎么被调用：

```python
# rag/benchmark.py —— 评测时对每个 query 调检索
ranks = settings.retriever.retrieval(
    query, self.embd_mdl, self.tenant_id, [self.kb.id],
    1,       # page
    30,      # topn
    0.0,     # similarity threshold
    self.vector_similarity_weight,   # 向量权重（默认 0.3）
)
for c in ranks["chunks"]:
    run[query][c["chunk_id"]] = c["similarity"]   # 记录每个 chunk 的相似度
```

**作用**：`retriever.retrieval()` 是**在线检索的统一入口**——内部走 `Dealer.search`（混合召回）+ `Dealer.rerank` / `rerank_by_model`（重排），返回带 `similarity` 的排序 chunk。

---

## 三、重排 + 分数融合 Dealer.rerank_by_model（search.py:526）

```python
def rerank_by_model(self, rerank_mdl, sres, query, tkweight=0.3, vtweight=0.7, ...):
    _, keywords = self.qryr.question(query)          # query 分词

    # ① 把每个候选 chunk 的"文本字段"拼成一句话（重排模型的输入）
    ins_tw = []
    for i in sres.ids:
        content_ltks = sres.field[i][cfield].split()
        title_tks = [t for t in sres.field[i].get("title_tks", "").split() if t]
        important_kwd = sres.field[i].get("important_kwd", [])
        tks = content_ltks + title_tks + important_kwd
        ins_tw.append(tks)
    docs = [remove_redundant_spaces(" ".join(tks)) for tks in ins_tw]

    # ② 关键词相似度（BM25/token 重叠）
    tksim = self.qryr.token_similarity(keywords, ins_tw)

    # ③ ★ 重排模型打分（rerank_mdl.similarity 已归一化到 [0,1]）
    vtsim, _ = rerank_mdl.similarity(query, docs)

    # ④ ★ 融合：0.3 * 关键词 + 0.7 * 重排模型分
    return tkweight * np.array(tksim) + vtweight * vtsim + rank_fea, tksim, vtsim
```

**作用（关键）**：
1. **重排模型打分 + 关键词打分融合**：`0.3 * tksim + 0.7 * vtsim`——重排模型（Cross-Encoder）是主力，关键词作补充。**分数融合的前提是两者同一尺度**（这就是主干⑥里 `Rerank Base._normalize_rank` 归一化到 [0,1] 的原因）。
2. **候选输入构造**：把 chunk 的 `content + title + important_kwd` 拼成一句话喂重排模型——重排模型看的是"query 和整段文本"的相关性，比只靠向量更准。

---

## 四、RAG 组装（拼 context + 引用）

### 引用格式（rag/prompts/citation_prompt.md）

```
Based on the provided document or chat history, add citations using format [ID:i]

# Technical Rules:
- Use format: [ID:i] or [ID:i] [ID:j] for multiple sources
- Place citations at the end of sentences, before punctuation
- Maximum 4 citations per sentence
- DO NOT cite content not from <context></context>
- DO NOT modify whitespace or original text

# What MUST Be Cited:
1. Quantitative data: Numbers, percentages, statistics
2. Temporal claims: Dates, timeframes
3. Causal relationships
4. Comparative statements
5. Technical definitions
...

# Example:
<context>
ID: 45
└── Content: The global smartphone market grew by 7.8% in Q3 2024, with Samsung holding 20.6% market share...
ID: 46
└── Content: 5G adoption reached 1.5 billion users worldwide by October 2024.
</context>
USER: How is the smartphone market performing?
ASSISTANT: The global smartphone market grew by 7.8% in Q3 2024 [ID:45]. Samsung leads with 20.6% market share [ID:45]. This is partly driven by 5G, which reached 1.5 billion users [ID:46].
```

**作用（关键）**：这是"**带引用的 RAG**"的落地——一个专门的 prompt 规定：
- 引用格式 `[ID:i]`，放在句末、标点前，最多 4 个。
- **禁止引用 `<context>` 之外的内容** → 防幻觉的硬约束。
- 强制要求引用**数字、时间、因果、定义、预测**类内容 → 答案可溯源。

### context 怎么拼（retrieval 服务里）

```python
# 简化示意（实际在 chat 服务里）
context_blocks = []
for i, chunk in enumerate(top_k_chunks):
    context_blocks.append(f"ID: {chunk['id']}\n└── Content: {chunk['text']}")
context = "<context>\n" + "\n".join(context_blocks) + "\n</context>"
# → 拼进 prompt：system(citation_prompt) + user(context + query)
# → LLM 生成带 [ID:i] 的答案
```

---

## 五、在线问答 API（服务层）

```
api/apps/restful_apis/chat_api.py    # 聊天接口（REST）
api/apps/restful_apis/bot_api.py     # 机器人/Agent 接口
api/apps/restful_apis/search_api.py  # 纯检索接口
api/apps/restful_apis/dify_retrieval_api.py  # Dify 兼容检索
```

**在线问答的接口**：
- `POST /chat/completions`：完整问答（检索 → 组装 → 生成）。
- `POST /retrieval`：只检索，不生成（给其他系统用）。
- 流式：SSE 逐 token 推送（打字机效果）。

**和 Vanna 对照**：Vanna 是 `agent.send_message() → 组件流`；RAGFlow 是 `POST /chat → 检索+生成 → SSE`。两者都是「把 LLM 循环包成服务」，只是 RAGFlow 多了一步「检索组装」。

---

## 六、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 检索入口 | `retriever.retrieval` | 混合检索 + 重排统一入口 |
| 重排融合 | `rerank_by_model` | 0.3 关键词 + 0.7 重排模型分 |
| 引用格式 | `citation_prompt.md` | [ID:i] 引用 + 防幻觉约束 |
| context 组装 | chat 服务 | top-K chunk → <context> |
| 在线 API | `chat_api.py` 等 | REST + SSE 流式 |

**核心心法**：在线问答 = **「检索 + 重排 + 组装 + 引用 + 流式」**。RAGFlow 用专门引用 prompt 做"防幻觉"——这是你 ai_assistant 最缺的一块：答案可溯源、可点击、可验证。
