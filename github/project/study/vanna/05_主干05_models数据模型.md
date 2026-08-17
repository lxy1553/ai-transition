# 主干 ⑤：models 数据模型

> **状态**：⬜ 未学完
> **代码位置**：`src/vanna/core/tool/models.py`（84 行）

---

## 三问（先想清楚再读代码）

- **Q1 解决什么问题**：定义 Agent 循环里流转的"数据结构"——LLM 和工具之间传什么
- **Q2 数据流哪一环**：贯穿整个循环（ToolCall → ToolResult → ToolContext）
- **Q3 删掉会怎样**：没有标准结构，LLM 返回什么格式全靠猜 → 无法稳定解析

## 核心骨架（待填充）

```python
# LLM 说"我要调这个工具"
class ToolCall(BaseModel):
    id: str                 # 唯一 ID
    name: str               # 工具名
    arguments: Dict         # 参数（LLM 填的原始 JSON）

# 每次工具调用带着的上下文
class ToolContext(BaseModel):
    user: User              # ★ 谁在调用（权限）
    conversation_id: str
    request_id: str         # 追踪
    agent_memory: AgentMemory

# 工具执行结果
class ToolResult(BaseModel):
    success: bool           # 成功/失败
    result_for_llm: str     # ★ 给 LLM 看的结果（回喂）
    ui_component: Optional  # 给用户看
    error: Optional[str]    # 失败原因

# 给 LLM 看的工具描述
class ToolSchema(BaseModel):
    name, description, parameters, access_groups
```

## 待学内容

- 4 个模型的完整解读
- ToolContext 如何"贯穿每层"（权限/追踪）

## 对照 ai_assistant

你的 `QueryResult` 只有 `data` → 加 `result_for_llm`（回喂给 LLM）概念。

> 核心心法：数据契约定义清楚，循环才能稳定运转。
