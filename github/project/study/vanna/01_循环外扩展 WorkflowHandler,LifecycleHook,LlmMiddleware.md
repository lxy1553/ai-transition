# 循环外扩展点（WorkflowHandler / LifecycleHook / LlmMiddleware）

> 这是从 `01_主干01_Agent循环.md` 第三部分单独复制出来的扩展点章节。
> Hook 属于主干① Agent 循环的 3 个外围扩展点之一。
> 完整上下文见 `01_主干01_Agent循环.md`。

# 第三部分：循环外三个扩展点

> 这三个扩展点把"灵活性"放在循环外，核心循环保持收敛（就一个 `is_tool_call`）。

## 全景图

```
_send_message（agent.py）
  │
  ├─ 274行  is_starter_request and workflow_handler → get_starter_ui()
  ├─ 365行  for hook: hook.before_message()     【ⓑ-1】
  ├─ 449行  workflow_handler.try_handle()       （命令拦截）
  ├─ 循环内：
  │    ├─ 1244 middleware.before_llm_request()  【ⓒ-1】
  │    ├─ 1290 middleware.after_llm_response()  【ⓒ-2】
  │    ├─ 787  hook.before_tool()               【ⓑ-2】
  │    └─ 848  hook.after_tool()                【ⓑ-3】
  └─ 1119 hook.after_message()                  【ⓑ-4】
```

## ⓐ WorkflowHandler —— 命令拦截器 / 确定性流程

**三问**：
- Q1：有些消息不该进 LLM 循环（/help /status /reset），用确定性代码拦截
- Q2：进循环之前（agent.py:449）
- Q3：斜杠命令进 LLM → 浪费 token、回答不可靠

**接口**（`core/workflow/base.py`）：
```python
@dataclass
class WorkflowResult:
    should_skip_llm: bool            # True=我处理了别进LLM；False=放行
    components: list = None          # 返回给用户的 UI
    conversation_mutation = None     # 可改会话状态（/reset 清空历史）

class WorkflowHandler(ABC):
    async def try_handle(self, agent, user, conversation, message) -> WorkflowResult: ...
```

**默认实现**（`core/workflow/default.py`）——命令分发器：
```
/help      → 帮助文本（admin 看管理命令）
/status    → 检查配置状态（SQL/记忆/可视化齐不齐）
/memories  → 查看最近记忆
/delete id → 删记忆
其他       → should_skip_llm=False 放行
```

**关键字段**：`should_skip_llm=True` = 不进 LLM；`False` = 放行；`conversation_mutation` = 改会话。

### 真实代码逐步走一遍（`core/workflow/default.py` 的 try_handle）

> 这个 handler 本质就是一个 **if/elif 命令分发器**——用户说什么，匹配哪个分支，返回对应结果。下面跟着代码走。

```python
async def try_handle(self, agent, user, conversation, message) -> WorkflowResult:
    """处理基础命令，其余放行给 LLM"""

    # ── 分支 1：/help 帮助命令 ──
    if message.strip().lower() in ["/help", "help", "/h"]:
        # ① 判断是不是管理员（影响帮助内容）
        is_admin = "admin" in user.group_memberships
        # ② 拼帮助文本（普通用户 vs 管理员看到不同命令）
        help_content = "## 🤖 Vanna AI Assistant\n\n..."
        if is_admin:
            help_content += "\n**🔒 Admin Commands**\n- `/status`...\n- `/memories`...\n"
        # ③ 返回：不进 LLM，直接把帮助文本给用户
        return WorkflowResult(
            should_skip_llm=True,          # ★ 不进 LLM 循环
            components=[UiComponent(       # 返回 UI 组件（前端渲染）
                rich_component=RichTextComponent(content=help_content, markdown=True),
                simple_component=None,
            )],
        )

    # ── 分支 2：/status 状态检查（仅管理员）──
    if message.strip().lower() in ["/status", "status"]:
        # ① 权限检查：非管理员直接拒绝
        if "admin" not in user.group_memberships:
            return WorkflowResult(should_skip_llm=True, components=[拒绝组件])
        # ② 管理员：检查系统配置（SQL/记忆/可视化齐不齐）
        return await self._generate_status_check(agent, user)

    # ── 分支 3：/memories 查看记忆（仅管理员）──
    if message.strip().lower() in ["/memories", "memories", "/recent_memories", "recent_memories"]:
        if "admin" not in user.group_memberships:
            return WorkflowResult(should_skip_llm=True, components=[拒绝组件])
        return await self._get_recent_memories(agent, user, conversation)

    # ── 分支 4：/delete id 删记忆（仅管理员）──
    if message.strip().lower().startswith("/delete "):
        if "admin" not in user.group_memberships:
            return WorkflowResult(should_skip_llm=True, components=[拒绝组件])
        memory_id = message.strip()[8:].strip()   # ★ 从消息里提取 ID（"/delete "后8位起）
        return await self._delete_memory(agent, user, conversation, memory_id)

    # ── 兜底：不是我认识的命令 → 放行给 LLM ──
    return WorkflowResult(should_skip_llm=False)   # ★ 关键：放行进循环
```

