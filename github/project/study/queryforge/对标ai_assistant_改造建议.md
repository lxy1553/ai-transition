# QueryForge → 对标 ai_assistant 改造建议

> **把 QueryForge 学到的生产工程化，映射到你的 ai_assistant**——学到什么、缺什么、改什么。
> 这是活文档，持续更新（对照 vanna 的 `12_对标ai_assistant_改造建议.md`，这个聚焦生产工程化）。
>
> 目标：把 ai_assistant 从"能跑的 demo"变成"能上线的产品"。

---

## 一、总览：QueryForge vs 你 ai_assistant

| 能力 | QueryForge | 你 ai_assistant | 差距 |
|------|-----------|----------------|------|
| 编排 | ✅ LangGraph 图 + 自纠错 | ❌ 8 步固定 if-else | ★★★ |
| SQL 安全 | ✅ sqlglot 真解析 | 🟡 正则校验 | ★★★ |
| 自纠错 | ✅ validate/execute 失败回 generate | ❌ 无重试 | ★★★ |
| 缓存 | ✅ Redis + 语义缓存 | ❌ 无 | ★★★ |
| 熔断/重试 | ✅ CircuitBreaker | ❌ 无 | ★★★ |
| RAG | ✅ 三套语料 + few-shot + schema | 🟡 单文档 | ★★ |
| 评测 | ✅ 执行准确率 + A/B + 分桶 | 🟡 eval_qa 雏形 | ★★ |
| 限流 | ✅ slowapi | ❌ 无 | ★★ |
| 多轮 | ✅ 会话 + history | ❌ 单轮 | ★★★ |
| 鉴权 | ✅ JWT | ❌ 无 | ★★ |
| 可观测 | ✅ Prometheus/Langfuse | ❌ 无 | ★★ |
| 部署 | ✅ Docker + alembic | ❌ 无 | ★★ |

---

## 二、最该先做的 6 个改造（按优先级）

### ★★★ 1. 自纠错循环（改 pipeline）

```python
# 现在：8 步固定
sql = sql_generator.generate(query)
result = executor.execute(sql)

# 改造：生成→校验→重试（带错误回喂）
attempt = 0
last_error = None
while attempt < SQL_MAX_RETRY:
    sql = sql_generator.generate(query, last_error)   # ★ 带上次错误重生成
    error = sql_validator.validate(sql)
    if not error:
        result = executor.execute(sql)
        if result.success: break
    last_error = error
    attempt += 1
```

**为什么**：LLM 生成 SQL 常错，重试带错误回喂能显著提准（README 实验证明 retry 提升明显）。

### ★★★ 2. SQL 安全升级（正则 → sqlglot）

```python
# 现在：正则（能被绕过）
if re.search(r'\bDROP\b', sql): reject

# 改造：sqlglot 真解析（识别嵌套/变体）
import sqlglot
from sqlglot import exp
stmt = sqlglot.parse_one(sql, dialect="sqlite")
if not isinstance(stmt, exp.Select):       # 强制只读
    raise PermissionError("仅允许 SELECT")
if not stmt.args.get("limit"):
    stmt = stmt.limit(1000)                # 自动 LIMIT
safe_sql = stmt.sql()
```

**为什么**：正则字符串匹配能被绕过（`dr\rop`、大小写变体），sqlglot 真解析识别真实语句类型。这是"命门"。

### ★★★ 3. 缓存（相同问题不重复烧 LLM）

```python
# 加 Redis 精确缓存
def _normalize(text):
    return re.sub(r"[\s，。？！、,.?!;:\"'`]+", "", text.lower().strip())

async def ask(query, user_role):
    key = hashlib.sha256(f"{user_role}::{_normalize(query)}".encode()).hexdigest()[:32]
    cached = await redis.get(key)
    if cached: return json.loads(cached)     # ★ 命中不调 LLM（省钱）
    answer = pipeline.ask(query, user_role)
    if answer.success:                       # 只缓存成功
        await redis.set(key, json.dumps(answer), ex=3600)
    return answer
