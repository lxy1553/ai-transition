# RAG 问答 API 演示项目

> 覆盖学习阶段：Day 17 知识入库、Day 18 检索与引用、Day 19 召回优化、Day 20 API 接口化、Day 21 项目收口。

这个项目把 Day 18 的本地 RAG 问答脚本封装成 FastAPI API。

它练的是：RAG 能力如何从“自己在命令行跑”变成“外部系统可以通过 HTTP 调用”。

## 项目目标

这个项目模拟一个企业知识库问答服务：

- 离线侧把学习笔记和项目资料切分、向量化并写入 SQLite 索引。
- 在线侧接收用户问题，从索引里召回相关 chunk。
- API 返回答案草稿、引用来源、request_id、confidence 和排查信息。

它不是为了做一个复杂模型 Demo，而是练习生产 RAG 的最小工程闭环：

```text
文档资料 -> 清洗切分 -> embedding -> 索引 -> 检索 -> citations -> API -> 回归测试
```

## 生产映射

| 本地能力 | 生产含义 |
|----------|----------|
| `POST /rag/ask` | 知识库问答服务入口 |
| `question` | 用户原始问题 |
| `top_k` | 控制召回 chunk 数量 |
| `citations` | 用户核对依据、研发排查问题 |
| `request_id` | 线上日志追踪和问题定位 |
| `confidence` | 粗略判断召回相关性 |
| `cannot_answer_reason` | 明确无答案原因，避免模型胡编 |

## 架构流程

```text
Day 17 离线入库
  读取 notes/docs/projects
  -> 清洗正文
  -> 切成 chunk
  -> 生成学习版 embedding
  -> 写入 rag_index.sqlite

Day 18/19 在线检索
  用户问题
  -> 转成同一套学习版 embedding
  -> 计算相似度
  -> 取 top-k
  -> 返回引用来源
  -> 用固定问题做召回评估

Day 20 API 化
  POST /rag/ask
  -> 参数校验
  -> 检索 top-k chunk
  -> 组装 answer、citations、request_id、confidence
  -> 返回稳定 JSON
```

## 前置步骤

先生成 Day 17 知识库索引：

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day17_rag_ingestion/main.py
```

## 启动 API

```bash
uvicorn projects.day20_rag_api.main:app --reload --port 8020
```

打开接口文档：

```text
http://127.0.0.1:8020/docs
```

## 健康检查

```bash
curl http://127.0.0.1:8020/health
```

## 问答接口

```bash
curl -X POST http://127.0.0.1:8020/rag/ask \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "RAG 知识入库怎么设计？",
    "top_k": 3,
    "user_id": "local_user",
    "business_domain": "ai_transition"
  }'
```

响应会包含：

```json
{
  "request_id": "req_xxx",
  "question": "RAG 知识入库怎么设计？",
  "answer": "基于当前知识库，相关资料主要来自以下片段：...",
  "citations": [
    {
      "ref": 1,
      "chunk_id": "chunk_xxx",
      "doc_id": "doc_xxx",
      "source_path": "notes/day17_rag_ingestion.md",
      "title": "Day 17 - RAG 知识入库",
      "position": 2,
      "score": 0.9
    }
  ],
  "retrieved_chunks": [],
  "confidence": 0.9,
  "cannot_answer_reason": null,
  "latency_ms": 5
}
```

## 本地回归

```bash
cd /Users/lxy/Documents/ai_transition/projects/day20_rag_api
python3 regression.py
```

输出：

```text
projects/day20_rag_api/output/regression_results.json
```

## 今日检查标准

- `/health` 能返回 `index_ready=true`
- `/rag/ask` 能返回 `answer`
- 响应里包含 `citations`
- 响应里包含 `request_id`
- 5 个回归问题能跑完并生成结果文件

## 固定测试问题

1. RAG 知识入库怎么设计？
2. RAG 为什么要返回引用来源？
3. SQL 解释助手能检查哪些风险？
4. query rewrite 解决什么问题？
5. RAG 召回质量差怎么排查？

## 常见失败场景

| 场景 | 表现 | 排查方向 |
|------|------|----------|
| Day 17 索引不存在 | `/health` 返回 `index_ready=false` 或问答接口 503 | 先运行入库脚本 |
| 知识库没有相关资料 | `citations` 为空，`cannot_answer_reason=no_relevant_chunks` | 补资料或调整入库范围 |
| 召回结果不相关 | answer 有内容但 citations 和问题关系弱 | 检查 query、chunk、top-k、rewrite 和 rerank |
| 引用资料过期 | citations 指向旧文档 | 增加版本管理和增量更新 |
| top-k 太小 | 正确资料没进入上下文 | 提高 top-k 或引入 rerank |
| top-k 太大 | 噪声变多，答案容易发散 | 限制上下文并做去重、重排 |

## 当前限制

- embedding 是学习版关键词向量，不是真实语义 embedding。
- 还没有接真实 LLM，answer 是基于召回 chunk 的答案草稿。
- 权限、业务域和用户身份字段已经预留，但还没有做真实权限过滤。
- 还没有接缓存、限流、监控和服务部署。
- 评测集规模较小，当前只覆盖 5 个回归问题和 Day 19 的小规模召回实验。

## 后续优化方向

- 替换为真实 embedding 模型和向量数据库。
- 增加 query rewrite、混合检索和 rerank。
- 增加权限过滤、敏感信息控制和访问审计。
- 接入真实 LLM，并要求只基于 citations 生成答案。
- 扩大评测集，增加拒答、权限、资料冲突和 bad case 样例。
- 增加 Docker、配置管理、日志监控和接口测试。

## 5 分钟演示流程

1. 说明项目目标：把本地 RAG 脚本变成可调用的知识库问答 API。
2. 说明离线入库：Day 17 负责文档接入、切分、embedding 和索引。
3. 说明在线问答：Day 18/19 负责检索、引用和召回优化。
4. 启动 Day 20 API，调用 `/health` 和 `/rag/ask`。
5. 展示 `citations`，说明如何排查答案依据。
6. 展示一个 bad case，说明后续会用 query rewrite、混合检索和 rerank 优化。