**跟着用户输入走一遍**：
```
用户输入 "/help"
  → 命中分支1 → 判断 admin → 拼帮助文本 → should_skip_llm=True → 返回帮助，不进 LLM ✅

用户输入 "/status"
  → 命中分支2 → 非 admin？→ 拒绝。是 admin？→ 检查系统状态 ✅

用户输入 "上个月逾期率是多少"
  → 不匹配任何命令分支 → 兜底 should_skip_llm=False → 放行给 LLM 循环 ✅
```

**这个模式揭示了**：
1. **try_handle = 命令的"白名单"**——认识的命令确定性处理，不认识的放行
2. **权限在 handler 里判断**（is_admin / group_memberships）——命令级权限
3. **should_skip_llm 是核心开关**——True=我处理了，False=放行给 LLM

### 真实用法（`examples/default_workflow_handler_example.py`）

```python
from vanna import Agent, DefaultWorkflowHandler, MockLlmService
from vanna.core.registry import ToolRegistry

# 组装：把 DefaultWorkflowHandler 传给 Agent
agent = Agent(
    llm_service=MockLlmService(response_content="I'm ready to help!"),
    tool_registry=ToolRegistry(),          # 空工具（场景1）
    workflow_handler=DefaultWorkflowHandler(),   # ★ 注入 workflow handler
    config=AgentConfig(stream_responses=False),
)

# 触发欢迎界面：空消息 + starter_ui_request 标记
# → workflow_handler 生成欢迎卡片，不调 LLM
async for component in agent.send_message(
    request_context=user_resolver.create_request_context(
        metadata={"starter_ui_request": True}   # ★ 关键：标记启动请求
    ),
    message="",                 # 空消息
    conversation_id="empty-setup",
):
    ...
```

**关键机制**：
- `get_starter_ui()` 按工具配置生成欢迎卡片（无工具→"需要配置"；齐全→"系统就绪"）
- **空消息 + starter_ui_request** → 返回欢迎界面，不进 LLM（省 token）

### 自定义命令示例（你的业务命令）

```python
class CreditWorkflowHandler(WorkflowHandler):
    """信贷业务命令拦截器"""

    async def try_handle(self, agent, user, conversation, message):
        if message.strip().lower() in ["/myquota", "配额"]:
            # 返回用户剩余配额
            quota = get_user_quota(user.id)
            return WorkflowResult(
                should_skip_llm=True,
                components=[RichTextComponent(content=f"你的剩余配额：{quota} 次")],
            )
        if message.strip().lower() == "/reset":
            # 清空会话历史
            async def clear(conv): conv.messages.clear()
            return WorkflowResult(
                should_skip_llm=True,
                components=[...],
                conversation_mutation=clear,   # ★ 改会话状态
            )
        return WorkflowResult(should_skip_llm=False)   # 放行
```

**为什么自定义**：默认 handler 只有 /help /status /memories /delete。你的业务命令（查配额/重置）要自己实现——这就是"确定性代码"处理，不烧 token。

> **类比**：客服 IVR 语音菜单——按 1/2/3 走固定流程，按错转人工（LLM）。

## ⓑ LifecycleHook —— 消息全生命周期钩子

