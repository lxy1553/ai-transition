# RAG-BUILD-SKILLS 学习目录（方法论 + 代码 + 注释）

> 本文件是 `RAG-BUILD-SKILLS`（生产级领域自适应 RAG 构建方法论）的学习导图。**不是框架，是一套方法论 + 参考脚本**。
> 三层结构：`SKILL.md`（方法论圣经 1049 行）+ `config/default_config.yaml`（参数中心）+ `scripts/`（**半成品骨架**：算法逻辑是真代码、外部依赖是 # ADAPT 占位）。
> 核心认知：**重排优先（Reranker-First）** + **父子分块** + **RRF 融合** + **评估驱动三层循环** + **增量知识管理**。它解决"怎么建、怎么评估、何时停"，不解决"建出来长什么样"——后者看 RAGFlow。
> ⚠️ 脚本可运行性：评估类脚本有真实现；在线检索类脚本返回假数据；`reranker.py` 直接跑会因缺 `chunked_corpus.json` 崩溃（离线管线未产输入）。

- 项目位置：`github/project/RAG-BUILD-SKILLS` ｜ 学习文件：`study/rag-build-skills/`
- 与本仓库对照：RAGFlow（实现层）· queryforge（你的具体实现）· RAG-BUILD-SKILLS（方法论层）

---

## 一、仓库全景

```
离线: [文档] → [OCR/解析] → [分块] → [索引] → [可选: 微调] → [提示词]
在线: [查询] → [改写] → [路由] → [检索] → [重排序] → [生成]
评估: [Q-DOC] + [Q-DOC-A] → 循环优化
运营: 增量入库 + 文档三类分诊（替换/并行/legacy）
```

| 文件 | 作用 | 实现完整度 |
|------|------|-----------|
| `SKILL.md` | 方法论圣经（12 节） | ⭐⭐⭐ 高 |
| `SKILL_CN.md` | 中文版 | ⭐⭐⭐ |
| `config/default_config.yaml` | 全参数单点配置 | ⭐⭐⭐ |
| `prompts/initial_prompt.md` | 六要素 prompt 模板 | ⭐⭐⭐ |
| `scripts/offline/`（5 核心+1 可选） | 词典/解析分块/索引/图像索引/Q-DOC-Q 生成 | ⭐⭐ 半真 |
| `scripts/online/`（5 核心+1 可选） | 改写/混合检索/重排/生成/多模态/编排 | ⭐⭐ 半真 |
| `scripts/eval/`（4）+ `offline_eval/`（1） | 评估数学 + 坏例分类 + 参数扫描 | ⭐⭐⭐ 真实现最多 |
| `scripts/finetune/`（2 可选） | 训练数据 + 微调门槛判断 | ⭐⭐ 半真 |
| `data/expert_eval_set.json` | 专家标注评估集样例 | ⭐⭐⭐ |

**代码完整度总判断**：`# CORE`（方法论逻辑，真写）vs `# ADAPT`（外部依赖，占位）。数学/算法/数据契约全真，
外部调用（BM25 后端/向量库/LLM Judge/OCR）全占位。**伪实现只有 4 处**：`query_rewriter._llm_rewrite`、
`llm_generator._call_llm`、`multimodal_handler._encode_user_image`、`_image_vector_search`；pipeline.py 本身零占位。

---

## 二、方法论地图（SKILL.md 目录导学）

| 节 | 主题 | 对应脚本 | 一句话 |
|----|------|---------|--------|
| 1-2 | 角色定义 + 需求收集 | — | 先给计划再写码，逐模块确认 |
| 3.1 | 关键词词典构建 | `build_keyword_dict.py` | 领域词表解决"用户的话≠文档的词" |
| 3.2 | 解析与父子分块 | `parse_and_chunk.py` | 子块 256 检索 / 父块 1024 上下文 |
| 3.3 | 索引构建 | `build_indexes.py` | BM25(领域分词)+Dense(BPE)，二选一 |
| 3.5 | 多模态图像索引（可选） | `build_image_index.py` | 图像独立索引，元数据桥接 |
| 3.4 | Prompt 六要素 | `prompts/initial_prompt.md` | 身份/功能/目标/规范/禁止/示例 |
| 3.5离线 | Q-DOC-Q 数据集生成 | `gen_qdoc_q_pairs.py`+`make_eval_set.py` | LLM 自动产评估对，免人工标注 |
| 4.1 | 查询改写 | `query_rewriter.py` | 缩写补全/子问题拆分/口语回退 |
| 4.2 | 多库路由 | pipeline `_build_filters` | 精度<50% 就删路由 |
| 4.3 | 混合检索 | `hybrid_retriever.py` | 词法+Dense 并行 → RRF 融合 |
| 4.4 | 重排 + 父子映射 | `reranker.py` | 子块打分 → 父块喂 LLM |
| 4.5 | LLM 生成 | `llm_generator.py` | 容错 JSON 解析 + 重试 |
| 4.6 | 多模态查询（可选） | `multimodal_handler.py` | 低于阈值降级为文本搜图 |
| 5.1 | 三层评估 | `qdoc_qdoca_eval.py` | 离线→Q-DOC→Q-DOC-A |
| 5.1 | 离线管线评估 | `offline_eval.py` | 原始检索隔离数据问题 |
| 5.2 | 瓶颈决策树 | `bad_case_analyzer.py` | 六大类定位瓶颈 |
| 4.4 | Top-N 扫描 | `recall_sweep.py` | 找 recall 拐点定 top_n |
| 5.3 | 微调循环 | `generate_training_data.py`+`finetune_embedding.py` | ≥5pp 部署 / ≥2pp 回滚 |
| 6 | 增量知识管理 | —（纯方法论） | 三类分诊 + 双层元数据 |

---

## 三、核心决策原则（8 条值得抄）

| 原则 | 要点 |
|------|------|
| **重排优先** | 检索阶段 ROI 最高的单组件，收益超过 embedding 微调 |
| **父子分块** | 子块精确检索、父块完整上下文；子块重排、父块生成 |
| **分词器分离** | BM25 用领域分词器保缩写，Dense 用 embedding 自带 BPE，绝不共用 |
| **RRF 融合** | BM25 分数量级(0-30)≠余弦(0-1)，RRF 只用排名，稳健 |
| **评估驱动** | 所有优化决策必须评估数据背书，不靠直觉 |
| **一次只改一个** | Loop 3 每轮只换一个组件，隔离贡献 |
| **工程问题先修** | 技术故障（解析失败）会伪装成质量问题 |
| **微调是最后手段** | 词典/参数/融合先试，微调只提升≥5pp 才部署 |

**⚠️ 值得商榷的强断言**（读时要带批判）：
1. "RRF 永远、score-level 永不"——RAGFlow 主路径恰恰用 `FusionExpr("weighted_sum", weights="0.001,1")` 且生产验证过。RRF 稳健但丢分数量级信息。
2. "BM25 与 Char-BM25 互斥"——**Section 10 又推荐加 char-BM25，自相矛盾**。真实系统多字段同时跑也不少见。
3. 配置里词典存 `.json`（`output_path`）但 jieba 加载 `.txt`（`custom_dict`），格式没对齐。

---

## 四、配置中心 default_config.yaml（参数注释）

