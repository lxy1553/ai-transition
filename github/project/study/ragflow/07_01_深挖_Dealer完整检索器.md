# 深挖：Dealer 完整检索器（rag/nlp/search.py + query.py）

> 深挖 07 讲检索重排概貌。本篇回答"**一个检索请求在 Dealer 里怎么走完**"——查询分析（question）→ 构造表达式 → 三路引擎搜索 → 融合重排 → 装配 SearchResult。
> 核心认知：**检索 = 全文（查询改写）+ 向量（整句编码）+ 融合（weighted_sum）+ 重排（token 相似度 × 向量相似度）**。关键词不直接进向量检索（向量用整句），而是驱动高亮和重排。
> ⚠️ 本版本无 `NaiveQA`（查询分析类是 `FulltextQueryer`）、无 `_row_rank`（融合是 weighted-sum 类，不是 RRF）。

- 源码位置：`github/project/ragflow/rag/nlp/{search,query,term_weight,synonym}.py`
- 上游：Retrieval 组件（深挖 12_02）调 `settings.retriever.retrieval()`
- 下游：`dataStore.search` → ES 连接器（深挖 08_01）

---

## 三问

- **Q1 解决什么问题**：把一句话问题变成"能命中知识库"的查询——分词、去疑问词、词加权、同义词展开、字段 boost、向量编码，一条龙。
- **Q2 数据流哪一环**：在线链路⑥——`Dealer.retrieval/search` 是混合检索的总入口。
- **Q3 删掉会怎样**：检索质量崩——命中率低、无排序、无高亮，RAG 变成"碰运气"。

---

## 一、`Dealer.__init__` —— 只持查询分析器 + 存储连接（search.py:49-52）

```python
class Dealer:
    def __init__(self, dataStore: DocStoreConnection):
        self.qryr = query.FulltextQueryer()
        self.dataStore = dataStore
```

**作用**：`qryr`（查询分析器）内部再初始化 `term_weight.Dealer` + `synonym.Dealer`（query.py:29-31）。**`embd_mdl` 和 `rerank_mdl` 不存为实例属性**，每次调用作为参数传入——模型即用即传。`dataStore` 由全局配置注入（settings.py:393-422 按 `DOC_ENGINE` 挑 ES/Infinity/GaussDB），`settings.py:476` 统一 `retriever = search.Dealer(docStoreConn)`。

## 二、`question()` —— 查询分析（query.py:42-167）★

先预处理：英文/中文间加空格、简繁转换、全角转半角、过滤特殊字符，再分非中文/中文两条分支。

**非中文分支**（query.py:42-94）：

```python
txt = self.add_space_between_eng_zh(txt)
txt = re.sub(r"[ :|\r\n\t,，。？?/`!！&^%%()\[\]{}<>*~'\"\\]+", " ",
             rag_tokenizer.tradi2simp(rag_tokenizer.strQ2B(txt.lower()))).strip()
txt = self.rmWWW(txt)                      # 剥离"请问/如何/是什么"等疑问语气词
if not self.is_chinese(txt):
    tks = rag_tokenizer.tokenize(txt).split()
    keywords = [t for t in tks if t]
    tks_w = self.tw.weights(tks, preprocess=False)          # term_weight 打分
    for tk, w in tks_w[:256]:
        syn = [rag_tokenizer.tokenize(s).replace("'", "") for s in self.syn.lookup(tk)]
        keywords.extend(syn)
        syn = ['"{}"^{:.4f}'.format(s, w / 4.0) for s in syn if s.strip()]
        syns.append(" ".join(syn))
    q = ["({}^{:.4f}".format(tk, w) + " {})".format(syn) for (tk, w), syn in zip(tks_w, syns) if tk and not re.match(r"[.^+\(\)-]", tk)]
    for i in range(1, len(tks_w)):                            # 相邻词构成短语
        q.append('"%s %s"^%.4f' % (tks_w[i-1][0], tks_w[i][0], max(tks_w[i-1][1], tks_w[i][1]) * 2))
    query = " ".join(q)
    return MatchTextExpr(self.query_fields, query, 100, {"original_query": original_query}), keywords