**三问**：
- Q1：在关键节点插入自定义逻辑（配额/日志/过滤/改写结果）
- Q2：4 个钩子点分布全链路（365 循环前 / 787、848 循环内 / 1119 循环后）
- Q3：无法做横切关注点，只能写死进核心

**接口**（`core/lifecycle/base.py`）：
```python
class LifecycleHook(ABC):
    async def before_message(self, user, message) -> Optional[str]:
        # 返回改写后的消息，或 None 保持原样；抛 AgentError 可中断
        return None
    async def after_message(self, result) -> None: ...
    async def before_tool(self, tool, context) -> None: ...   # 抛异常可阻止
    async def after_tool(self, result) -> Optional[ToolResult]: ...  # 可改写结果
```

**真实实现**（`examples/quota_lifecycle_example.py`）：
```python
class QuotaCheckHook(LifecycleHook):
    async def before_message(self, user, message):
        if usage >= quota:
            raise QuotaExceededError("配额已用完")   # ★ 抛异常 = 中断
        self._user_usage[user.id] = usage + 1
        return None
```

**关键点**：多个钩子按顺序执行；返回值 None=不改 / 字符串=替换 / 抛异常=中断。

### 每个钩子点：如何实现 + 为什么

#### before_message —— 消息进 LLM 前（agent.py:373）

**实现方式**（返回值和中断）：
```python
class MyHook(LifecycleHook):
    async def before_message(self, user, message):
        # ① 返回 None → 消息原样放行
        # ② 返回字符串 → 替换消息（如过滤敏感词后重写）
        # ③ 抛 AgentError → 中断处理，消息不进 LLM
        return None
```

**为什么这样设计**：
- **返回值决定"改不改"**：`hook_result is not None` 才替换（agent.py:374-375）。这样"只观察不干预"的钩子（如日志）和"会改写"的钩子（如过滤）共用同一接口，互不干扰。
- **抛异常决定"进不进"**：`AgentError` 向上传播 → 整个 `send_message` 异常 → 消息不进 LLM。配额超了、命中敏感词，直接拦下。

**典型用法**：
```python
class QuotaCheckHook(LifecycleHook):
    async def before_message(self, user, message):
        if user_usage(user) >= quota(user):
            raise AgentError("配额已用完，请明天再试")   # 中断
        return None

class SensitiveFilterHook(LifecycleHook):
    async def before_message(self, user, message):
        if "密码" in message:
            return message.replace("密码", "****")      # 改写
        return None
```

#### before_tool —— 工具执行前（agent.py:787-800）

**实现方式**：
```python
class PermissionCheckHook(LifecycleHook):
    async def before_tool(self, tool, context):
        if tool.name == "run_sql" and not can_use(user=context.user):
            raise AgentError(f"无权限使用 {tool.name}")   # ★ 阻止工具执行
        # 不抛异常 = 放行
```

**为什么这样设计**：
- 它在 `registry.execute()` **之前**调用（agent.py:800 → 827）。只要抛异常，工具根本不会执行——这是"第二道权限检查"（第一道是 `registry._validate_tool_permissions`）。
- 和 registry 权限的区别：**registry 是"工具级"静态检查，before_tool 是"动态/业务级"检查**（比如根据用户当前状态、审批流决定）。二者互补。

#### after_tool —— 工具执行后（agent.py:848-859）

**实现方式**：
```python
class MaskPiiHook(LifecycleHook):
    async def after_tool(self, result):
        # 改写工具结果：把手机号打码
        if result.success and "phone" in str(result.result_for_llm):
            result.result_for_llm = mask_phone(result.result_for_llm)
        return result    # 返回改写后的 result（或 None 保持原样）
```

**为什么这样设计**：
- 它在 `tool.execute()` **之后**、`result` 回喂 LLM **之前**调用（agent.py:827 → 848 → 987）。
- **返回值决定"改不改"**：返回 `ToolResult` = 替换结果；返回 `None` = 保持原样（agent.py:859 `modified = await hook.after_tool(result)`）。
- 典型用途：**列级脱敏**——工具查到了手机号，这里打码后才回喂给 LLM 和用户。这是"数据权限"第 2.2 层"列级脱敏"的实现点之一。

#### after_message —— 整条消息处理完（agent.py:1119）