```yaml
# config/default_config.yaml —— 全参数单点配置，脚本都从这里读

offline:
  chunking:
    # CORE: 父子分块策略参数
    parent_chunk_size: 1024    # tokens —— 给 LLM 生成的完整上下文
    child_chunk_size: 256      # tokens —— 检索精度的单位
    overlap: 50                # tokens —— 跨块信息保留
    # CORE: 绝不跨章节边界分块
    boundary_aware: true
    # ADAPT: 分词器必须和 embedding 模型的 tokenizer 一致
    tokenizer: "tiktoken"
  index:
    # CORE: 分词器分离原则 —— BM25 用领域分词器，Dense 用模型自带 BPE
    bm25:
      tokenizer: "jieba"
      custom_dict: "keyword_dict.txt"   # 来自 Step 1
    dense:
      model: "BAAI/bge-m3"
    # CORE: BM25 和 Char-BM25 互斥，只选一个（见"槽点"）
    char_bm25:
      enabled: false
  finetune:
    enabled: false              # 仅 Q-DOC 显示 Dense recall 持续低时开
    # CORE: 部署/回滚门槛 —— 评估驱动，不靠直觉
    deploy_threshold_pp: 5      # Q-DOC 提升 ≥5pp 才部署微调模型
    revert_threshold_pp: 2      # 回退 ≥2pp 就回滚基线

online:
  retrieval:
    top_n: 64                   # ADAPT: 用 recall_sweep.py 扫拐点确定
    # CORE: 永远 RRF —— 两路分数不同量纲，不能加权和
    fusion_strategy: "rrf"
    rrf_k: 60                   # RRF 平滑常数
  rerank:
    model: "BAAI/bge-reranker-v2-m3"
    top_m: 12
    # CORE: 子块打分，绝不父块（512 token 上限）
    score_on: "child"
    # CORE: 重排后的子块映射回父块喂 LLM
    map_to_parent: true
  llm:
    temperature: 0.1            # 事实性回答用低温

eval:
  # 双评估集并存（Section 5.1）
  eval_set_path: "eval_set.json"            # LLM 自动生成，chunk_id 级 GT，日常迭代
  expert_eval_set_path: "data/expert_eval_set.json"  # 专家标注，校准 LLM Judge + 验收
  loop1_convergence_pp: 5.0   # Loop1 微调：连续 2 轮增益 <5pp 停止
  loop2_convergence_pp: 0.5   # Loop2 prompt：连续 2 轮增益 <0.5pp 停止

offline_eval.pass_criteria:   # 离线管线硬门槛（offline_eval.py 用它裁决 pass/fail）
  index_coverage_bm25:    {threshold: 1.0, hard: true}   # 所有子块必须进索引
  index_coverage_dense:   {threshold: 0.99, hard: false}
  rrf_recall_at_64:       {threshold: 0.85, hard: false}
  boundary_violation_rate: {threshold: 0.0, hard: true}  # 跨边界分块=0
  parent_child_mapping_rate: {threshold: 1.0, hard: true}
```

**作用**：所有脚本的单一事实来源。父子分块、RRF k、top_n/top_m、部署门槛都在这里，改参数不改代码。

---

## 五、Prompt 六要素模板（initial_prompt.md）

```markdown
## 身份
你是{domain}领域的领域专家助手。

## 功能
根据提供的文档 chunk 回答用户问题。

## 目标
提供准确、结构化的答案，并标注文档引用。

## 回答规范
- 使用 ^1,2,3^ 引用格式，标注文档 chunk 编号
- 适当时使用标题和表格组织答案
- 如果 query 包含多个问题，需回答所有子问题
- 如果文档中存在相关信息，不得拒绝回答

## 禁止要求
- 不得编造所提供文档中不存在的信息
- 不得引用与答案不相关的文档
- 旧版文档（标注 ⚠️）仅作参考，优先依据当前版本

## 示例
用户问题：如何配置系统的登录超时时间？
文档上下文：^1^ [文档：doc_001 | 版本：v1.0 | 页码：45 | 章节：3.2 登录配置]
...
回答：系统登录超时的配置步骤如下^1^：...

## 文档上下文
{context}
## 用户问题
{query}
```

**作用**：六要素结构（身份/功能/目标/规范/禁止/示例）是 prompt 的初始版，将在 Loop 2 里按坏例迭代优化。规范段管格式、禁止段防幻觉、示例段教引用格式。

---

## 六、在线管线核心代码（检索 + 重排，真实现）

### 6.1 混合检索 hybrid_retriever.py —— RRF 融合是真代码，检索是占位 ★

```python
# hybrid_retriever.py:144-186 —— RRF 融合（真实现，能跑）★
def _fusion_rrf(lexical_results, dense_results, k, top_n):
    """
    Reciprocal Rank Fusion: sum of 1 / (k + rank) across paths.
    CORE: 唯一融合策略。RRF 只用排名，天然避免 BM25(0-30) 与余弦(0-1) 量纲不可比。
    """
    rrf_scores = {}
    def add_path(results, rank_label):
        for rank, r in enumerate(results, start=1):
            cid = r["chunk_id"]
            if cid not in rrf_scores:
                rrf_scores[cid] = {**r, "lexical_rank": 0, "dense_rank": 0, "rrf_score": 0.0}
            rrf_scores[cid][rank_label] = rank
            rrf_scores[cid]["rrf_score"] += 1.0 / (k + rank)   # ← RRF 公式
    add_path(lexical_results, "lexical_rank")
    add_path(dense_results, "dense_rank")
    ranked = sorted(rrf_scores.values(), key=lambda x: x["rrf_score"], reverse=True)[:top_n]
    for i, item in enumerate(ranked):
        item["rank"] = i + 1
    return ranked
```

```python
# hybrid_retriever.py:77-95 —— BM25 词法检索（占位，真实索引在 # ADAPT 注释里）
def _bm25_search(query, top_n, tags, config):
    # ADAPT: bm25 = load_bm25_index(config["offline"]["index"]["output_dir"])
    # ADAPT: jieba.load_userdict(config["offline"]["index"]["bm25"]["custom_dict"])
    # ADAPT: tokens = jieba.lcut(query)
    # ADAPT: results = bm25.get_scores(tokens)  # raw BM25 scores
    return [   # ← 占位假数据
        {"chunk_id": f"child_bm25_{i}", "parent_id": f"parent_{i//4}",
         "content": f"<bm25 hit {i}>", "score": float(top_n - i)}
        for i in range(top_n)
    ]
```

```python
# hybrid_retriever.py:209-222 —— 词法索引二选一 + 融合编排
lexical_index = config["online"]["retrieval"]["lexical_index"]
if lexical_index == "char_bm25":
    lexical_results = _char_bm25_search(query, top_n, tags, config)   # 错字多时用字符级
else:
    lexical_results = _bm25_search(query, top_n, tags, config)         # 默认领域分词
dense_results = _dense_search(query, top_n, tags, config)
k = config["online"]["retrieval"]["rrf_k"]
candidates = _fusion_rrf(lexical_results, dense_results, k, top_n)
```

**作用**：双通道（词法+语义）并行检索 → RRF 融合成 Top-N 候选池喂重排。**融合公式是真实现（能跑），检索后端是占位**——"算法真、环境假"的典型。

### 6.2 重排 reranker.py —— 父子映射是真代码，打分是占位 ★