```

**中文分支**（query.py:96-167）：`self.tw.split(txt)[:256]` 切关键词短语，每个短语 `term_weight.weights` 打分、`fine_grained_tokenize` 拆细粒度字词、`synonym.lookup` 查同义词，拼成 `(词)^权重 OR "细粒度词组"^0.5 OR ("近义词")^0.2` 的 OR 表达式，整体 OR 并设 `minimum_should_match`。

`query_fields`（query.py:32-40）是带 boost 的字段列表：`title_tks^10, title_sm_tks^5, important_kwd^30, important_tks^20, question_tks^20, content_ltks^2, content_sm_ltks`。

**作用（关键）**：`question()` 返回 `(MatchTextExpr, keywords)`——前者是把问句改写成"字段加权 + 词权重 + 同义词/细粒度展开 + minimum_should_match"的全文检索表达式；后者是关键词列表，供 rerank 和高亮使用。

## 三、`search()` 完整主流程（search.py:144-277）★

```python
# ① get_filters 构造过滤条件（131-142）
for key, field in {"kb_ids": "kb_id", "doc_ids": "doc_id"}.items():
    if key in req and req[key] is not None: condition[field] = req[key]
for key in ["id", "knowledge_graph_kwd", "available_int", "entity_kwd",
            "from_entity_kwd", "to_entity_kwd", "removed_kwd"]:
    if key in req and req[key] is not None: condition[key] = req[key]
if isinstance(req.get("must_not"), dict): condition["must_not"] = req["must_not"]

# ② get_vector 构造向量表达式（65-72）——整句 query 编码成 dense 向量
async def get_vector(self, txt, emb_mdl, topk=10, similarity=0.1):
    qv, _ = await thread_pool_exec(emb_mdl.encode_queries, txt)
    embedding_data = [get_float(v) for v in qv]
    vector_column_name = f"q_{len(embedding_data)}_vec"    # ★ 按维度命名：q_768_vec
    return MatchDenseExpr(vector_column_name, embedding_data, "float", "cosine", topk,
                          {"similarity": similarity})

# ③ 三路引擎的混合检索 + fusion 表达式（202-235）
matchText, keywords = self.qryr.question(qst, min_match=(0.3 if min_match else 0))
matchDense = await self.get_vector(qst, emb_mdl, topk, req.get("similarity", 0.1))
if settings.DOC_ENGINE_INFINITY:
    vector_similarity_weight = float(req.get("vector_similarity_weight", 0.3))
    fusionExpr = build_fusion_expr(topk, vector_similarity_weight)
elif settings.DOC_ENGINE_GAUSSDB:
    fusionExpr = FusionExpr("weighted_sum", topk, {"weights": f"{1 - float(vector_weight)},{float(vector_weight)}"})
else:
    fusionExpr = FusionExpr("weighted_sum", topk, {"weights": "0.001,1"})   # ES
matchExprs = [matchText, matchDense, fusionExpr] if matchText else [matchDense]
res = await thread_pool_exec(self.dataStore.search, src, highlightFields, filters,
    matchExprs, orderBy, offset, limit, idx_names, kb_ids, rank_feature=rank_feature)

# ④ 空结果重试（240-261）：total==0 时先丢全文只做向量；否则 min_match 降到 0.1、向量阈值放宽到 0.17 再搜一次
# ⑤ 收尾（263-277）：keywords 做 fine_grained_tokenize 扩展 → 取 _score/高亮/聚合 → SearchResult
```

**作用**：`get_filters` 造等值/`must_not` 过滤 → `question()` 造全文 `MatchTextExpr` + `get_vector` 造 `MatchDenseExpr` → 按引擎拼接 `FusionExpr`（Infinity/GaussDB 原生 weighted_sum；ES 用 bool boost + knn 线性融合）→ 空结果降 `min_match` 重试。

## 四、`token_similarity` —— 关键词相似度（query.py:180-209）★

**不是 BM25**。先对 query 与每个 doc 的词序列各建"权重词袋"（unigram 权重 ×0.4 + 相邻 bigram 权重 ×0.6），词权重来自 `term_weight.weights`（idf 式频率 + NER 类型 + 词性加权），再算 query 侧被 doc 命中的权重占比（非对称重叠相似度）：

```python
def token_similarity(self, atks, btkss):
    def to_dict(tks):
        d = defaultdict(int)
        wts = self.tw.weights(tks, preprocess=False)
        for i, (t, c) in enumerate(wts):
            d[t] += c * 0.4                      # unigram 权重
            if i + 1 < len(wts):
                _t, _c = wts[i + 1]
                d[t + _t] += max(c, _c) * 0.6    # bigram 权重取两者较大
        return d
    atks = to_dict(atks)
    btkss = [to_dict(tks) for tks in btkss]
    return [self.similarity(atks, btks) for btks in btkss]