**实现方式**：
```python
class AuditHook(LifecycleHook):
    async def after_message(self, result):
        # 记录整条消息的处理结果（日志/指标/审计）
        logger.info(f"Message processed: {result}")
        audit_log.write(result)
        # 不返回任何东西
```

**为什么这样设计**：
- 它在循环完全结束、所有 `yield` 都发出后调用（agent.py:1111-1119）——此时整条消息已处理完。
- **只观察，不干预**（返回 `None`）：适合日志、指标、审计这些"事后记录"。
- 对应权限五层第 ⑤ 层（审计）——"谁、何时、操作了什么"就在这里记录。

### 4 个钩子点对比（如何 + 为什么）

| 钩子 | 位置 | 返回值作用 | 中断方式 | 典型用途 | 对应权限层 |
|------|------|-----------|---------|---------|-----------|
| before_message | 循环前 373 | None=不改 / 字符串=替换 | 抛 AgentError | 配额/敏感词过滤 | Rate limiting |
| before_tool | 循环内 787 | 无 | 抛 AgentError | 动态权限/审批 | 授权层 2 |
| after_tool | 循环内 848 | None=不变 / ToolResult=替换 | 无（只能改结果）| 列级脱敏 | 授权层 2.2 列级 |
| after_message | 循环后 1119 | 无 | 无 | 日志/指标/审计 | 审计层 5 |

### 为什么用"4 个分散点"而不是"1 个回调"

**核心设计思想：横切关注点（cross-cutting concerns）不污染核心逻辑。**

- 如果配额/日志/权限/脱敏全写进 `_send_message` → 核心循环变成几百行，没法读
- 拆成 4 个钩子点 + 任意多个 hook 实例 → 核心保持干净，关注点可插拔

**对应到你的 ai_assistant**：
```python
# 你的 pipeline 现在把"配额/日志/权限"写死在代码里
def ask(self, query, user_role):
    if not self.permission.check(...): return 拒绝   # 权限写死
    result = executor.execute(sql)                    # 查询写死
    audit.log(...)                                    # 审计写死

# 改造成 LifecycleHook 式：
# 1. 加 before_message hook → 配额检查
# 2. 加 before_tool hook → 动态权限（查权限表）
# 3. 加 after_tool hook → 结果脱敏（手机号打码）
# 4. 加 after_message hook → 审计
# pipeline 核心只剩"查数逻辑"，横切关注点全部外置
```

> **类比**：安检口——登机前（before_message）、过安检（before_tool）、取行李（after_tool）、离店结账（after_message），每个关键节点都有人查，但"查什么"可以随时增减。

### 为什么要插入自定义逻辑？（本质）

**核心原因：Agent 是"通用引擎"，不懂你的业务规则。**

Vanna 的 Agent 循环是通用的——它只知道"问 LLM → 调工具 → 回喂"，**不知道**：
- 你的免费用户一天只能问 5 次（配额）
- 你的系统不能回答涉及他人隐私的问题（过滤）
- 你的风控 SQL 查出的手机号不能直接给用户看（脱敏）
- 每一次查询都要留痕（审计）

这些是**你的业务规则**，Vanna 不可能内置。所以它开了 4 个"插槽"（钩子点），让你把规则插进去。

> **"插入"的本质**：把"会变的业务规则"和"不变的引擎逻辑"分开。配额/敏感词/脱敏随业务变，钩子让它们能单独增删，不碰引擎。换业务（信贷→电商）只改钩子，不改引擎。

### 每个钩子点插入的是什么？（信贷场景例子）

#### before_message —— 插入"准入规则"（这条消息能不能进、要不要改）

**配额（超过配额就报错？—— 是的，AgentError 中断）**
```python
class QuotaCheckHook(LifecycleHook):
    """业务规则：每个用户每天最多 5 次查询"""
    async def before_message(self, user, message):
        used = get_today_usage(user.id)
        if used >= 5:                           # ★ 超过配额
            raise AgentError("今日配额已用完")   # 中断，消息不进 LLM
        increment_usage(user.id)                # 没超，计数 +1
        return None                             # 放行
```
**配额"超过配额报错"？** —— 对，但报的是 `AgentError`（中断处理），不是普通报错。它让整条消息流程停止，不浪费 token 调 LLM。