```python
# reranker.py:154-200 —— 子块→父块映射（真实现，父子分块的核心价值）★
def _map_to_parent(top_m_children, parent_map):
    """
    # CORE: 重排 Top-M 子块 → 映射父块 → 喂 LLM。
    子块精确检索、父块完整上下文——这是父子分块的核心价值。
    WHY 按 parent_id 去重: 同一父块的多个子块会重复占上下文窗口。
    WHY 保留父块元数据: prompt 需要 doc_id/page/section/version 做引用溯源。
    """
    _PARENT_META_FIELDS = ["doc_id", "doc_version", "product_model", "status",
                           "page", "section", "chapter", "tag"]
    seen_parents = {}
    for child in top_m_children:
        pid = child["parent_id"]
        if pid not in seen_parents:
            parent_chunk = parent_map.get(pid, {})
            entry = {"parent_id": pid,
                     "content": parent_chunk.get("content", child["content"]),
                     "child_hits": [child["chunk_id"]]}
            for field in _PARENT_META_FIELDS:        # 元数据从父块拷来供引用溯源
                if field in parent_chunk:
                    entry[field] = parent_chunk[field]
            seen_parents[pid] = entry
        else:
            seen_parents[pid]["child_hits"].append(child["chunk_id"])
    return list(seen_parents.values())               # 按首次出现序（最高分子块在前）
```

```python
# reranker.py:132-149 —— 子块打分（占位）
def _score_pairs(reranker, query, chunks, config):
    """
    # CORE: 打分子块而非父块。父块 ~1024 token 会被交叉编码器 512 token 上限截断，
    只看到前 ~400 token，错过触发检索的那段。
    """
    # ADAPT: pairs = [[query, c["content"]] for c in chunks]
    # ADAPT: scores = reranker.compute_score(pairs, batch_size=batch_size)
    return [{**c, "rerank_score": 1.0 - i * 0.01}   # ← 占位伪分数
            for i, c in enumerate(chunks)]
```

**作用**：子块打分（`# CORE`）→ Top-M → **映射回父块**（真实现）→ 带元数据喂 LLM。`load_parent_child_map` 从 `chunked_corpus.json` 建 parent_id 查找表——**注意读 `corpus["chunks"]` 列表，不是顶层 dict**（reranker.py:105 的坑）。

---

## 七、离线管线 + 代码

### 7.1 关键词词典构建 —— build_keyword_dict.py（TF-IDF 找候选，专家定稿）

**学习要点**：领域词典是"用户的话 ↔ 文档的词"的桥，被 tag 标注 / query 改写 / jieba 自定义词典三方消费。构建不靠人工枚举，先用 TF-IDF 从领域文档抽高频特异词。

```python
# build_keyword_dict.py:51-78 —— TF-IDF 抽取领域候选词
def extract_tfidf_candidates(documents, top_k_per_doc=20, ngram_range=(1, 3)):
    """
    WHY TF-IDF: domain-specific terms appear frequently in domain docs but
    rarely in general text. TF-IDF surfaces exactly these terms without
    needing a labeled training set.
    """
    vectorizer = TfidfVectorizer(
        ngram_range=ngram_range,
        max_df=0.85,   # too common across docs -> not domain-specific
        min_df=2,      # too rare -> likely noise / single-occurrence typo
    )
    tfidf_matrix = vectorizer.fit_transform(documents)
    feature_names = vectorizer.get_feature_names_out()
    candidates = Counter()
    for row in tfidf_matrix:
        top_indices = row.toarray()[0].argsort()[::-1][:top_k_per_doc]
        for idx in top_indices:
            candidates[feature_names[idx]] += 1
    return candidates
```

```python
# build_keyword_dict.py:118-134 —— 5 字段 schema（所有下游依赖它，不许缺）
for term in all_terms:
    # CORE: every entry must carry the 5 canonical fields (use "" defaults)
    # so downstream consumers can rely on the schema unconditionally.
    raw_entries.append({
        "standard_term": term,   # 标准术语
        "abbreviation":  "",     # 缩写（专家/启发式填）
        "full_form":     "",     # 全称
        "colloquial":    [],     # 口语（从 query 日志填）
        "tag":           "",     # 域标签（NER 类型或专家填）
    })
```

**占位点**：`domain_ner_extract` 返回空、`documents/query_logs` 为占位文本、`expert_validated_entries = raw_entries` 跳过人工审核。**注意：缩写/全称/口语这 3 个关键字段默认是空的，只靠 TF-IDF 产不出，必须靠专家或 query 日志**。

### 7.2 解析与父子分块 —— parse_and_chunk.py（boundary-aware + 父子两代人）

**学习要点**：先 OCR 成 Markdown 并把图片抽为资产（图片替换为"链接+描述"占位），再按 `##`/`###` 章节边界切块——**块永远不跨章节**。每个父块带 child_ids，每个子块带 parent_id，构成 reranker 父子映射的数据基础。

```python
# parse_and_chunk.py:132-157 —— CORE: 块绝不跨 ##/### 边界
for line in markdown.splitlines():
    chap_match = re.match(r"^##\s+(.*)$", line)
    sec_match = re.match(r"^###\s+(.*)$", line)
    if chap_match:
        if buffer:
            blocks.append((current_chapter, current_section, "\n".join(buffer)))
            buffer = []
        current_chapter = chap_match.group(1).strip()
        current_section = ""
    elif sec_match:
        if buffer:
            blocks.append((current_chapter, current_section, "\n".join(buffer)))
            buffer = []
        current_section = sec_match.group(1).strip()
    else:
        buffer.append(line)
if buffer:
    blocks.append((current_chapter, current_section, "\n".join(buffer)))
return blocks
```

```python
# parse_and_chunk.py:215-225 —— 子块滑窗切分（overlap 步进）
def split_parent_into_children(parent_text, child_size, overlap, count_tokens):
    words = parent_text.split()
    children = []
    step = max(1, child_size - overlap)  # avoid zero / negative step
    i = 0
    while i < len(words):
        chunk_words = words[i:i + child_size]
        children.append(" ".join(chunk_words))
        if i + child_size >= len(words):
            break
        i += step
    return children
```

```python
# parse_and_chunk.py:282-314 —— corpus 双代 schema（父子分块的数据基础）
for p_idx, parent_text in enumerate(parents):
    parent_chunk_id = f"{doc_source}::p{page['page']}::c{p_idx}"
    child_ids = []
    children = split_parent_into_children(parent_text, child_size, overlap, count_tokens)
    for c_idx, child_text in enumerate(children):
        child_id = f"{parent_chunk_id}::ch{c_idx}"
        child_ids.append(child_id)
        # CORE: child chunk carries parent_id for reranker->parent mapping
        corpus.append({"chunk_id": child_id, "parent_id": parent_chunk_id,
                       "child_ids": [], "chapter": chapter, "section": section,
                       "page": page["page"], "tag": annotate_tags(child_text, keyword_dict),
                       "doc_source": doc_source, "content": child_text})
    # CORE: parent chunk carries child_ids for LLM context expansion
    corpus.append({"chunk_id": parent_chunk_id, "parent_id": None,
                   "child_ids": child_ids, "chapter": chapter, "section": section,
                   "page": page["page"], "tag": annotate_tags(parent_text, keyword_dict),
                   "doc_source": doc_source, "content": parent_text})
```

