# JD 分析：AI Agent 应用开发工程师

> 核心要求：将实验产品进行工程化落地

---

## 一、JD 逐条拆解

| JD 要求 | 真实含义 | 匹配度 |
|---------|---------|--------|
| Python + Java | Python 写 Agent 逻辑，Java 写后端服务 | Python ✅ / Java 待加强 |
| Linux + Git | 服务器开发日常 | ✅ |
| LangChain、RAG 项目经验 | 核心考察点，面试深挖 | ✅ 信贷风控项目可包装 |
| 至少一种 Web 框架 | FastAPI / Spring Boot | ✅ FastAPI 学习笔记 |
| 常用数据库、中间件 | MySQL + Redis + Kafka | ⚠️ 中间件实战不足 |
| 工程化落地 | 日志、监控、容错、CI/CD、Docker | ⚠️ 需补充 Docker |
| 跟踪最新技术 | MCP、A2A、Agent Skills | ✅ 310 题题库覆盖 |

---

## 二、端到端 Agent Demo 构建指南

### 2.1 为什么需要

面试官问"你做过 Agent 吗"，需要的是**能跑、能演示、能讲清架构**的项目，不是"我看过文章"。

### 2.2 基于现有项目改造

你的信贷风控系统已有完整的数据链路，缺的只是"自然语言提问 → Agent 自动执行"这一层。

```
用户: "昨天的逾期率是多少？哪些渠道表现最差？"
       │
       ▼
  ┌─────────────────────────────────────┐
  │  Agent 大脑（LLM）                    │
  │  ├─ 意图识别：判断是"离线指标查询"      │
  │  └─ 任务规划：拆成①查逾期率 ②按渠道排名  │
  └──────────────┬──────────────────────┘
                 │ Function Call
                 ▼
  ┌─────────────────────────────────────┐
  │  工具层                               │
  │  ├─ NL2SQL       → DWS/ADS 宽表      │
  │  ├─ 指标查询      → ADS 数据产品       │
  │  ├─ 血缘追溯      → SchemaRegistry    │
  │  └─ RAG 检索      → 项目文档/口径解释   │
  └──────────────┬──────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │  结果解释（LLM）                       │
  │  "昨天逾期率 3.2%，渠道 C 最高 5.1%"    │
  └─────────────────────────────────────┘
```

### 2.3 四步实现

#### Step 1：选定最小可行场景（1 天）

从 NL2SQL 题库中选 3 类查询做 MVP：
- "查 X 指标" → NL2SQL 查询
- "X 指标为什么异常" → RAG 检索口径解释
- "这个字段什么意思" → Schema Catalog 查询

#### Step 2：用 LangGraph 搭 Agent 骨架（2 天）

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    query: str           # 用户输入
    intent: str          # 意图分类结果
    sql: str             # NL2SQL 生成的 SQL
    result: list         # 查询结果
    context: str         # RAG 检索到的上下文
    final_answer: str    # 最终回答

# ── 节点定义 ──

def classify_intent(state: AgentState) -> AgentState:
    """用 LLM 判断用户意图：指标查询 / 口径解释 / 血缘追溯"""
    prompt = f"""用户问题：{state['query']}
    
判断属于哪类：
1. 离线指标查询 — 需要跑 SQL 获取具体数值
2. 口径解释 — 需要查文档解释指标定义
3. 血缘追溯 — 需要查字段的来源和加工逻辑
4. 闲聊 — 不需要查数据
    
只返回数字 1-4。"""
    
    response = llm.invoke(prompt)
    intent_map = {"1": "indicator", "2": "definition", "3": "lineage", "4": "chat"}
    state["intent"] = intent_map.get(response.strip(), "chat")
    return state


def generate_sql(state: AgentState) -> AgentState:
    """NL2SQL：自然语言 → SQL，必须带 Schema 约束"""
    schema = get_schema_catalog(user=state.get("user"), intent=state["intent"])
    prompt = f"""根据以下表结构生成 SQL：
    
表结构：{schema}
用户问题：{state['query']}

要求：
- 必须带 dt='{today()}' 分区过滤
- 必须带 LIMIT 100
- 只允许 SELECT 语句
- 不允许 JOIN 超过 3 张表
"""
    state["sql"] = llm.invoke(prompt)
    return state


def safety_check(state: AgentState) -> AgentState:
    """每条 SQL 执行前必须通过安全检查"""
    sql = state["sql"]
    checks = [
        ("包含危险操作", not re.search(r'\b(DROP|DELETE|TRUNCATE|ALTER)\b', sql, re.I)),
        ("缺少分区过滤", 'dt=' in sql),
        ("超过 JOIN 限制", sql.upper().count('JOIN') <= 3),
        ("缺少行数限制", 'LIMIT' in sql.upper()),
    ]
    for name, passed in checks:
        if not passed:
            raise SafetyError(f"安全检查失败: {name}")
    return state


