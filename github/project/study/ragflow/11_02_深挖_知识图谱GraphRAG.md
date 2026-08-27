# 深挖：知识图谱 GraphRAG（rag/graphrag/）

> 深挖 11 讲工程化。本篇回答"**知识图谱怎么构建、怎么查、和普通检索怎么共存**"。
> 核心认知：**图不是存图数据库，而是"图序列化进 ES 同一索引"**——实体/关系都向量化，查询本质是"对图行做向量检索 + pagerank 加权 + n-hop 邻域补边"。
> 关键取舍：**顶层是二选一，不是混合**——KG 库走 `KGSearch`，普通库走 `Dealer`；但 KG 内部是真正的"图 × 向量"融合。

- 源码位置：`github/project/ragflow/rag/graphrag/`（general/ light/ ner/ + search.py + utils.py + query_analyze_prompt.py）
- 上游：`rag/svr/task_executor.py:1515-1577` 的 `graphrag` 任务类型
- 下游：`settings.kg_retriever`（KGSearch）→ 在线问答选择

---

## 三问

- **Q1 解决什么问题**：普通 RAG 对"多跳关系、实体中心型问题"（A 和 B 什么关系）答不好——图结构能把实体和关系显式建模。
- **Q2 数据流哪一环**：离线链路可选分支（KG chunk 方法）+ 在线问答的 KG 检索器，与普通检索二选一。
- **Q3 删掉会怎样**：知识图谱功能消失——但代价是每 chunk 最多 ~5 次 LLM 调用，成本敏感场景慎用。

---

## 一、图谱构建入口 —— 独立的 `graphrag` 任务类型

`ParserType.KG = "knowledge_graph"`（common/constants.py:137）。`task_executor.py:1515-1577`：

```python
elif task_type == "graphrag":
    kb_parser_config.update({"graphrag": {
        "use_graphrag": True,
        "entity_types": ["organization", "person", "geo", "event", "category"],
        "method": "light",                                   # ★ 默认抽取器：LightRAG 版
        "batch_chunk_token_size": 4096, ...}})
    with_resolution = graphrag_conf.get("resolution", False)
    with_community = graphrag_conf.get("community", False)
    async with kg_limiter:
        result = await run_graphrag_for_kb(row=task, doc_ids=task.get("doc_ids", []),
            language=task_language, kb_parser_config=kb_parser_config,
            chat_model=chat_model, embedding_model=embedding_model,
            callback=progress_callback, with_resolution=with_resolution, with_community=with_community)
```

`run_graphrag_for_kb`（general/index.py:256）总编排：文档切成 ≤4096 token batch → 每篇 `generate_subgraph` LLM 抽取 → `merge_subgraph` 合并进全局图 → 可选 `resolve_entities`（消歧）/ `extract_community`（社区报告）。抽取器按 `method` 选：`general`=微软 GraphRAG 版、`light`=LightRAG 版（默认）、`ner`=spaCy 无 LLM 抽取。

## 二、实体关系抽取 —— prompt + 三元组解析 ★（light/graph_prompt.py:20-45）

**Prompt** 要求 LLM 按固定模板输出元组，用 `##` 分隔、`<|COMPLETE|>` 结尾：

```python
PROMPTS["entity_extraction"] = """---Goal---
Given a text document ... and a list of entity types, identify all entities ...
1. Identify all entities. ... Format each entity as
   ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)
2. ... Format each relationship as
   ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>
      {tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)
3. Identify high-level key words ... ("content_keywords"{tuple_delimiter}<high_level_keywords>)
...
"""
# 分隔符常量：tuple_delimiter="<|>"  record_delimiter="##"  completion_delimiter="<|COMPLETE|>"
```

**LLM 调用循环**（light/graph_extractor.py:74-121）——初次抽取 + 最多 2 轮补抽：