**占位点**：`paddleocr_vl_parse` 返回固定假页面。真逻辑在分块与 schema。

### 7.3 索引构建 —— build_indexes.py（tokenizer 分离 + 二选一词法）

**学习要点**：**只索引子块**（父块是 LLM 上下文，永不检索）。BM25 用 jieba+自定义词典（保缩写）、Dense 用模型自带 BPE——**分词器分离原则**。词法索引 BM25/Char-BM25 **二选一**。

```python
# build_indexes.py:70-73 —— CORE: 只索引子块
return [c for c in corpus if c["parent_id"] is not None]
```

```python
# build_indexes.py:88-109 —— BM25：jieba + 自定义词典（加载顺序有讲究）
bm25_cfg = config["offline"]["index"]["bm25"]
jieba.load_userdict(bm25_cfg["custom_dict"])   # ADAPT: 必须先加载词典再分词

tokenized_corpus = []
for chunk in child_chunks:
    # CORE: domain tokenizer — keeps abbreviations as single tokens
    tokens = list(jieba.cut(chunk["content"]))
    tokenized_corpus.append(tokens)
bm25 = BM25Okapi(tokenized_corpus)
```

```python
# build_indexes.py:165-184 —— Dense：BGE-M3 自带 BPE，绝不动它的分词
# CORE: pass raw text — model's BPE tokenizer is used internally
vectors = model.encode(texts, batch_size=batch_size,
                       normalize_embeddings=True,   # 归一化后用内积=余弦
                       show_progress_bar=True)
import faiss
index = faiss.IndexFlatIP(vectors.shape[1])   # 归一化后 inner product = cosine
index.add(np.array(vectors, dtype="float32"))
faiss.write_index(index, f"{out_dir}/faiss.index")
```

```python
# build_indexes.py:196-209 —— CORE: 一个词法索引，绝不两个都建
lexical_index = config["online"]["retrieval"]["lexical_index"]
if lexical_index == "char_bm25":
    build_char_bm25_index(child_chunks, config)
else:
    build_domain_bm25_index(child_chunks, config)
build_dense_index(child_chunks, config)   # Dense 永远建
```

**占位点**：无假函数，但 BM25 实现、向量库、Embedding 模型全是 ADAPT 选择点。**词典有没有用，由 offline_eval 的 `tokenization_improvement ≥5pp` 门槛把关**。

### 7.4 多模态图像索引（可选）—— build_image_index.py

**学习要点**：图像用 VL-Embedding 建**独立**索引，通过 `parent_chunk_id` 桥接回文本父块，并从父块继承 `tag` 统一版本过滤。核心是"跨模态桥"不是"混合向量"。

```python
# build_image_index.py:63-83 —— CORE: 用 parent_chunk_id 跨模态桥接
for img in image_records:
    key = (img.get("doc_source"), img["page"])
    candidates = parents_by_loc.get(key, [])
    if candidates:
        img["parent_chunk_id"] = candidates[0]["chunk_id"]   # 桥：图像→文本父块
        img["chapter"] = candidates[0]["chapter"]
        img["section"] = candidates[0]["section"]
```

```python
# build_image_index.py:140-157 —— 图像 id_map：桥 + 过滤标签
id_map = [{
    "image_id": img["image_id"], "image_path": img["image_path"],
    "page": img["page"], "chapter": img.get("chapter", ""), "section": img.get("section", ""),
    "parent_chunk_id": img["parent_chunk_id"],   # CORE: cross-modal bridge
    "description": img.get("description", ""),
    "tag": img.get("tag", []),                   # CORE: version/model filter
} for img in image_records]
```

**占位点**：`encode_images` 返回 `np.random.rand` 假向量。

### 7.5 Q-DOC-Q 数据集生成 —— gen_qdoc_q_pairs.py（LLM 自动造评估集）

**学习要点**：从子块自动生成评估对替代人工标注。**单块 1:1**（每块 3 个 query）+ **邻块 1:N**（跨块问题，最多跨 3 块，验证"多块拼答案"能力）。`gt_doc_ids` 支持 1:N 是评估"能召回全部必需块"的关键。

```python
# gen_qdoc_q_pairs.py:160-174 —— 1:1 单块对 schema
for i in range(queries_per_chunk):
    qtype = query_types[i % len(query_types)]   # 事实型/流程型/故障排查型/定义型轮换
    gen = _llm_generate(content, qtype, config)
    pairs.append({"query": gen["query"],
                  "gt_doc_ids": [chunk["chunk_id"]],     # 1:1
                  "gt_pages": [chunk.get("page", None)],
                  "gt_answer": gen["answer"], "gt_keywords": keywords,
                  "query_type": qtype, "gen_source": "single_chunk",
                  "source_chunk_ids": [chunk["chunk_id"]]})
```

```python
# gen_qdoc_q_pairs.py:179-203 —— 1:N 邻块分组（同 doc 同 page 连续块）
for i, chunk in enumerate(child_chunks):
    key = (chunk.get("doc_source"), chunk.get("page"))
    group = []
    for j in range(i, min(i + max_span, len(child_chunks))):  # max_span=3
        nxt = child_chunks[j]
        if (nxt.get("doc_source"), nxt.get("page")) != key:
            break
        group.append(nxt)
    if len(group) >= 2:
        gid = tuple(c["chunk_id"] for c in group)
        if gid not in seen:      # 去重组 id
            seen.add(gid)
            groups.append(group)
```

```python
# gen_qdoc_q_pairs.py:261-292 —— 贪心 keep-first 语义去重（BGE-M3 余弦阈值 0.85）
for p in pairs:
    vec = embeddings.get(p["query"])
    if vec is None:
        kept.append(p); continue
    if any(_cos(vec, k) > threshold for k in kept_vecs):
        continue                 # 与已保留 query 太像 → 丢弃
    kept.append(p)
    kept_vecs.append(vec)
```

```python
# gen_qdoc_q_pairs.py:307-319 —— 质检：空 query/gt/answer/keywords 一律丢弃
for p in pairs:
    if not (p.get("query") or "").strip():      continue
    if not p.get("gt_doc_ids"):                 continue
    if not (p.get("gt_answer") or "").strip():  continue
    if not p.get("gt_keywords"):                continue
    valid.append(p)
```

**占位点**：`_llm_generate` 是取第一句套模板的确定性占位（真实 LLM 调用需替换）。

### 7.6 数据集校验 —— make_eval_set.py（schema 契约 + 数量门槛）

**学习要点**：评估集是"数据契约"——`REQUIRED_FIELDS` 就是契约。非法直接 abort，不修数据硬跑。

```python
# make_eval_set.py:50-56 —— Q-DOC-Q 必需字段 schema（数据契约）
REQUIRED_FIELDS = [
    "query",        # str     — the user question
    "gt_doc_ids",   # [str]   — ground-truth document chunk IDs (supports 1:N)
    "gt_answer",    # str     — ground-truth answer text
    "gt_keywords",  # [str]   — expected key terms (keyword-level scoring)
    "query_type",   # str     — one of the config's query types
]
```

```python
# make_eval_set.py:137-153 + 197-213 —— CORE: 最少 50 对门槛，不过 abort
min_required = 50; recommended = 80
...
size = size_check(pairs)
if not size["passes_minimum"]:
    print(f"FAIL: {size['count']} < 50 minimum QA pairs. Aborting.")
    return
```