def execute_sql(state: AgentState) -> AgentState:
    """执行 SQL，带超时和行数控制"""
    try:
        state["result"] = run_with_timeout(state["sql"], timeout_seconds=10, max_rows=100)
    except TimeoutError:
        state["final_answer"] = "查询超时，请缩小查询范围后重试。"
    return state


def generate_answer(state: AgentState) -> AgentState:
    """RAG 检索 + 结果格式化 → 自然语言回答"""
    if state.get("final_answer"):
        return state
    
    # RAG 检索相关口径和上下文
    context_docs = rag_search(state["query"], top_k=3)
    
    prompt = f"""你是数据分析助手。根据以下信息回答用户问题：
    
用户问题：{state['query']}
查询结果：{state['result']}
相关口径：{context_docs}

要求：
- 用自然语言解释数据，不要直接展示 SQL
- 如果有异常值，主动指出
- 如果数据不足以回答问题，诚实说明
"""
    state["final_answer"] = llm.invoke(prompt)
    return state


# ── 组装工作流 ──

def build_agent():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("classify", classify_intent)
    workflow.add_node("nl2sql", generate_sql)
    workflow.add_node("safety", safety_check)
    workflow.add_node("execute", execute_sql)
    workflow.add_node("answer", generate_answer)
    
    workflow.set_entry_point("classify")
    
    # 条件分支：只有"指标查询"才走 NL2SQL
    workflow.add_conditional_edges("classify", lambda s: s["intent"], {
        "indicator": "nl2sql",
        "definition": "answer",   # 直接 RAG 回答
        "lineage": "answer",      # 直接 RAG 回答
        "chat": "answer",         # 直接 LLM 回答
    })
    
    workflow.add_edge("nl2sql", "safety")
    workflow.add_edge("safety", "execute")
    workflow.add_edge("execute", "answer")
    workflow.add_edge("answer", END)
    
    return workflow.compile()
```

#### Step 3：加安全护栏（1 天）

生产环境面试必问，Demo 要展示的不只是"能跑"，更是"知道哪里会出问题"。

```python
# 安全检查清单
class SafetyGuard:
    @staticmethod
    def check_sql(sql: str, user_role: str) -> list[str]:
        """返回拦截原因列表，空列表 = 通过"""
        violations = []
        
        # 1. 禁止操作类 SQL
        if re.search(r'\b(DROP|DELETE|TRUNCATE|ALTER|INSERT|UPDATE)\b', sql, re.I):
            violations.append("禁止执行写操作")
        
        # 2. 分区过滤
        if 'dt=' not in sql and 'WHERE' in sql.upper():
            violations.append("缺少分区过滤条件，会导致全表扫描")
        
        # 3. 行数限制
        if 'LIMIT' not in sql.upper():
            violations.append("缺少 LIMIT 限制")
        
        # 4. 敏感表权限
        sensitive_tables = ['user_pii', 'credit_report', 'device_fingerprint']
        for t in sensitive_tables:
            if t in sql.lower() and user_role != 'admin':
                violations.append(f"无权访问敏感表: {t}")
        
        # 5. JOIN 数量限制
        join_count = len(re.findall(r'\bJOIN\b', sql, re.I))
        if join_count > 3:
            violations.append(f"JOIN 数量过多: {join_count}")
        
        return violations
    
    @staticmethod
    def should_reject(intent: str, user_role: str) -> bool:
        """某些意图直接拒绝"""
        reject_intents = {
            "guest": ["indicator", "lineage"],  # 游客不能查数据
            "analyst": [],                       # 分析师全部开放
        }
        return intent in reject_intents.get(user_role, [])

    @staticmethod
    def sanitize_result(rows: list) -> list:
        """结果脱敏：手机号、身份证号打码"""
        import re
        sanitized = []
        for row in rows:
            r = dict(row)
            for k, v in r.items():
                if isinstance(v, str):
                    v = re.sub(r'\b1[3-9]\d{9}\b', '1**********', str(v))
                    v = re.sub(r'\b\d{6}(19|20)\d{2}(0[1-9]|1[0-2])\d{6}\b', '******', str(v))
                r[k] = v
            sanitized.append(r)
        return sanitized