```python
async with chat_limiter:
    final_result = await self._async_chat("", [{"role": "user", "content": hint_prompt}], gen_conf, task_id)
history = pack_user_ass_to_openai_messages(hint_prompt, final_result, self._continue_prompt)
for now_glean_index in range(self._max_gleanings):        # = 2
    async with chat_limiter:
        glean_result = await self._async_chat("", history, gen_conf, task_id)
    final_result += glean_result
    history.extend([{"role": "user", "content": self._if_loop_prompt}])
    if_loop_result = await self._async_chat("", history, gen_conf, task_id)   # Y/N 判断
    if if_loop_result != "yes": break
```

**解析成 (head, relation, tail)**（utils.py:344-395）：

```python
def handle_single_entity_extraction(record_attributes, chunk_key):
    if len(record_attributes) < 4 or record_attributes[0] != '"entity"':
        return None
    return dict(entity_name=clean_str(record_attributes[1].upper()),
                entity_type=clean_str(record_attributes[2].upper()),
                description=clean_str(record_attributes[3]), source_id=chunk_key)

def handle_single_relationship_extraction(record_attributes, chunk_key):
    if len(record_attributes) < 5 or record_attributes[0] != '"relationship"':
        return None
    source = clean_str(record_attributes[1].upper())
    target = clean_str(record_attributes[2].upper())
    weight = float(record_attributes[-1]) if is_float_regex(record_attributes[-1]) else 1.0
    pair = sorted([source.upper(), target.upper()])        # 无向边：src/tgt 排过序
    return dict(src_id=pair[0], tgt_id=pair[1], weight=weight,
                description=clean_str(record_attributes[3]),
                keywords=clean_str(record_attributes[4]), source_id=chunk_key)
```

**作用（关键）**：三元组最终形态——实体点 `(entity_name, entity_type, description)`，关系边 `(src_id, tgt_id, weight, description, keywords)`。`general` 版走同一套解析；`ner` 版完全不用 LLM，用 spaCy 词法栈式合并 + 句内共现建边（ner/graph_extractor.py:328-517）。

## 三、图谱存储 —— "图序列化进 ES 同一索引" ★（utils.py:414-500, 550）

`set_graph` 先写全局图 + 每文档子图，再逐个把节点/边写成可向量检索的 chunk：

```python
# 实体 → chunk（utils.py:414-460）
chunk = {
    "id": get_uuid(),
    "important_kwd": [ent_name],
    "title_tks": rag_tokenizer.tokenize(ent_name),
    "entity_kwd": ent_name,                       # 实体名（节点）
    "knowledge_graph_kwd": "entity",              # ★ 行类型标记
    "entity_type_kwd": meta["entity_type"],
    "content_with_weight": json.dumps(meta, ensure_ascii=False),
    "rank_flt": float(meta.get("pagerank", 0) or 0),   # pagerank 驱动排序
    "n_hop_with_weight": json.dumps(nhop_neighbors or [], ensure_ascii=False),  # ★ 邻域预计算
    ...
}
chunk["q_%d_vec" % len(ebd)] = ebd               # 实体名的 embedding
```

```python
# 关系 → chunk（utils.py:462-500）
chunk = {
    "id": get_uuid(),
    "from_entity_kwd": from_ent_name,
    "to_entity_kwd": to_ent_name,
    "knowledge_graph_kwd": "relation",            # ★ 行类型标记
    "content_with_weight": json.dumps(meta, ensure_ascii=False),
    "weight_int": int(meta["weight"]),
    ...
}
chunk["q_%d_vec" % len(ebd)] = ebd               # "from->to: desc" 的 embedding
```

**行类型汇总**（`knowledge_graph_kwd` 取值）：
- `graph`：全 KB 全局图，`nx.node_link_data` JSON 快照
- `subgraph`：每文档子图快照，用于**断点续跑**（index.py:770-790）
- `entity` / `relation`：节点/边，各带 embedding，**是 KG 查询时做向量检索的对象**
- `community_report`：社区报告（index.py:918-962）
- `ty2ents`：实体类型→样例名，供查询改写用

