# Day 21 - RAG 项目演示与复盘

## 项目一句话

这是一个本地 RAG 知识库问答 API，把学习笔记和项目资料入库后，通过
`POST /rag/ask` 返回答案草稿、引用来源、request_id 和召回排查信息。

## 5 分钟演示脚本

### 1. 项目目标

这个项目解决的是企业知识库问答的最小闭环问题：用户不用知道底层怎么切 chunk、
怎么检索、怎么拼上下文，只要通过 API 提交问题，就能拿到答案和引用来源。

### 2. 离线入库

Day 17 负责离线入库：读取学习笔记和项目文档，做清洗、切分、学习版 embedding，
然后把 chunk、向量、来源、位置和 metadata 写入 SQLite 索引。

### 3. 在线问答

Day 18 和 Day 19 负责在线检索：用户问题会转成同一套学习版向量，从索引中召回 top-k
chunk，并返回 citations。Day 19 额外做了 top-k 和 query rewrite 的召回实验。

### 4. API 化

Day 20 把本地问答能力封装成 FastAPI：

```text
GET /health
POST /rag/ask
```

`/rag/ask` 返回的不只是 answer，还包括 citations、request_id、confidence、
cannot_answer_reason 和 latency_ms，方便前端展示、日志追踪和问题排查。

### 5. 成功样例

推荐演示问题：

```text
RAG 为什么要返回引用来源？
```

演示时重点看：

- answer 是否有内容
- citations 是否指向 Day 18 相关笔记
- request_id 是否存在
- confidence 是否能帮助判断召回相关性

### 6. Bad Case

推荐讲 Day 19 的 bad case：

```text
结构化输出为什么要校验 JSON 字段？
```

这个问题在召回实验里没有命中预期来源，说明当前学习版 embedding 和检索策略还不够强。
后续可以通过扩大词表、混合检索、query rewrite、rerank 和更合理的 chunk 策略优化。

## 当前边界

- 目前使用关键词计数模拟 embedding，不能等同于真实语义向量。
- answer 还是答案草稿，没有接真实 LLM。
- user_id 和 business_domain 已预留，但没有做真实权限过滤。
- 评测集还小，需要扩展到更多业务问题、拒答问题和权限问题。

## 复盘结论

这个项目的价值不是模型能力有多复杂，而是形成了 RAG 的工程闭环：

```text
资料治理 -> 入库 -> 检索 -> 引用 -> API -> 回归测试 -> bad case 优化
```

面试或项目展示时，要主动讲清楚引用、边界和 bad case。这样能体现自己理解的是生产系统，
不是只会跑一个本地 Demo。
