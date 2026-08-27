# QueryForge 主干 1：LangGraph 编排（心脏）

> **这是 QueryForge 的核心**——用 LangGraph 状态图表达 Text-to-SQL 完整链路。
> 11 个节点 + 条件边 + 自纠错循环。相当于 Vanna 的 agent.py 循环，但用图表达。
>
> **代码位置**：`app/core/langgraph/graph.py`（134行）+ `state.py`（42行）+ `nodes/`（11个节点）

---

## 三问

- **Q1 解决什么问题**：把复杂流程（检测→改写→检索→生成→校验→执行）表达成图，支持条件分支 + 自纠错循环 + 人机确认
- **Q2 数据流哪一环**：请求主路径核心——`api → run_query → graph.invoke` → 走完整链路
- **Q3 删掉会怎样**：流程写死在代码，无法分支/重试/人机确认

---

## 一、完整链路图

```
detect_language → rewrite → expand → retrieve ─┬─(无上下文)→ error → END
                                               └→ schema_linking → generate_sql
     ↑(loop)                                                        ↓
self_correct ←──(失败且未超次数)── validate_sql ──(通过)→ execute_sql ─(成功)→ format_answer → END
                          │                    │
                          └(超次数)→ format_answer ←(失败且超次数)┘
```

**大白话**：流水线——听懂问题 → 改写 → 扩展 → 查资料 → 生成 SQL → 校验 → 执行 → 回答。**哪步失败回上一步重来**（自纠错）。

---

## 二、GraphState：节点间共享状态（state.py）

```python
class GraphState(TypedDict, total=False):
    query: str               # 用户问题
    language: str            # 检测的语言
    rewritten_query: str     # 改写后问题
    expanded_query: str      # 扩展后问题
    schema_docs: list        # 检索到的 schema 文档
    fewshot_examples: list   # few-shot 示例
    schema_linking: str      # 表/列链接结果
    sql: str                 # 生成的 SQL
    error: str               # 错误信息
    attempt: int             # 重试次数
    sql_result: dict         # 执行结果
    final_answer: str        # 最终回答
    history: list            # 多轮历史
```

**大白话**：GraphState = 一张"共享工作台"，每个节点读它、写它。`total=False` = 字段可缺省（节点只返回增量）。

---

## 三、图构建（graph.py 逐段）

### 节点注册（11 个）

```python
def build_graph(checkpointer=None, enable_hil=None):
    g = StateGraph(GraphState)      # ① 创建图（GraphState = 共享状态）
    # ② 注册所有节点（每个 = 一个函数）
    g.add_node("detect_language", nodes.detect_language)
    g.add_node("rewrite", nodes.rewrite)
    g.add_node("expand", nodes.expand)
    g.add_node("retrieve", nodes.retrieve)
    g.add_node("schema_linking", nodes.schema_linking)
    g.add_node("generate_sql", nodes.generate_sql)
    g.add_node("human_review_sql", nodes.human_review_sql)   # 人机确认
    g.add_node("validate_sql", nodes.validate_sql)
    g.add_node("execute_sql", nodes.execute_sql)
    g.add_node("self_correct", nodes.self_correct)
    g.add_node("format_answer", nodes.format_answer)
    g.add_node("error_node", nodes.error_node)
```

### 固定边（顺序执行）

```python
    g.add_edge(START, "detect_language")    # 起点 → 检测
    g.add_edge("detect_language", "rewrite")  # 检测 → 改写
    g.add_edge("rewrite", "expand")           # 改写 → 扩展
    g.add_edge("expand", "retrieve")          # 扩展 → 检索
```

### 条件边（分支决策）

```python
    # retrieve 后：有 schema → schema_linking；无 → error
    g.add_conditional_edges(
        "retrieve", _route_after_retrieve,#路由函数（判断逻辑）
        {"schema_linking": "schema_linking", "error_node": "error_node"},
    )
    # validate 后：无错→执行；有错可重试→自纠错；超次→回答失败
    g.add_conditional_edges(
        "validate_sql", _route_after_validate,#路由函数（判断逻辑）
        {"execute_sql": "execute_sql", "self_correct": "self_correct", "format_answer": "format_answer"},
    )
```