**作用（关键）**：图和 chunk 共存一个 ES 索引，靠 `knowledge_graph_kwd` 区分。**pagerank 存 `rank_flt`、n-hop 邻域预计算存 `n_hop_with_weight`**——查询期零图遍历。

## 四、图谱查询 —— 先向量召回实体，再做 n-hop 邻域扩展 ★（search.py:139-275）

在线问答选择检索器（dialog_service.py:1775）：`is_knowledge_graph = all([kb.parser_id == ParserType.KG for kb in kbs])`，是则用 `settings.kg_retriever = KGSearch(docStoreConn)`。

**Step 1 查询改写**（search.py:46-66）：`query_rewrite` 用 `minirag_query2kwd` prompt 把问题拆成 `answer_type_keywords`（答案类型）和 `entities_from_query`（问题里的实体）。

**Step 2 三路召回 + n-hop 扩展**（search.py:159-218）：

```python
ty_kwds, ents = await self.query_rewrite(llm, qst, ...)
ents_from_query = self.get_relevant_ents_by_keywords(ents, filters, idxnms, kb_ids, emb_mdl, ent_sim_threshold)
ents_from_types = self.get_relevant_ents_by_types(ty_kwds, filters, idxnms, kb_ids, 10000)   # 类型下 pagerank 最高
rels_from_txt = self.get_relevant_relations_by_txt(qst, filters, idxnms, kb_ids, emb_mdl, rel_sim_threshold)

# ★ 邻域扩展：从每个命中实体的 n_hop_with_weight 取路径，边得分按 hop 衰减累加
nhop_pathes = defaultdict(dict)
for _, ent in ents_from_query.items():
    for nbr in ent.get("n_hop_ents", []):
        path, wts = nbr["path"], nbr["weights"]
        for i in range(len(path) - 1):
            f, t = path[i], path[i + 1]
            nhop_pathes[(f, t)]["sim"] += ent["sim"] / (2 + i)   # 距离越远衰减越多
            nhop_pathes[(f, t)]["pagerank"] = max(..., wts[i])
```

**Step 3 重排 + 组包**（search.py:220-275）：按 `sim * pagerank` 排序取 top，把实体/关系格式化 CSV，再拼社区报告，最后返回一个"合成 chunk"（`docnm_kwd = "Related content in Knowledge Graph"`）交给 LLM 生成答案。

## 五、融合方式 —— P(E|Q) = P(E) * P(Q|E)（search.py:193-221）★

```python
# 类型命中加权：同时被问题实体命中的实体 sim ×2
for ent in ents_from_types.keys():
    if ent not in ents_from_query: continue
    ents_from_query[ent]["sim"] *= 2

# 关系边加乘：n-hop 命中或端点命中类型都加分
for f, t in rels_from_txt.keys():
    pair = tuple(sorted([f, t]))
    s = 0
    if pair in nhop_pathes:
        s += nhop_pathes[pair]["sim"]; del nhop_pathes[pair]
    if f in ents_from_types: s += 1
    if t in ents_from_types: s += 1
    rels_from_txt[(f, t)]["sim"] *= s + 1

# 最终排序：sim × pagerank
ents_from_query = sorted(ents_from_query.items(),
                         key=lambda x: x[1]["sim"] * x[1]["pagerank"], reverse=True)[:ent_topn]
```

**作用（关键）**：**pagerank（图结构先验）与向量相似度（语义）相乘**决定入选；n-hop 路径给"未被问题向量直接命中、但经由已命中实体一跳可达"的关系补分。社区报告 `_community_retrieval_`（search.py:277）按实体名匹配 `entities_kwd` 再按 `weight_flt` 取顶。

## 六、落地成本与适用场景 ★

**构建期 LLM 调用量**（每 chunk，默认 `light`）：
- 初次抽取 1 次 + 最多 2 轮补抽（每轮 1 抽取 + 1 Y/N 判断）≈ **上限 ~5 次 LLM 调用 / chunk**
- chunk 按 `batch_chunk_token_size=4096` token 合并，所以一个 4096 token batch 就要 ~5 次调用
- 附加：实体/关系描述合并（同名描述 >12 条时）、可选 `resolution`（消歧）、可选 `community`（Leiden 分层聚类 + 每社区 1 次 LLM 报告）

