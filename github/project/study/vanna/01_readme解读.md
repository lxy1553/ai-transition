# Vanna 2.0 README 深度解读（含源码验证 + 实战踩坑）

> 学习方式：README 讲"设计意图"，源码验证"真实实现"，运行脚本记录"实战真相"。
> 本文把三者整合，标注了每个概念对应的**真实代码路径**。
>
> 项目位置：`github/project/vanna`
> 完成时间：2026-08-14

---

## 一、Vanna 是什么？（README 一句话）

> **Natural language → SQL → Answers.**
> 用户用自然语言提问 → 系统生成 SQL 查数据库 → 返回答案。

Vanna 2.0 的核心不是"生成 SQL 的算法"，而是一个 **Agent 框架**：
- 你提供 **LLM**（大脑）
- 你提供 **数据库**（数据源）
- Vanna 提供 **Agent 循环 + 工具注册表 + 用户权限 + 流式 UI**

**代码位置**：`src/vanna/__init__.py` 顶部导出的东西就是全部核心概念：
```python
# src/vanna/__init__.py
from .core import (
    Agent,          # 核心 Agent 类（大脑 + 循环）
    Tool,           # 工具抽象基类
    ToolRegistry,   # 工具注册表
    LlmService,     # LLM 服务接口
    ToolCall,       # LLM 说"我要调这个工具，参数是这些"
    ToolContext,    # 每个工具调用都带着 用户+会话+追踪ID
    User,           # 用户模型（含 group_memberships 权限组）
    UiComponent,    # UI 组件（流式返回给前端）
    ...
)
```

---

## 二、Vanna 2.0 相比 0.x 的四大变化（README "What's New"）

| 变化 | README 说的 | 源码里怎么体现 |
|------|------------|--------------|
| 🔐 **User-Aware 每层感知用户** | 查询按用户权限自动过滤 | `ToolContext.user` + `Tool.access_groups`（`core/tool/base.py`）|
| 🎨 **现代 Web UI** | 内置 `<vanna-chat>` 组件 | `components/` 目录（Rich/Simple 两套）|
| ⚡ **流式响应** | 实时返回表格/图表/进度 | `servers/base/chat_handler.py` + SSE |
| 🔒 **企业安全** | 行级权限、审计、限流 | `core/audit/` + `core/user/` |

**关键迁移点**（`MIGRATION_GUIDE.md` + 源码确认）：
- 0.x 用 `VannaBase` 类的方法（`vn.ask()`），2.0 改成 **Agent 类**（`agent.send_message()`）
- 0.x 返回 dataframe，2.0 返回 **流式 UI 组件**

---

## 三、核心概念逐个拆解（README 讲概念，源码给真相）

### 1. Agent —— 大脑 + 循环

**README 说**：Agent 是核心，管理 LLM + 工具循环。

**源码真相**：`src/vanna/core/agent/agent.py`（1407 行）

构造要求（**注意：和 README 示例不一样！**）：
```python
Agent(
    llm_service=llm_service,          # 必填：LLM
    tool_registry=tool_registry,      # 必填：工具注册表
    user_resolver=user_resolver,      # ★ 必填：用户解析器（README 示例没传，会报错！）
    agent_memory=agent_memory,        # ★ 必填：Agent 记忆
    config=AgentConfig(stream_responses=False),
)
```

**核心方法**：`send_message(request_context, message, conversation_id)` —— 处理一条用户消息，yield 一串 UI 组件。

### 2. Tool —— 工具的抽象

**README 说**：扩展 `Tool` 基类就能加自定义工具。

**源码真相**：`src/vanna/core/tool/base.py`（70 行，最小也最核心）

