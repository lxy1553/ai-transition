
# 主干 ⑤：models 数据模型

> **状态**：✅ 已学完
> **代码位置**：`src/vanna/core/tool/models.py`（84 行，完整读过）
>
> **这是 Agent 循环里流转的"数据契约"**——ToolCall/ToolContext/ToolResult/ToolSchema 定义了 LLM、Agent、工具之间传什么。没有它们，循环无法稳定解析。

---

## 三问

- **Q1 解决什么问题**：定义 Agent 循环里流转的"数据结构"——LLM 和工具之间传什么
- **Q2 数据流哪一环**：贯穿整个循环（ToolCall → ToolResult → ToolContext）
- **Q3 删掉会怎样**：没有标准结构，LLM 返回什么格式全靠猜 → 无法稳定解析

---

## 一、四个核心模型（`core/tool/models.py`，全文解读）

### ① ToolCall —— LLM 说"我要调这个工具"

```python
class ToolCall(BaseModel):
    """代表 LLM 发出的工具调用请求"""
    id: str                      # 唯一 ID（对应工具结果的 tool_call_id）
    name: str                    # 工具名（Registry 靠它找工具）
    arguments: Dict[str, Any]    # 参数（LLM 填的原始 JSON）
```

**在哪产生**：LLM 返回 tool_calls → `_extract_tool_calls_from_message` 解析成 ToolCall（见主干④）。

**数据流**：`LLM → ToolCall → registry.execute(tool_call)` → 工具找到并执行。

**例子**：
```python
ToolCall(
    id="call_001",
    name="run_sql",
    arguments={"sql": "SELECT COUNT(*) FROM Customer"}
)
```

---

### ② ToolContext —— 每次工具调用带着的上下文（★ 最核心）

```python
class ToolContext(BaseModel):
    """传给所有工具执行的上下文"""
    user: "User"                    # ★ 谁在调用（权限判断的依据）
    conversation_id: str            # 哪个会话
    request_id: str                 # 哪个请求（全链路追踪）
    agent_memory: AgentMemory       # 记忆（工具可读写）
    metadata: Dict[str, Any]        # 附加信息（可放 SQL、ui_features 等）
    observability_provider: Optional = None   # 观测（追踪）

    class Config:
        arbitrary_types_allowed = True   # ★ 允许 User/AgentMemory 这种非标准类型
```

**为什么是"贯穿每层"**：
- 每个工具调用都带 ToolContext
- 权限判断看 `context.user`
- 追踪看 `context.request_id`
- 记忆读写看 `context.agent_memory`

**这就是"每层感知用户"的实现**——权限不是 pipeline 判一次，而是每个工具调用都带着 user。

**例子**：
```python
ToolContext(
    user=User(id="u_1001", group_memberships=["analyst"]),
    conversation_id="conv_123",
    request_id="req_abc",
    agent_memory=DemoAgentMemory(),
    metadata={"sql": "SELECT ..."},   # 工具可读的附加信息
)
```

---

### ③ ToolResult —— 工具执行结果

```python
class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool                 # 成功/失败
    result_for_llm: str           # ★ 给 LLM 看的结果（回喂循环）
    ui_component: Optional = None # 给用户看的 UI（表格/图表/通知）
    error: Optional[str] = None   # 失败原因
    metadata: Dict = {}           # 额外信息（如耗时）

    # Vanna 补充的方法（非抽象方法）
    def to_dict(self): ...
```

**关键区分**：
- `result_for_llm`：**给 LLM 看**的文本（回喂进循环，LLM 基于它决定下一步）
- `ui_component`：**给用户看**的 UI 组件（前端渲染）

**例子**：
```python
ToolResult(
    success=True,
    result_for_llm="SELECT COUNT(*) 返回 59 行...",   # LLM 看
    ui_component=DataFrameComponent(rows=[...]),      # 用户看
    metadata={"row_count": 59},
)
```

**错误时**：
```python
ToolResult(
    success=False,
    result_for_llm="Error executing query: ...",   # ★ 错误也回喂给 LLM
    error="table not found",
)
```

---

### ④ ToolSchema —— 给 LLM 看的工具描述