### 路由函数（决定去哪）

```python
def _route_after_validate(state) -> str:
    """validate 后决定走哪"""
    if not state.get("error"):
        return "execute_sql"                      # 无错 → 执行
    if state.get("attempt", 0) < settings.SQL_MAX_RETRY:
        return "self_correct"                     # 有错可重试 → 自纠错
    return "format_answer"                        # 超次 → 回答失败

def _route_after_execute(state) -> str:
    result = state.get("sql_result", {})
    if result.get("ok"):
        return "format_answer"                    # 执行成功 → 回答
    return "self_correct" if state.get("attempt", 0) < settings.SQL_MAX_RETRY else "format_answer"
```

**大白话**：路由函数 = 判断"下一步去哪"，像 Vanna 的 `is_tool_call()`。自纠错 = 失败回 generate 带错误重来。

### 自纠错循环 + 编译

```python
    g.add_edge("self_correct", "generate_sql")   # 自纠错 → 回到生成（带错误重来）
    g.add_edge("format_answer", END)
    g.add_edge("error_node", END)
    return g.compile(checkpointer=checkpointer)   # 编译成可执行图
```

---

## 四、checkpointer（断点续跑，框架的价值）

```python
async def get_graph():
    # 挂上 AsyncPostgresSaver（断点续跑，供人机交互 interrupt() 用）
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    # 挂载失败时降级为无检查点图（HIL 不可用，主链路照常）
```

**大白话**：checkpointer = 存图执行到哪了，断了能恢复（人机确认时暂停等审批）。**这是 Vanna 手写版没有的**——正是之前学的"框架补上手写版缺的能力"。

---

## 五、对比 Vanna（框架 vs 手写，之前学过）

| | Vanna（手写）| QueryForge（LangGraph）|
|---|---|---|
| 表达 | while 循环 + if | 图（节点 + 边 + 条件边）|
| 分支 | `is_tool_call()` | `add_conditional_edges` |
| 循环 | while 上限 | self_correct 回边 |
| 状态 | conversation 消息 | GraphState |
| 恢复 | ❌ 无 | ✅ checkpointer 断点续跑 |

**正是"框架 vs 手写"实例**：你懂 Vanna 手写，看 LangGraph 一目了然。**先手写懂了，用框架是降维打击**。

---

## 六、对照 ai_assistant 的改造动作

```python
# 现在：8 步固定 if-else
sql = generate_sql(query)
result = execute(sql)

# 改造 1：加自纠错循环（不用图，先手写）
attempt = 0
while attempt < MAX_RETRY:
    sql = generate_sql(query, last_error)   # 带上次错误重生成
    error = validate_sql(sql)
    if not error:
        result = execute(sql)
        break
    attempt += 1

# 改造 2：需要时再用 LangGraph（断点/人机确认）
# g = StateGraph(...)
# g.add_conditional_edges(...)  # 校验失败回退
```

**改造要点**：先手写自纠错循环，需要断点/人机确认再上 LangGraph。

---

## 七、小结

| 学到 | 一句话 |
|------|--------|
| 图 | 节点（步骤）+ 边（顺序）+ 条件边（分支）|
| GraphState | 节点间共享状态 |
| 自纠错 | 失败回 generate 重来（带错误）|
| 路由函数 | 决定分支（像 is_tool_call）|
| checkpointer | 断点续跑（框架价值）|
| 对比 Vanna | 手写 vs 图 |

> **核心心法**：LangGraph 把流程表达成图——节点是步骤、边是流程、条件边是分支、回边是重试、checkpointer 是断点。你懂 Vanna 手写循环，看这个图降维打击。**ai_assistant 先加自纠错循环（手写），需要时再上 LangGraph**。