```python
class Tool(ABC, Generic[T]):
    @property
    @abstractmethod
    def name(self) -> str: ...          # 工具名（LLM 靠这个调用它）

    @property
    @abstractmethod
    def description(self) -> str: ...   # 工具描述（LLM 靠这个判断何时用）

    @property
    def access_groups(self) -> List[str]:  # 权限组（谁能用这个工具）
        return []

    @abstractmethod
    def get_args_schema(self) -> Type[T]:  # 参数结构（Pydantic 模型，LLM 靠这个填参数）
        ...

    @abstractmethod
    async def execute(self, context: ToolContext, args: T) -> ToolResult:
        ...                               # 真正干活的地方
```

**一个工具 = 名字 + 描述 + 参数schema + 执行函数 + 权限**。这就是 function calling 的本质。

### 3. ToolRegistry —— 工具注册表

**源码真相**：`src/vanna/core/registry.py`（46 行 `ToolRegistry`）

```python
class ToolRegistry:
    def register_local_tool(self, tool, access_groups):  # ★ 注意：不是 register()！
        # 把工具注册进 self._tools 字典

    async def get_tool(self, name):        # 按名字找工具
    async def get_schemas(self, user):     # 返回当前用户能用的所有工具 schema
    async def execute(self, tool_call, context):  # 执行工具调用（带权限/参数校验）
```

**execute() 的完整流程**（`registry.py:144-278`）：
```
execute(tool_call, context)
  → 1. 找到工具：get_tool(tool_call.name)
  → 2. 权限校验：_validate_tool_permissions(tool, context.user)
  → 3. 参数校验：args_model.model_validate(tool_call.arguments)
  → 4. 参数转换：transform_args()（可做行级安全、敏感字段脱敏）
  → 5. 真正执行：tool.execute(context, final_args)
  → 6. 审计：log_tool_invocation / log_tool_result
```

**这是"Agent"和"脚本"的分水岭**——工具是可插拔的、带权限的、被审计的。

### 4. LlmService —— LLM 服务接口

**源码真相**：`src/vanna/core/llm/base.py`（40 行）

```python
class LlmService(ABC):
    async def send_request(self, request: LlmRequest) -> LlmResponse: ...
    async def stream_request(self, request: LlmRequest): ...   # 流式
    async def validate_tools(self, tools: List[ToolSchema]) -> List[str]: ...
```

**生产实现**：`src/vanna/integrations/` 下，OpenAI/Anthropic/Ollama/DeepSeek 各一个文件，都实现这同一个接口 → **可插拔**。

### 5. User 和 UserResolver —— 用户与权限

**源码真相**：
- `User`：`src/vanna/core/user/models.py`（含 `group_memberships` 权限组）
- `UserResolver`：`src/vanna/core/user/resolver.py`（从请求里解析用户身份）
- `RequestContext`：`src/vanna/core/user/request_context.py`（封装 cookies/headers）

**为什么必须有 UserResolver**：Vanna 2.0 是"每层感知用户"——每个工具调用都带着 `context.user`，工具根据用户的权限组决定放行还是拒绝。

---

## 四、数据流转全图（用户提问 → 答案）

这是整个项目最核心的流程。结合我实际跑通的 `02_触发工具调用.py`：

```
👤 用户："数据库里有多少客户？"
  │
  ▼
① send_message(request_context, message, conversation_id)
  │   （src/vanna/core/agent/agent.py:142）
  ▼
② user_resolver.resolve_user(request_context)
  │   解析出是谁在问（user + 权限组）
  ▼
③ 构建 system_prompt（把所有工具 schema 塞进去）
  │   system_prompt_builder.build_system_prompt(user, tool_schemas)
  ▼
④ 进入 while 循环（agent.py:646）★ 核心！
  │   while tool_iterations < max_tool_iterations:
  │
  ├── ⑤ llm_service.send_request(request)
  │        LLM 返回 LlmResponse
  │        （第一次：带 tool_calls = 我想调 run_sql）
  │
  ├── ⑥ 判断 response.is_tool_call()
  │        YES → 遍历每个 tool_call：
  │               tool = registry.get_tool(tool_call.name)     ← 找到工具
  │               result = registry.execute(tool_call, context) ← 执行！（执行SQL）
  │               把结果作为 role="tool" 消息加进会话
  │               重新构建 request → 回到 ⑤（循环）
  │
  └── ⑦ NO（LLM 说答完了）
            yield response.content（最终回答）→ break
  │
  ▼
⑧ 前端收到组件流（表格/图表/文字）
```