**敏感词过滤（过滤的什么？—— 用户输入 message 里的敏感内容）**
```python
class SensitiveFilterHook(LifecycleHook):
    """业务规则：用户不能问涉及他人隐私的问题"""
    async def before_message(self, user, message):
        if "张三的征信" in message:                 # ★ 过滤：用户输入里的敏感内容
            raise AgentError("无权查询他人征信信息")   # 直接拦
        if "密码" in message:
            return message.replace("密码", "****")   # 或改写：敏感词打码后往下走
        return None
```
**过滤的什么？** —— 用户的输入 message。两种方式：直接拦（抛异常）或改写（返回替换后的字符串）。

#### before_tool —— 插入"工具准入规则"（这个工具这次能不能用）

```python
class ApprovalHook(LifecycleHook):
    """业务规则：超过 100 万授信的查询要人工审批"""
    async def before_tool(self, tool, context):
        if tool.name == "run_sql" and "credit_limit > 1000000" in context.metadata.get("sql", ""):
            raise AgentError("大额授信查询需人工审批")   # 阻止这次工具执行
        # 不抛异常 = 放行
```
**和 registry 权限的区别**：registry 查"张三是不是 risk 组"（静态）；这里查"这次查询是不是大额"（动态/业务）。二者互补。

#### after_tool —— 插入"结果改写规则"（工具结果要不要改、改成什么）

```python
class MaskPiiHook(LifecycleHook):
    """业务规则：查询结果里的手机号必须打码"""
    async def after_tool(self, result):
        if result.success:
            # ★ 改写：13812345678 → 138****5678
            result.result_for_llm = re.sub(r'\b1[3-9]\d{9}\b', '138****5678', str(result.result_for_llm))
        return result    # 返回改写后的结果
```
**改写什么改成什么？** —— 改写工具返回的数据，把敏感字段改成掩码。工具查出了完整手机号，这里打码后才回喂给 LLM / 展示给用户。这是权限五层"第 2.2 层列级脱敏"的实现点。

#### after_message —— 插入"记录规则"（处理完留痕）

```python
class AuditHook(LifecycleHook):
    """业务规则：每次查询都要留审计日志"""
    async def after_message(self, result):
        audit_log.write({
            "user": result.user_id, "query": result.query,
            "sql": result.sql, "timestamp": now(),
        })   # 只记录，不干预
```
对应权限五层"第 ⑤ 层审计"。

### 一条完整消息的旅程（4 钩子串起来）

用户问"上个月逾期率"：
```
① before_message —— 配额检查（今天问了几次？超 5 次拦下）
      ↓ 通过
② before_tool —— 工具准入（查逾期率需要 analyst 权限？有，放行）
      ↓ 通过
③ run_sql 执行 → 查出逾期率 3.2%
      ↓
④ after_tool —— 结果脱敏（结果里没手机号？不改）
      ↓
⑤ LLM 生成回答 → 返回用户
      ↓
⑥ after_message —— 审计（记录"张三 14:00 查了逾期率"）
```

### 为什么用钩子而不是写死在 pipeline 里

| 写法 | 问题 |
|------|------|
| 写死在 pipeline 里 | 换业务（信贷→电商）要改核心代码，引擎不能复用 |
| 用钩子插入 | 核心引擎不变，业务规则可插拔，一套引擎服务多个业务 |

> **一句话**：**"插入" = 把会变的业务规则（配额/权限/脱敏/审计）从不变的引擎逻辑里抽出来**，通过 4 个钩子点插回去。引擎通用，业务可换。

### hook 的本质（grill-me 修正记录）

> 我最初理解 hook 是"在核心逻辑前/后检查或插入业务规则"。grill-me 挖出 3 个偏差点，修正为准确理解。

**✅ 对的部分**：位置对（逻辑前/循环中/后）；是检查；插业务规则。

**❌ 修正 1：hook 是"织进"核心逻辑，不是"旁边加一步"**