```

**为什么**：相同问题重复问会重复烧 token。缓存命中跳过 LLM = 省钱省延迟。

### ★★★ 4. 熔断 + 重试（LLM 挂了不拖垮）

```python
# 给 llm_client 加熔断
class CircuitBreaker:
    def __init__(self, fail_threshold=5, reset_timeout=30):
        self._failures = 0
        self._opened_at = None

    async def call(self, fn, *args):
        if self._opened_at and time.monotonic() - self._opened_at < self.reset_timeout:
            raise CircuitOpenError("熔断打开")   # 快速失败
        try:
            result = await fn(*args)
            self._failures = 0
            return result
        except Exception:
            self._failures += 1
            if self._failures >= self.fail_threshold:
                self._opened_at = time.monotonic()
            raise

breaker = CircuitBreaker("llm")
async def llm_call(prompt):
    return await breaker.call(llm.chat, prompt)
```

**为什么**：LLM 挂了时所有请求卡在等待——熔断快速失败，防雪崩。

### ★★★ 5. 多轮会话 + history（从单轮到产品）

```python
# ① pipeline.ask 加 history 参数
def ask(query, user_role, history=None):
    if history:
        query = rewrite_with_history(query, history)   # 多轮改写
    return pipeline.ask(query, user_role)

# ② 会话存储（简单版）
sessions = {}
def chat(session_id, query):
    history = sessions.get(session_id, [])
    answer = ask(query, "analyst", history)
    history.append({"role": "user", "content": query})
    history.append({"role": "assistant", "content": answer})
    sessions[session_id] = history
    return answer
```

**为什么**：产品级必备——"这个指标"能指代上一轮的"逾期率"（多轮）。

### ★★ 6. few-shot 检索 + schema 语料（RAG 准确率）

```python
# ① few-shot：找类似问题的成功 SQL
fewshots = fewshot_retriever.search(query)
prompt = build_prompt(query, docs, fewshots)   # 示例增强

# ② schema 语料：不只是字段清单，带主外键
schema_text = build_ddl_text(indicator_tables)   # CREATE TABLE 风格
```

**为什么**：README 实验证明 few-shot 最稳定收益；schema 带主外键帮助 LLM 理解 JOIN。

---

## 三、改造后的一图（完整）

```
用户问题
  │
  ▼
API（限流 + 鉴权 + 会话）     ← 加 FastAPI + JWT + 会话
  ▼
缓存（Redis）                 ← 相同问题直接返回
  ▼
pipeline（自纠错循环）         ← 生成→校验→重试
  │  few-shot 增强            ← RAG 升级
  │  schema 语料             ← 带主外键
  ▼
SQL Guard（sqlglot）          ← 安全升级
  ▼
执行（熔断 + 重试）            ← LLM 挂了快速失败
  ▼
评测（执行准确率 + 分桶）       ← 量化效果
```

**大白话**：从"能跑的 demo"到"能上线的产品"——每个环节加 QueryForge 学到的工程化。

---

## 四、落地顺序（建议按版本）

```
v2.0（★★★）：自纠错循环 + SQL 安全升级
  → 改 pipeline：生成→校验→重试 + sqlglot
v2.1（★★★）：缓存 + 熔断
  → Redis 缓存 + llm_client 熔断
v2.2（★★★）：多轮会话
  → pipeline.ask 加 history + 会话存储
v2.3（★★）：few-shot + schema 语料
  → RAG 升级
v3.0（★★）：API 层 + 限流 + 评测升级
  → FastAPI + JWT + slowapi + 执行准确率评测
v3.1（★★）：可观测 + 部署
  → Prometheus + Docker
```

**每个版本能验证**：跑 eval_qa.py，准确率不降 + 延迟降 = 改对了。

---

## 五、一句话总结

> QueryForge 教你的核心 = **Text-to-SQL 落地不是"生成 SQL"那么简单，而是：自纠错 + SQL 真安全 + 缓存省钱 + 熔断防雪崩 + 多轮会话 + 评测量化**。
> 你的 ai_assistant 最该先做：**自纠错循环 + sqlglot 安全 + 缓存 + 熔断**（★★★ 四个），然后多轮 + API + 评测升级。

---

## 六、更新日志

| 日期 | 追加内容 |
|------|---------|
| 2026-08-20 | 初版：6 个优先改造（自纠错/sqlglot/缓存/熔断/多轮/few-shot）|

> 持续更新：每学完 QueryForge 一个主干/阶段，回来追加"区别 → 对照 → 改造建议"。