**实际运行输出**（`02_触发工具调用.py` 的结果）：
```
🤖 让我查一下数据库里的客户数量...      ← 第一次 LLM 返回 ToolCall
🤖 Tool completed successfully        ← Agent 执行了 run_sql
🤖 查到了！数据库里共有 59 个客户。      ← 第二次 LLM 看到结果后回答
```

**这证明**：Agent 真的在循环里——LLM 说"要调工具"→ Agent 执行 → 结果回喂 → LLM 再回答。

---

## 五、实战踩的坑（这是最有价值的学习点）

> 教训：**开源项目主分支在快速演进，examples/ 目录往往过时**。学的时候要以源码为准，别迷信示例。

### 坑 1：examples 全部用旧 API
`examples/mock_sqlite_example.py` 调用 `tool_registry.register(...)`，但实际方法是 `register_local_tool(tool, access_groups)`。

### 坑 2：Agent 构造参数和 README 不一致
README 示例只传 `llm_service` + `tool_registry`，但实际 `Agent.__init__` 还要求 `user_resolver` + `agent_memory`。

### 坑 3：send_message 签名变了
examples 用 `send_message(user=user, ...)`，实际是 `send_message(request_context=..., ...)`。

### 怎么应对
**不要逐个改示例**（会陷入无穷适配），而是**用当前真实 API 自己组装**。我写的 `01_最小可运行Agent.py` 和 `02_触发工具调用.py` 就是干这个的。

---

## 六、README 提到的生产功能（对应源码位置）

| 功能 | README 说 | 源码位置 |
|------|----------|---------|
| Lifecycle Hooks | 配额、日志、内容过滤 | `core/lifecycle/base.py` |
| LLM Middlewares | 缓存、prompt 工程 | `core/middleware/base.py` |
| Conversation Storage | 会话持久化 | `core/storage/base.py` + `integrations/local/storage.py` |
| Observability | 追踪和指标 | `core/observability/base.py` |
| Context Enrichers | RAG、记忆增强 | `core/enricher/base.py` |
| Evaluation | 评测体系 | `core/evaluation/`（dataset/evaluators/runner/report）|

---

## 七、对照我的 `ai_assistant` 项目

| Vanna 概念 | 我的 ai_assistant | 差距 |
|-----------|------------------|------|
| Agent 循环（while + ToolCall）| 8 步 if-else 固定顺序 | ❌ 该学 Vanna 的循环 |
| ToolRegistry（多工具注册）| 写死的 1 个 sql 工具 | ❌ 该加工具注册表 |
| ToolContext（每层带用户）| 权限只在 pipeline 判一次 | ❌ 权限该落到工具粒度 |
| agent_memory（记住成功查询）| 无记忆 | ❌ 该加训练式 RAG |
| LlmService（流式）| 无流式 | ❌ 该加流式支持 |

---

## 八、下一步学习指引

- **阶段 2**：读透 `core/tool/base.py` + `core/llm/base.py` + `core/tool/models.py`（四个核心抽象）
- **阶段 3**：看 3 个集成实现（sqlite/mock/openai），理解"可插拔"
- **阶段 4**：学记忆系统（`capabilities/agent_memory/` + `tools/agent_memory.py`）
- **阶段 5**：看 FastAPI 服务层（`servers/fastapi/`）
- **阶段 6**：看评测体系（`core/evaluation/`）

> 学习心法：每学一个概念，问自己"我的 ai_assistant 缺这个吗？该怎么加？"然后用 Vanna 式循环重构自己的项目。