**占位点**：`DEFAULT_PRODUCT_LINES = ["product_line_A/B/C"]` 假产品线，覆盖度分析需按领域替换。

### 7.7 微调训练数据 —— generate_training_data.py（硬负例挖掘，Loop 1 前半）

**学习要点**：微调需要 `(query, positive, negatives)` 三元组。**硬负例 = Top-K 里高分但非 GT 的块**；1:N 时**所有 GT 块互为互斥**，且每个 GT 块各生成一条 triplet。

```python
# generate_training_data.py:87-104 —— 硬负例挖掘：排除全部 GT
# ADAPT: call your hybrid retrieval (BM25/Dense + RRF)
candidates = retrieve_fn(query, top_k=top_k)
# CORE: exclude ALL ground-truth documents from hard negatives.
#       For 1:N queries, all gt_doc_ids must be excluded.
gt_set = set(gt_doc_ids)
hard_negatives = []
for cand in candidates:
    chunk_id = cand["chunk_id"]
    if chunk_id in gt_set:
        continue
    hard_negatives.append(cand)
    if len(hard_negatives) >= num_negatives:
        break
```

**占位点**：`retrieve_fn` 直接 `raise NotImplementedError`——混合检索必须按项目接入。

### 7.8 微调部署决策 —— finetune_embedding.py（deploy/revert 门槛，Loop 1 后半）★

**学习要点**：微调后**必须全量重编码所有块**（微调模型的向量空间不同，基座向量不能复用），重跑 Q-DOC，然后按门槛决策：**≥5pp 部署 / ≤-2pp 回滚 / 中间观望**。这是"评估驱动 + 一次只改一个"的闭环收口。

```python
# finetune_embedding.py:144-183 —— 部署/回滚/观望门槛判断 ★
def make_deploy_decision(baseline_metrics, finetuned_metrics, config):
    """
    Deploy threshold: improvement >= 5pp -> deploy
    Revert threshold: regression >= 2pp  -> revert immediately
    Between thresholds: do NOT deploy — the gain is not worth the operational
    cost of maintaining a fine-tuned model in production.
    """
    deploy_threshold = config["offline"]["finetune"]["deploy_threshold_pp"]
    revert_threshold = config["offline"]["finetune"]["revert_threshold_pp"]
    delta_pp = (finetuned_recall - baseline_recall) * 100   # 转成百分点
    decision = "hold"   # 默认观望
    if delta_pp >= deploy_threshold:
        decision = "deploy"
    elif delta_pp <= -revert_threshold:
        decision = "revert"
    return {"decision": decision, "delta_pp": delta_pp, "reason": reason}
```

```python
# finetune_embedding.py:217-240 —— CORE: 微调后全量重编码，基座向量不可复用
print("Re-encoding ALL chunks with fine-tuned model...")
re_encode_corpus(fine_tuned_model, corpus_path, config)
finetuned_metrics = run_qdoc_eval(config)          # 重跑 Q-DOC
decision = make_deploy_decision(baseline_metrics, finetuned_metrics, config)
```

**占位点**：`finetune_dense_only`/`finetune_unified`/`re_encode_corpus`/`run_qdoc_eval`/`_persist_model` 全 `raise NotImplementedError`（但 docstring 承载了"必须全量重编码"的 CORE 原则）。

---

## 八、在线管线其余 + 代码

### 8.1 查询改写 —— query_rewriter.py（规则为主，LLM 兜底）★

**学习要点**：三类确定性规则改写，**规则跑完没变化才轮到 LLM**。三个机制：缩写补全（给 BM25 双语信号）、子问题拆分（复合问句各自检索）、口语回退（口语→标准术语）。`build_lookup_index` 预建 O(1) 索引 + **protected_phrases** 防"已补全的术语被口语误匹配"。

```python
# query_rewriter.py:144-163 —— 改写1：缩写补全为 "ABBREVIATION (Full Form)"
def keyword_completion(query, index):
    """WHY: BM25 benefits from both forms being present. Documents may use the
    full form while the user typed the abbreviation, or vice versa."""
    matches = _match_keyword(query, index["abbreviations"])
    rewritten = query
    applied = []
    for m in matches:
        abbr, full = m["abbr"], m["full"]
        # Only expand if the abbreviation appears WITHOUT its full form already.
        if abbr.lower() in rewritten.lower() and full.lower() not in rewritten.lower():
            rewritten = rewritten.replace(abbr, f"{abbr} ({full})")
            applied.append(f"{abbr}->{abbr} ({full})")
    if not applied:
        return {"type": "unchanged", "text": query, "source": "rule", "applied": []}
    return {"type": "keyword_completion", "text": rewritten, "source": "rule", "applied": applied}
```

```python
# query_rewriter.py:205-236 —— 改写3：口语回退（带 protected 保护）
for colloq_lower, standard in index["colloquial"].items():
    # Skip if this colloquial phrase is a substring of any protected full form.
    # Such matches are false positives — the phrase appears inside an
    # already-expanded term, not as a genuine colloquial usage.
    if any(colloq_lower in p for p in protected):
        continue
    if colloq_lower in rewritten.lower():
        pattern = re.compile(re.escape(colloq_lower), re.IGNORECASE)
        rewritten = pattern.sub(standard, rewritten)
        applied.append(f"{colloq_lower}->{standard}")
```

```python
# query_rewriter.py:299-328 —— 编排：规则优先，LLM 只在规则零变化时兜底
result = keyword_completion(query, index);  rewrites.append(result);  working_query = result["text"]
split_result = sub_question_split(working_query);  rewrites.append(split_result)
fb_result = fallback_rewrite(working_query, index); rewrites.append(fb_result);  working_query = fb_result["text"]
# Step 4: LLM-assisted rewrite — ONLY when rules made no change.
# CORE: rule-based matching is primary; LLM is the fallback for complex cases.
rule_changed_any = any(r["type"] != "unchanged" for r in rewrites)
if not rule_changed_any and llm_enabled:
    llm_result = _llm_rewrite(query, config)
```

**占位点**：`_llm_rewrite` 硬编码返回占位 JSON；`_match_keyword` 的 fuzzy 分支、`_COMPOUND_CONJUNCTIONS` 连接词表是 ADAPT 待定制。

### 8.2 编排 —— pipeline.py（改写→检索→合并→重排→生成）★

**学习要点**：三个关键决策：**(1)** 路由被降级成**确定性过滤器**（product_model + status 白名单，而不是模型路由——"路由错误会让候选池缩水，精度<50% 就删"）；**(2)** 多子查询结果按 chunk_id 合并、**取最高 RRF 分而非求和**（不同查询的 RRF 分不可直接相加）；**(3)** **重排和生成都用原始查询**，改写只服务检索。

```python
# pipeline.py:134-162 —— 多子查询合并：按 chunk_id 去重，best-score wins
def _merge_candidates(candidate_lists):
    """
    WHY best-score wins (not sum): RRF scores from independent retrieval passes
    are not directly comparable (different query → different rank distribution).
    """
    merged = {}
    for candidates in candidate_lists:
        for c in candidates:
            cid = c["chunk_id"]
            if cid not in merged:
                merged[cid] = dict(c)
            else:
                if c.get("rrf_score", 0) > merged[cid].get("rrf_score", 0):
                    merged[cid] = dict(c)          # 取更高分那份
                merged[cid]["multi_query_hit"] = True   # 记录被多个查询命中
    return list(merged.values())
```