不是排队式（核心逻辑 → hook → 核心逻辑），而是核心逻辑**内部**嵌了可插入点。看真实代码：
```python
# agent.py —— before_tool 就嵌在"工具执行"这一行前面
for tool_call in response.tool_calls:        # 循环内部
    tool = await registry.get_tool(tool_call.name)
    for hook in lifecycle_hooks:             # ★ hook 嵌在这里
        await hook.before_tool(tool, context)  # 能抛异常拦停后续
    result = await registry.execute(tool_call)  # 真正的工具逻辑
```
hook 能在**执行中**抛异常，让后面全部短路——不是"检查完再继续"那么被动。

**❌ 修正 2：hook 有两种能力——拦截 + 改写，不只是"检查"**

| 能力 | 机制 | 例子 |
|------|------|------|
| 拦截/中断 | 抛异常 → 短路 | 配额超了拦下 |
| 改写 | 返回新值 → 替换 | 结果脱敏、消息过滤 |

改写不是检查——它在逻辑后**改变结果**再往下传：
```python
result = await registry.execute(tool_call)   # 查出 13812345678
for hook in lifecycle_hooks:
    modified = await hook.after_tool(result)  # ★ 改成 138****5678
# 用改写后的结果继续
```
如果只理解成"检查"，会漏掉"脱敏/改写"这类核心用途。

**❌ 修正 3：4 个钩子点钩的是"不同粒度的核心"，不是同一个核心的一圈**

```
before_message / after_message → 钩"整条消息处理"（消息级）
before_tool / after_tool       → 钩"单个工具执行"（工具级）
```
所以是"两对（前/后）钩子点"，各自钩不同粒度的核心。before_tool 是**每个工具都过一遍**，before_message 是**每条消息过一遍**——粒度不同，设计时要分清。

**📋 修正后的准确理解**：
> hook = 织进核心逻辑的**可插入点**（不是旁边加一步）。
> 每个点能：①拦截（抛异常短路）②改写（返回新值替换）。
> 4 个点钩的是**不同粒度的核心**（消息级 × 2 + 工具级 × 2）。
> 用途：插入你的业务规则（配额/权限/脱敏/审计）。

**对照 ai_assistant**：
```python
# 现在：业务规则写死在 pipeline
def ask(self, query, user_role):
    if not permission.check(...): return 拒绝    # 权限写死
    result = executor.execute(sql)                # 查询写死
    audit.log(...)                                # 审计写死

# hook 式：核心只留查数，规则外置
# before_message → 配额/过滤（可拦截）
# before_tool → 权限（可拦截）
# after_tool → 脱敏（可改写）
# after_message → 审计（记录）
```

### 业务规则分四层（grill-me 修正记录）

> 我最初理解"主干固定，业务规则只写在 hook 中"。grill-me 挖出：**hook 不是"规则的全部"，只负责"约束层"**。

**✅ 对的部分**：主干骨架固定 ✅；横切规则（配额/权限/脱敏/审计）进 hook ✅。

**❌ 修正：业务规则不是一坨，分四层**

| 层 | 是什么 | 放哪 | 例子 |
|----|--------|------|------|
| ① 能力层 | Agent 能做什么 | **Tool** | 查库/查征信/画图（RunSqlTool.execute）|
| ② 数据层 | 规则依据的数据 | **DB/配置** | 权限表、配额表、indicators.yaml 的 required_role |
| ③ 约束层 | 在什么时机拦截/改写 | **hook** | 配额检查、权限判断、脱敏、审计 |
| ④ 配置层 | 引擎怎么跑 | **AgentConfig** | max_tool_iterations、temperature、stream_responses |

**关键认知**：
- hook 只负责**③约束层**——"在正确的时机拦截/改写"
- 但"能力（Tool）"、"数据（权限表）"、"配置（AgentConfig）"这些**仍然是业务**，写在别处
- 所以"业务规则只写在 hook"是错的——**业务规则分布四层，hook 只占一层**

**真实代码佐证**（工具本身 = 业务能力）：
```python
class RunSqlTool(Tool):
    async def execute(self, context, args):
        result = sql_runner.run_sql(args.sql)   # ★ 连库、执行——业务核心，在 Tool
        return ToolResult(...)
```
Vanna 不可能内置"查信贷数仓"，这是你的业务，写在 Tool。hook 管"规则"，Tool 管"能力"。