def similarity(self, qtwt, dtwt):
    s = 1e-9
    for k, v in qtwt.items():
        if k in dtwt: s += v                     # 命中的 query 权重
    q = 1e-9
    for k, v in qtwt.items(): q += v             # 全部 query 权重
    return s / q                                 # ★ 命中权重占比
```

`term_weight.weights` 的本质（term_weight.py:192-290）：`0.3*idf(freq,N=10M) + 0.7*idf(df,N=1B)`，再乘 `ner(t)*postag(t)`（实体类型权重 × 词性权重），最后整体归一化。

**作用**：加权 token 重叠（含 bigram），权重 = idf 频率 × 实体类型 × 词性，得分 = 命中的 query 权重占比。

## 五、混合相似度 / rerank —— 融合公式 ★（query.py:170-178 + search.py:465-550）

**本地混合相似度**（query.py:170-178）：

```python
def hybrid_similarity(self, avec, bvecs, atks, btkss, tkweight=0.3, vtweight=0.7):
    sims = cosine_similarity([avec], bvecs)
    tksim = self.token_similarity(atks, btkss)
    if np.sum(sims[0]) == 0:
        return np.array(tksim), tksim, sims[0]
    return np.array(sims[0]) * vtweight + np.array(tksim) * tkweight, tksim, sims[0]
```

**ES 路径的 `rerank_with_knn`**（search.py:465-490）——二次纯 KNN 取余弦分 + 本地 token 相似度加权：

```python
tksim = np.array(self.qryr.token_similarity(keywords, ins_tw), dtype=np.float64)
vtsim = np.array([knn_scores.get(chunk_id, 0.0) for chunk_id in sres.ids], dtype=np.float64)
rank_fea = self._rank_feature_scores(rank_feature, sres)      # 标签余弦 + pagerank
sim = tkweight * tksim + vtweight * vtsim + rank_fea          # ★ 融合公式
```

**外部 rerank 模型**（`rerank_by_model`，search.py:525-550）：`vtsim = rerank_mdl.similarity(query, docs)`（BGE/bge-rerank 归一化到 [0,1]），同样 `tkweight*tksim + vtweight*vtsim + rank_fea`。然后 `np.argsort(sim * -1, kind="stable")` 稳定排序 + 阈值过滤 + 分页切片（search.py:700-721）。

**本地 rerank 的加权 token 组装**（search.py:509-523）：

```python
content_ltks = list(OrderedDict.fromkeys(sres.field[i][cfield].split()))
title_tks = [t for t in sres.field[i].get("title_tks", "").split() if t]
question_tks = [t for t in sres.field[i].get("question_tks", "").split() if t]
important_kwd = sres.field[i].get("important_kwd", [])
tks = content_ltks + title_tks * 2 + important_kwd * 5 + question_tks * 6   # ★ 字段加权
```

**作用（关键）**：融合 = `term_weight*token_overlap + vector_weight*向量相似度 + rank_feature(标签余弦+pagerank)`。Infinity/ES/GaussDB 在引擎内先融合，**ES 再通过二次 KNN 调用取干净余弦做本地加权合并**。

## 六、keywords 如何影响检索（search.py:202-275）

```python
matchText, keywords = self.qryr.question(qst, ...)      # search.py:202
...
for k in keywords:
    kwds.add(k)
    for kk in rag_tokenizer.fine_grained_tokenize(k).split():
        if len(kk) < 2: continue
        if kk in kwds: continue
        kwds.add(kk)