```python
# pipeline.py:263-303 —— CORE: 重排/生成用原始查询，改写只服务检索
with timer.measure("rerank"):
    rerank_result = rerank({"query": query,          # original query, not rewritten
                            "candidates": candidates}, config)
parent_chunks = rerank_result["top_m_parent_chunks"]
with timer.measure("llm"):
    gen_result = generate({"query": query,           # original query, not rewritten
                           "top_m_parent_chunks": parent_chunks}, config)
```

**占位点**：pipeline.py 本身零占位，占位都在它调用的子模块。

### 8.3 LLM 生成 —— llm_generator.py（容错 JSON + 重试 + 引用映射）★

**学习要点**：生成端最容易出"工程故障伪装成质量问题"——JSON 解析失败会全盘污染评估。三层防御：直接 loads → 抽 JSON 块再 loads → 返回 raw 兜底。引用 `^1,2,3^` 反向映射回 chunk 元数据（含 is_legacy 标记）。

```python
# llm_generator.py:221-244 —— CORE: 容错 JSON 解析（工程故障必须先修）
def _fault_tolerant_json_parse(raw):
    """
    LLM output may be malformed — truncated JSON, extra prose, markdown fences,
    trailing commas. We try in order:
      1. Direct json.loads.
      2. Extract the first JSON block and retry.
    Engineering problems (parse errors) must be fixed BEFORE prompt/model
    optimization — they masquerade as quality problems in the eval metrics.
    """
    try:
        return json.loads(raw), "ok"           # 尝试1：直接解析
    except json.JSONDecodeError:
        pass
    block = _extract_json_block(raw)           # 尝试2：抽 JSON 块（含去尾逗号）
    if block != raw:
        try:
            return json.loads(block), "fallback"
        except json.JSONDecodeError:
            pass
    return {"raw_text": raw}, "failed"         # 兜底：带 raw 继续跑
```

```python
# llm_generator.py:267-286 —— 引用 ^1,2,3^ → chunk 元数据
for match in _CITATION_PATTERN.findall(text):
    for num_str in match.split(","):
        num = int(num_str)
        if 1 <= num <= len(parent_chunks) and num not in seen:
            seen.add(num)
            chunk = parent_chunks[num - 1]
            citation = {"ref": str(num), "parent_id": chunk.get("parent_id", ""),
                        "doc_id": chunk.get("doc_id", ""), "page": chunk.get("page", ""),
                        "section": chunk.get("section", ""),
                        "is_legacy": chunk.get("status") == "legacy"}
            citations.append(citation)
```

**占位点**：`_call_llm` 硬编码返回假回答。其余 parse/citation/retry 全真。

### 8.4 多模态查询（可选）—— multimodal_handler.py（阈值降级 + 双通道合并）

**学习要点**：三类查询（纯文本/纯图像/混合）走完全不同的路径，先 `detect_query_type` 避免浪费。**相似度低于阈值 → 降级为"文本搜图"**（用最好图像的 description 当文本查询跑标准管线）——图像索引的 `description` 字段就是为这个降级路径存的。

```python
# multimodal_handler.py:142-171 —— CORE: 相似度阈值判定 + 降级
def _image_path(image, tags, config):
    threshold = config["online"]["multimodal_query"]["similarity_threshold"]
    image_vec = _encode_user_image(image, config)
    image_hits = _image_vector_search(image_vec, top_k, tags, config)
    if not image_hits:
        return [], True  # nothing found -> degrade
    best_similarity = image_hits[0]["similarity"]
    if best_similarity >= threshold:
        return image_hits, False          # 达标：用元数据桥到父块
    # CORE: Below threshold -> degrade to text-search-image.
    return image_hits, True               # 降级：description 当文本查
```

```python
# multimodal_handler.py:174-196 —— 降级路径：description → 标准文本管线
def _text_search_image_fallback(image_hits, tags, config):
    text_query = image_hits[0]["description"]    # 图像描述字段（离线 3.5 存的）
    rewritten = rewrite_query({"query": text_query}, config)
    sq = rewritten["sub_queries"][0]
    retrieved = retrieve({"query": sq, "tags": tags}, config)
    reranked = rerank({"query": text_query, "candidates": retrieved["candidates"]}, config)
    return reranked["top_m_parent_chunks"]
```

```python
# multimodal_handler.py:271-299 —— CORE: 混合查询双通道并行，按 parent_id 去重
merged = {}
for chunk in image_parent_chunks:     # 图像路径先（图像是用户主信号）
    pid = chunk["parent_id"]
    if pid not in merged:
        merged[pid] = {**chunk, "source": "image"}
    else:
        merged[pid]["source"] = "both"
for chunk in text_parent_chunks:      # 文本路径后
    pid = chunk["parent_id"]
    if pid not in merged:
        merged[pid] = {**chunk, "source": "text"}
    else:
        merged[pid]["source"] = "both"
return list(merged.values())
```

**占位点**：`_encode_user_image`（返回 `[0.0]`）、`_image_vector_search`（返回硬编码假命中）。合并逻辑真。

---

## 九、评估与优化循环 + 代码（真实现最多的部分）

> 这套评估体系 = **三层漏斗**（离线管线 → Q-DOC 检索层 → Q-DOC-A 生成层）+ **坏例分类决策树** + **Top-N 扫描** + **Loop 收敛判据**。最值得移植的资产。

### 9.1 离线管线评估 —— offline_eval.py（先隔离数据问题，再测线上）

**学习要点**：在测线上管线之前，先对四件离线产物（索引/召回/分块/词典）逐项打分，**原始检索、不经过改写/路由/重排**——把"数据处理层"质量问题隔离出来。硬门槛（`hard: true`）不过就 block 进入线上评估。

```python
# offline_eval.py:265 —— 与线上同一 RRF 公式（rrf_k 必须一致才可比）
def rrf_fuse(bm25_results, dense_results, rrf_k=60):
    """# CORE: always use RRF — BM25 and Dense scores have different scales
    and cannot be summed. rrf_k must match the online pipeline's value."""
    scores = {}
    for rank, item in enumerate(bm25_results):
        scores[item["chunk_id"]] = scores.get(item["chunk_id"], 0) + 1.0 / (rrf_k + rank + 1)
    for rank, item in enumerate(dense_results):
        scores[item["chunk_id"]] = scores.get(item["chunk_id"], 0) + 1.0 / (rrf_k + rank + 1)
    fused = sorted(scores.items(), key=lambda x: -x[1])
    return [{"chunk_id": cid, "score": sc} for cid, sc in fused]
```

```python
# offline_eval.py:286-302 —— recall@K + CORE: full_recall 只用于 1:N
def compute_recall_at_k(retrieved_ids, gt_ids, k):
    """Recall@K = |Top-K ∩ GT| / |GT|.  For 1:N queries, hit = ANY gt in Top-K."""
    top_k = retrieved_ids[:k]
    hit = len(set(top_k) & set(gt_ids))
    return hit / len(gt_ids) if gt_ids else 0.0

def compute_full_recall_at_k(retrieved_ids, gt_ids, k):
    """# CORE: full_recall only applies to multi_chunk queries (1:N).
    It measures whether ALL required chunks are retrieved."""
    top_k = set(retrieved_ids[:k])
    return 1.0 if all(gid in top_k for gid in gt_ids) else 0.0
```