**为什么必须分四层**：
- 能力层 → 决定"能做什么"（Tool）
- 数据层 → 决定"依据什么判断"（权限表/配额表）
- 约束层 → 决定"在什么时机拦/改"（hook）
- 配置层 → 决定"引擎怎么跑"（AgentConfig）

** **（你现在的业务其实已分布四处）：
```python
# ① 能力：sql_generator + executor（查数）→ 能力层
# ② 数据：indicators.yaml 的 required_role → 数据层
# ③ 约束：permission.check（当前写死在 pipeline）→ 约束层，该进 hook
# ④ 配置：settings.yaml → 配置层
```
**你的 pipeline 的问题不是"业务写死在主干"，而是"约束层（权限判断）和主干混在一起"**。正确的改造：约束层（权限/审计）抽到 hook，能力/数据/配置保持现状。

> **一句话**：hook 是"业务规则的**约束时机**"，不是"业务规则的全部"。能力在 Tool、数据在 DB、约束在 hook、配置在 AgentConfig——业务规则分四层，各归其位。

### Vanna hook 真实使用现状（查证）

> 全仓库搜"继承 LifecycleHook 的类"，真实存在的只有 examples 里的 2 个。

**Vanna 提供的**（真实）：
- `LifecycleHook` 接口（4 个钩子点）✅
- agent.py 里 4 个调用点（373/787/848/1119）✅
- examples 里 2 个示例（配额 + 日志）✅

**Vanna 没内置的**（要你自己写）：
- 敏感词过滤 ❌
- 结果脱敏 ❌
- 动态权限 ❌
- 任何业务 hook ❌

**结论**：Vanna 给了 hook 的"插槽"（4 个调用点）+ "最小示例"（配额/日志），**具体业务 hook 全要你自己实现**。

**Vanna 真实示例（examples/quota_lifecycle_example.py）**：
```python
class QuotaCheckHook(LifecycleHook):
    """配额检查（before_message）"""
    def __init__(self, default_quota: int = 10):
        self._user_quotas = {}    # 每用户配额
        self._user_usage = {}     # 每用户用量
        self._default_quota = default_quota

    async def before_message(self, user, message):
        if usage >= quota:
            raise QuotaExceededError(...)   # 抛异常中断
        self._user_usage[user.id] = usage + 1
        return None

class LoggingHook(LifecycleHook):
    """日志（before_message + after_message）"""
    async def before_message(self, user, message):
        print(f"[LOG] User {user.username} sent: {message[:50]}...")
        return None
    async def after_message(self, result):
        print("[LOG] Message processing completed")
```

---

## ⓒ LlmMiddleware —— LLM 调用的外层包装

**三问**：
- Q1：所有 LLM 调用都经过它——缓存/成本/请求改写/响应过滤
- Q2：包在 LLM 调用外（1244/1290 非流式，1317/1379 流式）
- Q3：无法缓存、无法控成本

**接口**（`core/middleware/base.py`）：
```python
class LlmMiddleware(ABC):
    async def before_llm_request(self, request) -> LlmRequest:
        # 发 LLM 前：查缓存、加 prompt 工程、记日志
        return request
    async def after_llm_response(self, request, response) -> LlmResponse:
        # 拿到响应后：写缓存、过滤内容、记成本
        return response
```

**真实实现**（`examples/extensibility_example.py`）：
```python
class CachingMiddleware(LlmMiddleware):
    def __init__(self): self.cache = {}
    async def before_llm_request(self, request):
        # 检查缓存是否命中（示例只检查，没真正短路返回）
        return request
    async def after_llm_response(self, request, response):
        self.cache[compute_key(request)] = response   # 写缓存
        return response   # ★ 必须返回 response，不能吞掉
```

> **⚠️ 坑**：`before_llm_request` 只返回 request，无法直接"短路返回缓存命中"。生产级要抛特殊异常/标记让框架跳过 LLM 调用。

### 完整调用链路走一遍（middleware 在循环里怎么被调）

> LlmMiddleware 不是"单独调用一次"，而是**每次 LLM 调用都经过**。它在 agent.py 的 `_send_llm_request` 里（1244/1290）。