**工程缓解**：每文档子图落盘断点续跑（index.py:365-371）、LLM 输出走 Redis 缓存（utils.py:170-187）、实体/关系 embedding 批量预热（utils.py:597-620）。

**适用**：多跳关系问答、实体中心型问题、需要可解释路径的领域；语料规模小到中等、实体关系稠密。**不适合**：海量/高吞吐增量入库、纯泛化语义检索、实时入库。`ner` 方法零 LLM 抽取，是成本敏感场景的替代。

---

## 七、数据流示意

```
文档 → 分块(~4096 token/batch)
        → LLM抽取: ("entity"<|>名字<|>类型<|>描述) / ("relationship"<|>src<|>tgt<|>desc<|>kw<|>权重)
        → 解析成三元组 → 生成 per-doc 子图 (networkx)
        → merge 进全局图 + pagerank + n-hop 邻域预计算
        → 落 ES 同一索引（knowledge_graph_kwd: graph/subgraph/entity/relation/community_report）
          实体/关系带 embedding，实体带 rank_flt(pagerank)+n_hop_with_weight
                ↓
用户问题 → LLM 查询改写(minirag_query2kwd → 答案类型 + 问题实体)
        → 向量检索实体点 + 按类型按pagerank取实体 + 向量检索关系边
        → n-hop 邻域扩展补边
        → sim × pagerank 重排 → 实体/关系 CSV + 社区报告
        → 合成KG chunk 喂给 LLM 生成答案
```

---

## 八、对照 ai_assistant

| RAGFlow | 你的 ai_assistant | 差距 |
|---------|------------------|------|
| LLM 抽取三元组（结构化 prompt + 补抽） | 无 | ❌ 无实体关系建模 |
| 图存 ES（knowledge_graph_kwd 行类型） | 无 | ⚠️ 无图存储 |
| pagerank × sim 融合排序 | 无 | 概念参考 |
| n-hop 邻域预计算（查询期零遍历） | 无 | 概念参考 |
| 查询改写（答案类型 + 问题实体） | 无 | 概念参考 |
| 断点续跑 + Redis 缓存 | 无 | 工程参考 |

**落地优先级**：
- **P0**：**别急着上 KG**——先确认你的问题是否"实体关系型"。如果是，用 LLM 抽取三元组存结构化表即可起步，不一定要图遍历。
- **P1**：实体消歧 + 同义词合并（同名实体不同写法合并）。
- **P2**：多跳检索（从命中实体沿关系扩展一跳/两跳）+ pagerank 加权。

---

## 九、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 构建入口 | `run_graphrag_for_kb`（index:256） | 切 batch → 抽取 → 合并 |
| 抽取 prompt | `PROMPTS["entity_extraction"]`（graph_prompt:20） | 固定模板三元组输出 |
| 补抽循环 | `graph_extractor.py:74-121` | 最多 2 轮 glean |
| 解析 | `handle_single_*_extraction`（utils:344） | 元组 → 实体/关系 dict |
| 存储 | `graph_node/edge_to_chunk`（utils:414/462） | 图行向量化进 ES |
| pagerank | `rank_flt` | 结构先验排序 |
| 邻域 | `n_hop_with_weight` | 查询期零遍历 |
| 查询 | `KGSearch.retrieval`（search:139） | 三路召回 + n-hop 扩展 |
| 融合 | sim × pagerank（search:193） | 语义 × 结构 |

**一句话心法**：**GraphRAG 的本质是把"图"翻译回"向量 + 元数据"**——实体/关系都向量化进 ES，pagerank 和 n-hop 邻域预计算好，查询时"向量召回 + 结构加权"。**顶层和普通 RAG 二选一，内部才是图×向量融合**。构建成本是每 batch 最多 5 次 LLM 调用——上不上 KG 先算这笔账。