```python
class ToolSchema(BaseModel):
    """描述工具，供 LLM 消费"""
    name: str                          # 工具名
    description: str                   # 做什么（LLM 判断何时用）
    parameters: Dict[str, Any]         # 参数 JSON Schema（LLM 填参数）
    access_groups: List[str]           # 权限组
```

**在哪产生**：`Tool.get_schema()` 自动生成（见主干②）。
**在哪用**：`get_schemas(user)` 过滤后 → 注入 system_prompt / OpenAI tools 参数（见主干③④）。

**例子**：
```python
ToolSchema(
    name="run_sql",
    description="Execute SQL queries against the configured database",
    parameters={"type": "object", "properties": {"sql": {"type": "string"}}},
    access_groups=["analyst"],
)
```

---

## 二、四个模型在循环里的数据流（一图）

```
┌─────────────────────────────────────────────┐
│  Agent 循环                                  │
│                                             │
│  LLM 返回 ──→ ToolCall（说要调工具）           │
│                │                            │
│                ▼                            │
│           ToolContext（带着 user/会话/记忆）   │
│                │                            │
│                ▼                            │
│           registry.execute(tool_call, context) │
│                │                            │
│                ▼                            │
│           Tool.execute() ──→ ToolResult      │
│                │          （给LLM + 给用户）   │
│                ▼                            │
│           result_for_llm 回喂给 LLM ──→ 再判断  │
│                                             │
└─────────────────────────────────────────────┘
```

**四者关系**：
- **ToolCall**：输入（LLM → 工具）
- **ToolContext**：全程携带（user/会话/记忆）
- **ToolResult**：输出（工具 → LLM + 用户）
- **ToolSchema**：描述（LLM 理解工具用）

---

## 三、ToolRejection（补充模型）

```python
class ToolRejection(BaseModel):
    """表示工具执行应被拒绝（带原因）"""
    reason: str   # 拒绝原因（如"无权限访问表 user_pii"）
```

**用在哪**：`transform_args` 返回 ToolRejection → registry 拒绝执行（见主干③）。

**例子**：
```python
return ToolRejection(reason="无权限访问表 user_pii")
# → registry 返回 ToolResult(success=False, error="无权限访问表 user_pii")
```

---

## 四、对照 ai_assistant 的改造动作

你的 `ai_assistant` 现在有 `QueryResult`，对比缺什么：

```python
# 你的 QueryResult（现在）
@dataclass
class QueryResult:
    success: bool
    data: list[dict]       # 只有 data，没有分给 LLM 和用户
    error: str

# Vanna 的 ToolResult（对比）
class ToolResult:
    success: bool
    result_for_llm: str    # ★ 给 LLM 回喂
    ui_component: Optional # 给用户
    error: Optional[str]
```

**改造建议**：
```python
# 你的 QueryResult 加 result_for_llm 概念
@dataclass
class QueryResult:
    success: bool
    data: list[dict]            # 查询结果
    result_for_llm: str         # ★ 新增：给 LLM 回喂的文本（格式化成可理解）
    user_facing: str            # ★ 新增：给用户看的文本
    error: str

# 同时加 ToolContext（贯穿权限/追踪）
@dataclass
class ToolContext:
    user_id: str
    user_role: str
    request_id: str
    sql: str
```

**改造要点**：
1. `QueryResult.data` → 分 `result_for_llm`（给LLM）+ `user_facing`（给用户）
2. 加 `ToolContext`（user_role 贯穿，追踪）
3. 你的 pipeline 每步返回统一数据结构，循环才能稳定流转

---

## 五、小结

| 模型 | 一句话 | 在哪用 |
|------|--------|--------|
| ToolCall | LLM 说要调什么 | LLM → 工具（输入）|
| ToolContext | 每次调用带 user/会话/记忆 | 全程携带 |
| ToolResult | 执行结果（给LLM+给用户）| 工具 → LLM+用户（输出）|
| ToolSchema | 工具描述（LLM 理解）| system_prompt / tools 参数 |
| ToolRejection | 拒绝执行带原因 | transform_args |

> **核心心法**：数据契约定义清楚，循环才能稳定运转。ToolResult 分"给LLM"和"给用户"是 Agent 循环的关键——LLM 靠 result_for_llm 决定下一步。
