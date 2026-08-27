# QueryForge 主干 3：SQL 安全与执行（命门）

> **这是 QueryForge 的"生产命门"**——LLM 生成的 SQL 不可信，必须强制校验 + 沙箱执行。
> 对比你 ai_assistant：你的 sql_validator 用正则（能被绕过），QueryForge 用 sqlglot 真解析。
>
> **代码位置**：`app/sql/guard.py`（81行）+ `app/sql/executor.py`（94行）

---

## 三问

- **Q1 解决什么问题**：LLM 生成的 SQL 可能包含注入/危险操作/全表扫描——执行前必须强制校验 + 只读沙箱
- **Q2 数据流哪一环**：LangGraph 的 validate_sql → execute_sql 节点——生成 SQL 后、执行前
- **Q3 删掉会怎样**：SQL 注入风险 + 危险操作 + 全表扫描拖垮数据库

---

## 一、SQL Guard（guard.py 逐段）

### 禁止的语句类型

```python
_FORBIDDEN = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop,
    exp.Create, exp.Alter, exp.TruncateTable, exp.Command, exp.Grant,
)
_READ_ONLY_ROOTS = (exp.Select, exp.Union, exp.Intersect, exp.Except, exp.With)
```

**大白话**：明令禁止写操作/危险操作；只允许 SELECT 类只读。

### 校验 + 加固

```python
def validate_and_secure(sql, dialect=None, max_rows=None) -> str:
    """校验并加固 SQL，返回可安全执行的最终 SQL"""
    raw = _strip_fences(sql)       # ① 剥掉 LLM 爱输出的 ```sql``` 围栏
    if not raw:
        raise SQLGuardError("空 SQL")

    statements = sqlglot.parse(raw, dialect=dialect)   # ② ★ 真解析（非字符串匹配）
    if len(statements) != 1:
        raise SQLGuardError("只允许单条语句")           # ③ 防多语句注入

    stmt = statements[0]
    if isinstance(stmt, _FORBIDDEN) or stmt.find(*_FORBIDDEN):
        raise SQLGuardError(f"禁止的语句类型: {type(stmt).__name__}")  # ④ 禁危险操作
    if not isinstance(stmt, _READ_ONLY_ROOTS):
        raise SQLGuardError("仅允许 SELECT 查询")       # ⑤ 强制只读

    if not stmt.args.get("limit"):
        stmt = stmt.limit(max_rows)                    # ⑥ 自动注入 LIMIT

    return stmt.sql(dialect=dialect)                   # ⑦ 返回规范化 SQL
```

### 为什么 sqlglot 真解析比正则强

| | 正则（你的）| sqlglot 真解析（QueryForge）|
|---|---|---|
| 绕过 | `dr\rop`、大小写变体可绕过 | 解析成 AST，识别真实语句类型 |
| 嵌套 | 难检测子查询里的危险操作 | `stmt.find(*_FORBIDDEN)` 找嵌套 |
| 注入 LIMIT | 难改 SQL | `stmt.limit()` 直接 AST 加 |

**大白话**：sqlglot 把 SQL 解析成 AST（语法树），能识别"真实是什么语句"+"嵌套里的危险操作"。正则匹配文本能被花式绕过。

---

## 二、SQL 执行沙箱（executor.py 逐段）

### ExecResult（统一返回）

```python
@dataclass
class ExecResult:
    ok: bool
    columns: list[str]
    rows: list[list]
    error: str | None
    row_count: int
```

### SQLite 只读执行

```python
def _run_sqlite(db_id, sql, max_rows) -> ExecResult:
    path = _sqlite_path(db_id)
    # ★ 只读打开（mode=ro），即使 SQL 有写操作也写不进去
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute(sql)
    cols = [c[0] for c in cur.description]
    rows = cur.fetchmany(max_rows)   # ★ 行数限制
    return ExecResult(ok=True, columns=cols, rows=[list(r) for r in rows], row_count=len(rows))
```

### PostgreSQL 只读事务

```python
async def _run_postgres(sql, max_rows, timeout) -> ExecResult:
    async with pool.connection() as conn:
        async with conn.transaction():
            await cur.execute("SET TRANSACTION READ ONLY")                    # ★ 只读事务
            await cur.execute(f"SET LOCAL statement_timeout = {timeout*1000}") # ★ 超时
            await cur.execute(sql)
            rows = await cur.fetchmany(max_rows)                              # ★ 行数限制
```

### 异步执行（超时控制）

```python
async def execute(db_id, sql, dialect=None) -> ExecResult:
    timeout = settings.SQL_EXEC_TIMEOUT_SECONDS
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_run_sqlite, db_id, sql, max_rows), timeout=timeout
        )
    except TimeoutError:
        result = ExecResult(ok=False, error=f"执行超时（>{timeout}s）")   # ★ 超时兜底
    return result
```

**大白话**：三层防护——**只读打开**（SQLite mode=ro / PG READ ONLY）+ **超时**（防慢查询）+ **行数限制**（防全表拖垮）。

---

## 三、完整流程（生成 → 校验 → 执行）

```
generate_sql（LLM 生成 SQL）
  → validate_sql（guard.validate_and_secure）
      │  通过 → 返回规范化 SQL
      │  失败 → SQLGuardError → 自纠错（回 generate 带错误重来）
  → execute_sql（executor.execute）
      │  成功 → format_answer
      │  失败 → 自纠错（回 generate）
      └（超次数）→ 返回失败
```

**大白话**：SQL Guard 是强制闸门——没通过就不执行，通过了才进只读沙箱。**任何一步失败回生成重来**（自纠错）。

---

## 四、对照 ai_assistant 的改造动作

```python
# ① SQL 校验：正则 → sqlglot
import sqlglot
from sqlglot import exp

def validate_and_secure(sql):
    stmt = sqlglot.parse_one(sql)          # 真解析
    if not isinstance(stmt, exp.Select):   # 强制只读
        raise PermissionError("仅允许 SELECT")
    if not stmt.args.get("limit"):         # 自动 LIMIT
        stmt = stmt.limit(1000)
    return stmt.sql()

# ② 执行沙箱：只读 + 超时 + 行数
def execute_sql(sql):
    conn = sqlite3.connect(f"file:data.db?mode=ro", uri=True)   # 只读
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchmany(1000)              # 行数限制
    return rows
```

**改造要点**：
1. `sql_validator` 正则 → sqlglot 真解析（更可靠）
2. `query_executor` 加只读连接 + 超时 + 行数限制

---

## 五、小结

| 学到 | 一句话 |
|------|--------|
| sqlglot 真解析 | 识别真实语句，防绕过 |
| 强制单条 SELECT | 防多语句注入 |
| 自动 LIMIT | 防全表扫描 |
| 只读沙箱 | SQLite mode=ro / PG READ ONLY |
| 超时 | 防慢查询拖垮 |
| 行数限制 | 防内存爆 |

> **核心心法**：SQL 是命门——生成后必须"强制校验（sqlglot）+ 沙箱执行（只读/超时/行数）"。你的 sql_validator 从正则升到 sqlglot 是最高优先改造。