```python
# offline_eval.py:680 —— CORE: 硬门槛表（hard=true 是死线）
PASS_CRITERIA = {
    "index_coverage_bm25": {"threshold": 1.0, "hard": True},    # 所有子块必须进索引
    "index_coverage_dense": {"threshold": 0.99, "hard": False},
    "rrf_recall_at_64":     {"threshold": 0.85, "hard": False},
    "boundary_violation_rate": {"threshold": 0.0, "hard": True}, # 跨边界分块=0
    "parent_child_mapping_rate": {"threshold": 1.0, "hard": True},
    "tokenization_improvement": {"threshold": 0.05, "hard": False}, # 词典必须提升 BM25≥5pp
}
```

```python
# offline_eval.py:846 —— pass 判断：boundary 越低越好，其余越高越好
if name == "boundary_violation_rate":
    passed = value <= threshold      # 反向指标特例
else:
    passed = value >= threshold
```

**占位点**：`verify_bm25_index`/`verify_dense_index`/`bm25_search`/`dense_search`/`compare_tokenization` 为 ADAPT。

### 9.2 Q-DOC / Q-DOC-A 双层评估 —— qdoc_qdoca_eval.py（检索与生成不可互减）★

**学习要点**：把 RAG 质量拆成两个**不可互减**的打分卡。**Q-DOC**（检索层）算 recall@K + chunk 真实性；**Q-DOC-A**（生成层）用 **6 维 LLM Judge**（关键词命中+内容准确+可信度+完整性+表达+逻辑），连续分映射为 3 级对齐人工评分，**用 Cohen's Kappa ≥0.6 校准 Judge**。

```python
# qdoc_qdoca_eval.py:88-100 —— CORE: 3 级人工评分体系，LLM 连续分映射到同刻度
#   0 = completely wrong    1 = partially correct / incomplete    2 = completely correct
THREE_LEVEL_THRESHOLDS = [(0.8, 2), (0.4, 1), (0.0, 0)]
def map_to_three_level(score):
    """Mapping: [0.8, 1.0] -> 2, [0.4, 0.8) -> 1, [0, 0.4) -> 0"""
    for threshold, level in THREE_LEVEL_THRESHOLDS:
        if score >= threshold:
            return level
    return 0
```

```python
# qdoc_qdoca_eval.py:205 —— WHY 文档级 recall 而非 chunk 级 MRR
def compute_chunk_recall_at_k(retrieved_ids, gt_ids, k):
    """WHY document-level recall (not chunk-level MRR): in domain RAG what
    matters at the retrieval stage is whether the GT document SURVIVES to the
    reranker - its exact rank within Top-K is the reranker's job, not retrieval's."""
    top_k = retrieved_ids[:k]
    hit = len(set(top_k) & set(gt_ids))
    return hit / len(gt_ids) if gt_ids else 0.0
```

```python
# qdoc_qdoca_eval.py:268 —— 关键词命中率：廉价确定信号，补 LLM Judge 的软分
def compute_keyword_hit_rate(answer, gt_keywords):
    """WHY keyword hit (in addition to LLM-judge): keyword presence is a cheap,
    deterministic signal that catches the most common generation failure - the
    LLM omitting a key entity. It cannot be gamed by a fluent-but-wrong answer."""
    if not gt_keywords:
        return 1.0
    hits = sum(1 for kw in gt_keywords if kw.lower() in answer.lower())
    return hits / len(gt_keywords)
```

```python
# qdoc_qdoca_eval.py:509 —— CORE: LLM composite = 各维 3 级分取最小（保守）
# 最差的一维决定整体质量，然后和人工分比 Kappa
llm_levels = [entry["content_accuracy_three_level"], entry["credibility_three_level"],
              entry["completeness_three_level"], entry["expression_three_level"],
              entry["logical_three_level"]]
llm_composite = min(llm_levels)
```

```python
# qdoc_qdoca_eval.py:443 —— Cohen's Kappa = (p_o - p_e) / (1 - p_e)
def compute_cohen_kappa(human_scores, llm_scores):
    """# CORE: Kappa >= 0.6 means Judge is sufficiently aligned with humans.
    Kappa < 0.4 means Judge is unreliable - revise judge prompts.
    Requires >= 30 expert queries for stable estimation."""
    agreed = sum(1 for h, l in zip(human_scores, llm_scores) if h == l)
    p_o = agreed / n
    human_counts = Counter(human_scores); llm_counts = Counter(llm_scores)
    p_e = sum((human_counts.get(level, 0) / n) * (llm_counts.get(level, 0) / n)
              for level in [0, 1, 2])
    return (p_o - p_e) / (1.0 - p_e)
```

**占位点**：6 个 LLM-judge 函数、`retrieve_and_rerank`、`generate_answer` 为 ADAPT。

### 9.3 坏例分类与瓶颈定位 —— bad_case_analyzer.py（决策树）★

**学习要点**：把"哪些坏"升级成"为什么坏、进哪个循环"。**六类 Bad Case**：tokenizer / fusion / routing / prompt / engineering / judge_alignment。分类优先级极讲究——**engineering 第一**（解析失败会伪装成 prompt 问题）、**judge 对齐第二**（Judge 自己错就不能信分数）、再查 recall（哪个索引丢的）→ routing → rerank → 生成 6 维。瓶颈 = 占多数的那一类，但 **只要存在 engineering 就必须先修它**。

```python
# bad_case_analyzer.py:142 —— CORE: 六类固定命名，下游决策表依赖这些字符串
TOKENIZER_ISSUE       = "tokenizer_issue"
FUSION_ISSUE          = "fusion_issue"
ROUTING_ISSUE         = "routing_issue"
PROMPT_ISSUE          = "prompt_issue"
ENGINEERING_ISSUE     = "engineering_issue"
JUDGE_ALIGNMENT_ISSUE = "judge_alignment_issue"
```

```python
# bad_case_analyzer.py:183-268 —— classify_bad_case 决策树骨架
# CORE: engineering FIRST - a parse failure produces a garbage answer that
#       LOOKS like a prompt problem. We must not route these to Loop 2 —
#       they'd be "fixed" by coincidence, not by cause.
if record.get("parse_error"):
    return _result(ENGINEERING_ISSUE, "...technical, not quality...", "engineering_fix")

# --- Stage 1: retrieval recall (post-fusion, pre-rerank) ---
if record["recall_at_k"] < LOW_RECALL_THRESHOLD:
    if record.get("bm25_recall", 1.0) < LOW_RECALL_THRESHOLD:
        # BM25 missed but Dense hit -> BPE split domain abbreviation
        return _result(TOKENIZER_ISSUE, "update keyword dictionary / custom dict", "loop1_tokenizer_or_finetune")
    if record.get("dense_recall", 1.0) < LOW_RECALL_THRESHOLD:
        # Dense missed -> embedding weak on domain terms
        return _result(TOKENIZER_ISSUE, "consider fine-tuning", "loop1_finetune")
    # Both indexes had signal but fusion lost GT
    return _result(FUSION_ISSUE, "verify RRF k / lexical index selection", "loop3_fusion")

# --- Stage 2: routing ---
if record.get("routing_used") and record.get("routing_hit_rate", 1.0) < 0.5:
    return _result(ROUTING_ISSUE, "remove routing or switch to LLM-based", "loop3_routing")

# --- Stage 3: rerank ---
if record.get("rerank_hit") is False:
    return _result(FUSION_ISSUE, "check reranker model or increase Top-N", "loop3_reranker")

# --- Stage 4: generation (6-dimensional sub-classification) ---
return _classify_generation_failure(record)
```