```python
# agent.py:1241 —— 每次发 LLM 请求都会走这个方法
async def _send_llm_request(self, request):
    # ── 阶段 A：发 LLM 前，所有 middleware 的 before_llm_request ──
    for middleware in self.llm_middlewares:
        request = await middleware.before_llm_request(request)
        #   每个 middleware 都能改 request（加缓存key/记日志/加提示）
        #   返回的 request 传给下一个 middleware

    # ── 阶段 B：真正调 LLM ──
    response = await self.llm_service.send_request(request)
    #   ★ 这是唯一一次真实 LLM 调用

    # ── 阶段 C：拿到响应后，所有 middleware 的 after_llm_response ──
    for middleware in self.llm_middlewares:
        response = await middleware.after_llm_response(request, response)
        #   每个 middleware 都能改 response（写缓存/注入用户/记成本）
        #   返回的 response 传给下一个 middleware

    return response   # 最终 response 回给 while 循环
```

**跟着一次循环迭代走**：
```
while 循环第 1 次迭代：
  → _send_llm_request(request)
    → CachingMiddleware.before（查缓存）→ 没命中，继续
    → UserEchoMiddleware.before（无操作）
    → LLM 真实调用（花钱）
    → CachingMiddleware.after（写缓存）
    → UserEchoMiddleware.after（注入用户信息）
  → 返回 response → 循环判断 is_tool_call
```

**关键洞察**：
1. **middleware 是"洋葱式"嵌套**——先 before 全部，再 LLM，再 after 全部
2. **每次迭代都跑**——不是一次，是循环里每次发请求都经过
3. **能改 request 也能改 response**——两端都有钩子
4. **多 middleware 按顺序执行**——前面的输出是后面的输入

### 真实实现 2：UserEchoMiddleware（改响应注入用户信息，`examples/mock_auth_example.py`）

```python
class UserEchoMiddleware(LlmMiddleware):
    """把用户信息注入 LLM 响应（验证认证是否生效）"""

    async def after_llm_response(self, request, response):
        # 从 request.user_id（Agent 设置的）拿用户
        user_id = request.user_id

        # ★ 改写响应：替换成带用户信息的内容
        new_content = f"Hello! You are authenticated as: {user_id}"

        return LlmResponse(
            content=new_content,
            finish_reason=response.finish_reason,
            usage=response.usage,        # 保留原 usage
        )
```

### 怎么挂上去（真实用法）

```python
# mock_auth_example.py
agent = Agent(
    llm_service=llm_service,
    tool_registry=tool_registry,
    user_resolver=user_resolver,
    llm_middlewares=[UserEchoMiddleware()],   # ★ 注入中间件
    config=AgentConfig(stream_responses=True),
)
```

### LlmMiddleware 的更多用途（比缓存更常见）

| 用途 | before/after | 例子 |
|------|-------------|------|
| 缓存 | before 查 + after 写 | CachingMiddleware |
| **用户注入** | after 改写响应 | UserEchoMiddleware（认证验证）|
| **成本追踪** | after 记 usage | 每次调用 token 成本落库 |
| 请求改写 | before 改 request | 加 system hint / 重试标记 |
| 内容过滤 | after 过滤 response | 敏感词拦截 LLM 输出 |
| **降级/回退** | before 判断 | 主模型挂了切备用模型 |

> **类比**：CDN——每次访问先过缓存层，命中直接返回。

## 三个扩展点对比

| | WorkflowHandler | LifecycleHook | LlmMiddleware |
|---|---|---|---|
| **位置** | 进循环前 | 消息全生命周期 | LLM 调用外层 |
| **核心问题** | 这条消息要进 LLM 吗？ | 关键节点插什么？ | 每次 LLM 调用包什么？|
| **典型用途** | 斜杠命令 | 配额/日志/过滤 | 缓存/成本/改写 |
| **能否中断** | should_skip_llm=True | 抛 AgentError | 改 request/response |
| **接口位置** | `core/workflow/base.py` | `core/lifecycle/base.py` | `core/middleware/base.py` |
| **调用点** | agent.py:274/449 | 365/787/848/1119 | 1244/1290/1317/1379 |

**为什么三个而不是一个**：关注点/粒度/插入点不同——要不要进 LLM（消息级）/ 生命周期插什么（事件级）/ 每次调用包什么（调用级）。这就是"面向扩展设计"。

---