keywords = list(kwds)
highlight = self.dataStore.get_highlight(res, keywords, "content_with_weight")   # 高亮
```

- **进全文检索**：`matchText` 里的 query 字符串 + `query_fields` boost + `minimum_should_match`。
- **进向量检索**：`get_vector` 用**整句原始 question**，不是 keywords。
- **keywords 的三个用途**：① 高亮（`get_highlight`）；② rerank 的 token 相似度（`rerank_with_knn`/`rerank`/`rerank_by_model` 里重新 `question()` 取 keywords）；③ 辅助 `tag_query`。

---

## 七、数据流示意

```
question
   │
   ▼
FulltextQueryer.question()  ──(rmWWW 去疑问词、分词、term_weight 打分、同义词/细粒度展开)──▶ MatchTextExpr + keywords[]
   │   emb_mdl.encode_queries(question)                              ▼
   ▼                                    build_fusion_expr ──▶ FusionExpr("1-v,v")
MatchDenseExpr("q_{dim}_vec", vec, cosine, topk)                      │
   │                                    matchExprs = [matchText, matchDense, fusionExpr]
   └───────────────────────────────────────────┼─────────────────────┘
                                               ▼ dataStore.search(filters, matchExprs, ...)
                          ┌───────────┼──────────────┬───────────────┐
                          ▼           ▼              ▼               ▼
                        Infinity   Elasticsearch   GaussDB        OceanBase/SereneDB
                   引擎内 weighted_sum      bool boost(1-v)     SQL 内 fusion      回传 chunk 向量
                   + atan 归一化     + knn 二次调用取余弦               │
                          │            rerank_with_knn                ▼
                          ▼            (tk*tsim + vt*vsim + rank_fea) rerank() 本地 hybrid_similarity
                   直接取 _score ──────────►                          (cosine*v + token_overlap*tk + rank_fea)
                          ▼
             rerank_by_model（可选）: tksim + rerank_mdl.similarity(query,docs) 加权
                          ▼
             np.argsort(-sim, kind="stable") → 阈值过滤 → 分页 → ranks{chunks, doc_aggs}
```

---

## 八、对照 ai_assistant

| RAGFlow | 你的 ai_assistant | 差距 |
|---------|------------------|------|
| `FulltextQueryer.question` 查询改写（去疑问词/词加权/同义词） | 原样问题直接检索 | ❌ 命中率低 |
| 字段 boost（title^10/important_kwd^30） | 无 | ⚠️ 标题命中和正文同权重 |
| 全文+向量+融合三路 | 单一向量检索 | ⚠️ 术语/精确匹配召回差 |
| weighted_sum 融合 + 引擎外二次合并 | 无 | ⚠️ 两种信号不会融合 |
| 空结果降级重试 | 无 | ⚠️ 无结果不会放宽阈值 |
| token 相似度重排（非 BM25） | 无 | ⚠️ 无重排阶段 |
| 高亮 `<em>` | 无 | ⚠️ 前端无高亮 |

**落地优先级**：
- **P0**：**查询改写**——去掉"请问/如何"等疑问词，保留实词；简单 IDF 加权即可大幅提升命中。
- **P1**：**全文 + 向量融合**——BM25 + 余弦用 `weight*term + weight*vector` 合并排序。
- **P2**：字段 boost（标题/关键词字段加权重）+ 空结果降级重试。

---

## 九、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 初始化 | `Dealer.__init__`（search:49） | 查询分析器 + 存储连接 |
| 查询分析 | `question`（query:42） | 分词/加权/同义词/字段 boost |
| 向量 | `get_vector`（search:65） | 整句编码 → MatchDenseExpr |
| 融合 | FusionExpr 三引擎分派（202-235） | weighted_sum |
| 过滤 | `get_filters`（131） | kb/doc/must_not |
| Token 相似 | `token_similarity`（query:180） | 加权词袋重叠（含 bigram） |
| 本地混合 | `hybrid_similarity`（query:170） | cosine×v + token×tk |
| 模型重排 | `rerank_by_model`（search:525） | rerank_mdl + 本地 token |
| 空结果重试 | search:240-261 | 降 min_match + 放宽阈值 |

**一句话心法**：**检索质量 = 查询改写（让问题更像索引语言）+ 多路召回（全文抓术语、向量抓语义）+ 融合重排（不同信号加权合并）+ 结果装配（高亮/排序/引用）**。RAGFlow 把每条都拆成独立环节，环环可替换——关键词是重排和全文的输入，向量是整句语义的输入，**两种信号各管一摊、最后融合**。
