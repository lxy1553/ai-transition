# QueryForge 阶段 F：可观测（监控 + 追踪）

> **这是生产级的"眼睛"**——Prometheus 指标 + Langfuse 追踪 + 结构化日志。
> 对比你 ai_assistant：你的没监控，QueryForge 有完整可观测。
>
> **代码位置**：`app/core/metrics.py` + `app/core/observability.py` + `app/core/logging.py`

---

## 三问

- **Q1 解决什么问题**：出问题能发现（指标）、能排查（追踪）、能关联（日志）
- **Q2 数据流哪一环**：贯穿全程——每次请求记录指标，每步调用追踪
- **Q3 删掉会怎样**：出问题不知道，无法监控，面试讲不了"可观测"

---

## 一、Prometheus 指标（metrics.py）

```python
# 6 类指标（挂到 /metrics，Grafana 展示）

# ① 请求量 / 时延（按结果 status 区分）
query_requests_total = Counter("qf_query_requests_total", "请求总数", ["status"])
query_latency_seconds = Histogram("qf_query_latency_seconds", "端到端时延", ["status"])

# ② LLM 调用时延 / 次数（按节点 + 状态）
llm_latency_seconds = Histogram("qf_llm_latency_seconds", "LLM 时延", ["node"])
llm_calls_total = Counter("qf_llm_calls_total", "LLM 次数", ["node", "status"])

# ③ 检索时延（按通道）
retrieval_latency_seconds = Histogram("qf_retrieval_latency_seconds", "检索时延", ["channel"])

# ④ SQL 执行 / 自纠错
sql_exec_total = Counter("qf_sql_exec_total", "SQL 执行结果", ["status"])
sql_self_correct_total = Counter("qf_sql_self_correct_total", "SQL 自纠错次数")

# ⑤ 缓存命中率
cache_total = Counter("qf_cache_total", "缓存访问", ["result"])  # hit | miss

# ASGI 子应用：挂到 /metrics
metrics_app = make_asgi_app()
```

**大白话**：6 类指标——请求量/时延、LLM 调用、检索时延、SQL 结果、自纠错次数、缓存命中率。**Grafana 画成看板**，一眼看出系统状态。

**关键指标能回答的问题**：
- 缓存命中率低？→ 缓存设计有问题
- 自纠错次数高？→ SQL 生成老错
- LLM 时延高？→ 模型太慢/并发太高

---

## 二、Langfuse 追踪（observability.py）

```python
# 每次请求挂 Langfuse handler → 链路追踪（能看到每一步调用了什么）
async def get_langfuse_handler():
    ...
    # 未配置时降级为 None（优雅降级）
```

**大白话**：Langfuse = 链路追踪——能看到一次请求里 LLM 调了几次、每次花了多少 token、走了哪些节点。**出问题能逐步回放**。

---

## 三、结构化日志 + correlation-id（logging.py）

```python
# structlog 结构化日志 + correlation-id（关联同一次请求的所有日志）
logger.info("graph_invoke_failed", category=err.category)
# → 输出 {"event": "graph_invoke_failed", "category": "llm_timeout", "timestamp": ...}
```

**大白话**：结构化日志（JSON 格式）+ 关联 ID——同一次请求的所有日志带同一个 ID，**能串起来排查**。

---

## 四、优雅降级（可观测相关）

```python
# Redis/Langfuse/rerank/ES/语义缓存 未配置或出错时一律降级为 no-op
# 调试时注意"功能静默跳过"可能是降级而非 bug
```

**大白话**：可选组件（监控/缓存）挂了不阻断主链路——**可用性 > 完美**。

---

## 五、对照 ai_assistant 的改造动作

```python
# ① 加基础指标（最简单：计数 + 时延）
from prometheus_client import Counter, Histogram
request_total = Counter("ask_requests_total", "请求总数", ["status"])
latency = Histogram("ask_latency_seconds", "时延")

# ② 每次 ask 记录
def ask(query, user_role):
    start = time.perf_counter()
    answer = pipeline.ask(query, user_role)
    request_total.labels(status="ok" if answer.success else "failed").inc()
    latency.observe(time.perf_counter() - start)
    return answer

# ③ 加日志（structlog）
logger.info("ask", query=query, role=user_role, success=answer.success)
```

**改造要点**：加指标（请求数/时延）+ 日志——最小可观测。

---

## 六、小结

| 学到 | 一句话 |
|------|--------|
| Prometheus 指标 | 请求/LLM/SQL/缓存/自纠错 6 类 |
| Langfuse 追踪 | 链路回放，逐步排查 |
| 结构化日志 | JSON 格式 + correlation-id |
| 优雅降级 | 可选组件挂了不影响主链路 |
| /metrics | Prometheus 拉取端点 |

> **核心心法**：可观测 = 指标（数字）+ 追踪（链路）+ 日志（详情）。你的 ai_assistant 最该先加**基础指标 + 日志**——面试能讲"我监控了什么"，出问题能排查。
