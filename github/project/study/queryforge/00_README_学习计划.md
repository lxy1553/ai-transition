# QueryForge 学习计划（生产级 Text-to-SQL 工程化）

> **项目**：jarry126/queryforge-test2sql（FastAPI + LangGraph + RAG）
> **为什么学**：Vanna 学 Agent 编排，QueryForge 学**生产工程化**（SQL安全/熔断/限流/缓存/评测）。
> **方法**：不套 vanna 阶段，按 queryforge 自身架构分**5 主干 + 6 阶段**，核心是主干代码拆解。

---

## 第一部分：5 个主干（核心代码拆解）

| 主干 | 内容 | 代码位置 |
|------|------|---------|
| **主干1_LangGraph编排** | 图/节点/条件边/自纠错/checkpointer | graph.py + state.py + nodes/ |
| **主干2_RAG检索** | 三套语料/schema语料/混合检索 | retriever.py + schema_corpus.py |
| **主干3_SQL安全执行** | sqlglot真解析/只读沙箱/超时 | guard.py + executor.py |
| **主干4_编排服务** | 缓存短路/错误分类/API | text2sql.py + query.py |
| **主干5_生产韧性** | 熔断/重试/限流/缓存/降级 | resilience.py + limiter.py + cache.py |

## 第二部分：6 个阶段（产品级扩展）

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| **阶段B_评测实验** | 执行准确率/难度分桶/A/B/消融 | ★★★ |
| **阶段A_多轮会话鉴权** | JWT登录/会话/多轮历史 | ★★★ |
| **阶段C_数据入库** | 切块/向量化/入库 | ★★ |
| **阶段D_部署迁移** | Docker/alembic/Makefile | ★★ |
| **阶段F_可观测** | Prometheus/Langfuse/日志 | ★★ |
| **阶段E_前端** | 零构建单页/会话/聊天 | ★ |

---

## 三个最该记住的认知

1. **SQL 安全用真解析**：正则能被绕过，sqlglot 真解析识别真实语句（命门）
2. **自纠错是核心**：生成→校验→重试（带错误回喂）显著提准
3. **RAG 不是万能的**：README 实验证明跨库下 RAG 不一定提升，few-shot 最稳定

---

## 落地顺序（对照 ai_assistant）

```
★★★ SQL 安全升级（sqlglot）+ 自纠错循环 + 缓存
★★  熔断 + 重试 + few-shot + API 层 + 限流 + 评测分桶
★★  多轮会话 + 数据入库 + 部署 + 可观测
★   前端
```

## 当前进度

| 文件 | 状态 |
|------|------|
| 主干1-5 | ✅ |
| 阶段A-多轮会话鉴权 | ✅ |
| 阶段B-评测实验 | ✅ |
| 阶段C-数据入库 | ✅ |
| 阶段D-部署迁移 | ✅ |
| 阶段E-前端 | ✅ |
| 阶段F-可观测 | ✅ |