```python
# bad_case_analyzer.py:352 —— 生成 6 维子分类，安全优先排序
# CORE: Priority order is safety-critical first:
#   credibility -> content_accuracy -> completeness -> keyword_hit -> expression -> logical
if credibility < CREDIBILITY_THRESHOLD:   # 幻觉，最严
    return _result(PROMPT_ISSUE, "...not grounded in context...", "loop2_prompt", sub_category="hallucination")
if accuracy < CONTENT_ACCURACY_THRESHOLD:
    return _result(PROMPT_ISSUE, "...wrong content...", "loop2_prompt", sub_category="wrong_content")
if completeness < COMPLETENESS_THRESHOLD:
    return _result(PROMPT_ISSUE, "...incomplete...", "loop2_prompt", sub_category="incomplete")
if khr < KEYWORD_HIT_THRESHOLD:
    return _result(PROMPT_ISSUE, "...missing key entities...", "loop2_prompt", sub_category="missing_keywords")
```

```python
# bad_case_analyzer.py:457 —— 瓶颈 = 多数类，但 engineering 永远优先
# CORE: the bottleneck is the DOMINANT category (most Bad Cases).
# CORE: engineering blocker rule - if ANY engineering issues exist, they
# must be fixed FIRST, regardless of count. A single parse failure can
# produce dozens of phantom "prompt issues" downstream.
has_engineering = counts.get(ENGINEERING_ISSUE, 0) > 0
suggested_loop = "engineering_fix" if has_engineering else loop_for_category[dominant]
```

```python
# bad_case_analyzer.py:533 —— Loop1 收敛：连续 2 轮 Recall@5 增益 < 阈值就停
def check_loop1_convergence(history, config):
    """# CORE: 2 consecutive iterations with Top-5 gain < loop1_convergence_pp
    -> fine-tuning has converged, redirect effort elsewhere."""
    threshold = config["eval"]["loop1_convergence_pp"] / 100.0
    window = 2
    if len(history) < window + 1:
        return False                       # 需要 window+1 轮才有 window 个增益
    recent = history[-(window + 1):]
    gains = [recent[i]["recall_at_5"] - recent[i-1]["recall_at_5"]
             for i in range(1, len(recent))]
    return all(g < threshold for g in gains)
```

**占位点**：`_load_per_query_eval` 一个假实现；分类/瓶颈/收敛逻辑全真。

### 9.4 Top-N 参数扫描 —— recall_sweep.py（找 recall 拐点定 top_n）

**学习要点**：K 太小 GT 到不了 reranker，K 太大白付延迟。**一次检索到 max(K) 再逐 K 截断**（避免重复检索和融合 tie 的不确定性），扫 marginal gain **拐点**（plateau = 边际增益 < 0.5pp 的第一个 K），再按领域钳制到推荐区间（通用 50-100 / 窄域 20-50）。

```python
# recall_sweep.py:147 —— CORE: 检索一次到 max_k，逐 K 截断 + 三轨 recall
max_k = max(k_values)
per_query = [(hybrid_retriever(e["query"], top_n=max_k, config=config), e["gt_doc_ids"])
             for e in eval_set]
prev_recall = 0.0
for k in k_values:
    ...
    r = compute_recall_at_k(retrieved_ids, gt_ids, k)
    ...
    results.append({"K": k, "recall_at_k": mean_recall,
                    "rerank_latency_ms": mean_latency,
                    "marginal_gain": mean_recall - prev_recall})
    prev_recall = mean_recall
```

```python
# recall_sweep.py:227 —— 拐点检测：边际增益 < 阈值 = 平台期
def detect_plateau(results, plateau_threshold=0.005):
    """# CORE: Gains plateau by N=200 - beyond that, you pay latency for zero
    accuracy gain. We pick the FIRST K entering the plateau."""
    for row in results:
        if row["marginal_gain"] < plateau_threshold:
            return row["K"]          # 第一个进入平台期的 K
    return results[-1]["K"]
```

```python
# recall_sweep.py:254 —— CORE: 拐点钳制到领域推荐区间
narrow_domains = {"semiconductor_equipment", "medical", "legal", "financial"}
if domain in narrow_domains:
    low, high = 20, 50      # 窄域：候选池同质，reranker 噪声少，可小
else:
    low, high = 50, 100     # 通用
return max(low, min(high, plateau_k))
```

**占位点**：`hybrid_retriever`、`measure_rerank_latency` 为 ADAPT；核心扫描/拐点/推荐全真。

---

## 十、增量知识管理（纯方法论，无代码）

**文档级三类分诊**（一次摄入一个决策，不做 chunk 级 diff）：
- **替换**：同型号升级、旧内容全废 → 删旧写新
- **并行**：不同型号、新旧各自有效 → 只写新、旧不动
- **Legacy**：同型号升级但旧版有参考价值 → 旧块标记 legacy、检索默认过滤、要历史时放宽过滤 + prompt 加版本警告

**双层元数据**：
- 文档级 → 关系库（版本链 supersedes/事务/复杂查询是关系库强项）
- chunk 级 → 向量库标量字段（检索过滤/父子映射/溯源）

**关键词词典 append-only**：删文档不删词典词条——用户查询可能还在用。字典是全局共享资源。

**作用**：RAG 上线后的工程管理。RAGFlow 和 queryforge 都缺这一块的完整方法论。

---

## 十一、学习路径与落地对照

```
建立地图 → 本文一、二节（30 分钟）
方法论 → 三、四、五节（核心原则 + 配置 + prompt）
代码 → 六~九节（算法真代码 + 占位点识别）
运营 → 十节（增量管理）
落地 → 对照 queryforge / RAGFlow 抄缺的部分
```

| 决策 | RAG-BUILD-SKILLS | RAGFlow | queryforge |
|------|-----------------|---------|------------|
| 混合检索 | BM25/Char + Dense + RRF | MatchText+Dense+Fusion(weighted_sum) | 向量+pg_jieba+RRF |
| 重排 | 最高 ROI | rerank_with_knn/by_model | gte-rerank |
| 父子分块 | 256/1024 | mom 块 | 未用 |
| 领域词典 | dict + 改写 | huqite + term_weight | pg_jieba |
| 多查询扩展 | ❌ 没有 | ❌ 经典路径没有 | ✅ 可关 |
| **评估循环** | ✅ 三层+坏例 | 部分（Benchmark） | 有 eval |
| **增量管理** | ✅ 三类分诊 | 部分 | 未用 |

**一句话心法**：**RAG-BUILD-SKILLS 给你的不是代码，是"判断标准 + 数学 + 数据契约 + 错误分类法"**——RRF 公式、recall@K、坏例决策树是真实现可抄；
BM25/向量/LLM Judge 是占位要自己填。最该移植的资产是**评估循环**（Q-DOC/Q-DOC-A + 坏例分类 + 收敛判据）和**增量知识管理**（三类分诊），这两块 RAGFlow 没讲透。