```

#### Step 4：录 3 分钟演示（1 天）

**必须展示的 3 条路径**（面试官想看的不只是成功样例）：

| 路径 | 输入 | 预期行为 |
|------|------|---------|
| ✅ 成功 | "昨天各渠道逾期率" | SQL → 执行 → 自然语言回答 |
| ❌ 拒答 | "帮我删掉 user_000042 的记录" | 安全检查拦截，返回"不支持此操作" |
| ⚠️ 澄清 | "今年利润" | 意图识别后发现无此指标，反问"您是指净收入还是毛利率？" |

### 2.4 Demo 与题库对应

| Demo 模块 | 题库分类 | 可展示的知识点 |
|-----------|---------|--------------|
| 意图识别 | Agent #27 | 为什么先做主题域识别再做意图识别 |
| NL2SQL 生成 | NL2SQL 全分类 | Schema Catalog、安全校验层 |
| SQL 执行 | 综合 #30-32 | 超时、限流、审计 |
| RAG 检索 | RAG #39-46 | rewrite、拒答策略、幻觉规避 |
| 工具调用 | MCP 全分类 | Function Call vs MCP vs Skills |
| 安全护栏 | Agent #18-25 | bad case 归因、降级策略 |

---

## 三、中间件实战补充

### 3.1 Redis — 缓存 + 限流 + 会话

```python
import redis, json

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# ── 场景1：缓存热点查询，减少 DB 压力 ──
def query_with_cache(query_key: str, ttl: int = 3600):
    """先查 Redis，未命中再查 DB"""
    cached = r.get(query_key)
    if cached:
        return json.loads(cached)
    
    result = run_expensive_query(query_key)
    r.setex(query_key, ttl, json.dumps(result))
    return result


# ── 场景2：用户请求限流 ──
def check_rate(user_id: str, max_per_minute: int = 10) -> bool:
    key = f"rate_limit:{user_id}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, 60)
    return count <= max_per_minute


# ── 场景3：Agent 会话上下文 ──
def save_session(session_id: str, history: list, ttl: int = 1800):
    r.setex(f"session:{session_id}", ttl, json.dumps(history))

def get_session(session_id: str) -> list:
    data = r.get(f"session:{session_id}")
    return json.loads(data) if data else []
```

**面试高频追问**：缓存穿透怎么处理？数据一致性问题？Redis 内存淘汰策略？

---

### 3.2 Kafka — 异步审计 + 解耦

```python
from kafka import KafkaProducer, KafkaConsumer
import json
from datetime import datetime

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
)

# ── Agent 每次问答后，异步写审计日志 ──
def audit_agent_call(user: str, query: str, sql: str, 
                     result_rows: int, latency_ms: float, status: str):
    event = {
        "timestamp": datetime.now().isoformat(),
        "user": user,
        "query": query,
        "sql": sql,
        "result_rows": result_rows,
        "latency_ms": latency_ms,
        "status": status
    }
    producer.send('agent.audit', event)
    # 异步发送，不阻塞主请求


# ── 消费者：写入数仓 ODS 层 → 聚合到报表 ──
# consumer = KafkaConsumer('agent.audit', bootstrap_servers='localhost:9092')
# for msg in consumer:
#     data = json.loads(msg.value)
#     warehouse.insert_ods('ods_agent_audit', data)
```

**面试高频追问**：消息丢失怎么办？重复消费怎么处理？partition key 怎么选？

---

### 3.3 Docker — 一键部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  agent-api:
    build: .
    ports: ["8000:8000"]
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://user:pass@db:5432/agent
      - KAFKA_BROKER=kafka:9092
    depends_on:
      redis:
        condition: service_healthy
      db:
        condition: service_healthy

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: agent
    volumes:
      - pgdata:/var/lib/postgresql/data

  kafka:
    image: confluentinc/cp-kafka:latest
    environment:
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092

volumes:
  pgdata:
```

---

## 四、最小 7 天实操计划

| 天 | 任务 | 产出 |
|----|------|------|
| Day 1 | 本地装 Redis，写缓存/限流/会话三个 demo | `agent_cache.py` |
| Day 2 | 装 Kafka，搭 producer→consumer 链路 | `audit_producer.py` |
| Day 3 | 用 LangGraph 搭 Agent 核心工作流 | `agent_graph.py` |
| Day 4 | 加安全护栏：SQL 校验、权限、脱敏 | `safety_guard.py` |
| Day 5 | 接入 NL2SQL + RAG，打通完整链路 | 端到端可运行 |
| Day 6 | Docker 化，compose up 一键启动 | `Dockerfile` + `docker-compose.yml` |
| Day 7 | 录 3 分钟演示视频 + 整理面试讲稿 | 演示视频 + README |

---

## 五、面试一句话总结模板

> "我做了一个**金融信贷 AI Agent 数据问答系统**。用户用自然语言提问，Agent 自动判断意图，通过 NL2SQL 查询数仓 ADS 层获取指标，结合 RAG 检索口径解释返回结果。系统有完整的安全护栏——SQL 执行前必须过 5 道校验（危险操作、分区过滤、权限、JOIN 限制、行数限制），所有调用通过 Kafka 异步写入审计日志。整个项目用 Docker Compose 一键部署，在面试演示中我展示了成功查询、安全拦截、指标不存在时的澄清三条路径。"

---

> 📅 生成时间: 2026-07-24
