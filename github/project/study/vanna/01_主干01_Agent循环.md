# 主干 ①：Agent 循环（完整版）

> 这是 04 系列（04 主干① Agent循环 / 04b 扩展点 / 04c 交互图 / 04d 问答记录 / 04e 代码详解）的**整合版**。
> 按"问题从进来到答案"的逻辑流组织，信息不丢失，重复部分已归并。
>
> 结构：
> - **第一部分**：完整交互图（7 步总览）
> - **第二部分**：每一步代码详解（位置 + 真实代码 + 注释）
> - **第三部分**：循环外三个扩展点（WorkflowHandler / LifecycleHook / LlmMiddleware）
> - **第四部分**：生产级分支（is_refusal / is_empty 补全）
> - **第五部分**：3 个易混淆点 + 核心心法

---

# 第一部分：完整交互图（7 步总览）

```
👤 用户："查一下客户数"
  │
  ▼
① 257  resolve_user(request_context)
  │     从请求解析出 User（id + group_memberships 权限组）
  ▼
② 270  is_starter_request?（空消息 / 首次进入）
  │     是 → get_starter_ui() 欢迎界面，不进 LLM
  ▼
③ 373  before_message hook（LifecycleHook 点1）
  │     配额检查 / 日志 / 过滤，可抛 AgentError 中断
  ▼
④ 449  workflow_handler.try_handle()
  │     识别斜杠命令？(/help /status...)
  │     should_skip_llm=True → 直接返回命令结果，不进循环
  │     should_skip_llm=False → 放行 ↓
  ▼
⑤ 646  while 循环 ★核心★
  │
  │    【第 N 次迭代】
  │    ├─ 1244 middleware.before_llm_request     （每次发前）
  │    ├─ 发请求给 LLM
  │    ├─ 1290 middleware.after_llm_response      （每次拿到后）
  │    │
  │    ├─ ★[生产级补全] is_refusal()? → 拒答 break
  │    ├─ ★[生产级补全] is_empty()? → 重试一次
  │    │
  │    ├─ 658 if response.is_tool_call():        ← Vanna 唯一大分支
  │    │     ├─ 存 assistant 消息（含 tool_calls）
  │    │     ├─ 787 before_tool hook（点2）
  │    │     ├─ registry.execute(tool) → 工具执行
  │    │     ├─ 848 after_tool hook（点3）
  │    │     ├─ 结果回喂（role=tool）
  │    │     └─ 重建 request → 回到 while 顶部
  │    │
  │    └─ else: yield 最终回答 → break
  │
  ▼
⑥ 1045 撞上限兜底（if 循环是因上限退出的）
  ▼
⑦ 1119 after_message hook（点4）日志/指标
  ▼
👤 用户收到答案
```

---

# 第二部分：每一步代码详解（①-⑦）

## ① resolve_user（agent.py:257）—— 解析"谁在问"

**代码位置**：`agent.py:257`，`_send_message` 开头。

```python
# agent.py:249-257
user_resolution_span = None
if self.observability_provider:          # 配了观测器就记录耗时
    user_resolution_span = await self.observability_provider.create_span(
        "agent.user_resolution",         # span 名
        attributes={"has_context": request_context is not None},
    )

# ★ 核心：请求 → User 对象（JWT/Cookie → id + group_memberships）
user = await self.user_resolver.resolve_user(request_context)

if self.observability_provider and user_resolution_span:
    user_resolution_span.set_attribute("user_id", user.id)
    await self.observability_provider.end_span(user_resolution_span)
```

**这一步的意义**：`user` 是后面一切的"主语"——权限判断、审计、个性化全用它。

## ② is_starter_request（agent.py:270-339）—— 空消息/首次进入 → 欢迎界面

**代码位置**：`agent.py:270`（判断）→ `agent.py:297`（欢迎 UI）→ `agent.py:339`（返回不进循环）。

```python
# agent.py:270 —— 判断是不是"启动请求"
is_starter_request = (not message.strip()) or request_context.metadata.get(
    "starter_ui_request", False   # ①空消息 ②前端显式标记
)

# agent.py:274 —— 是启动请求 且 配了 workflow_handler
if is_starter_request and self.workflow_handler:
    try:
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
        conversation = await self.conversation_store.get_conversation(conversation_id, user)
        if not conversation:
            conversation = Conversation(id=conversation_id, user=user, messages=[])

        # ★ 关键：workflow_handler 生成欢迎 UI
        components = await self.workflow_handler.get_starter_ui(self, user, conversation)
        #   → 根据工具配置生成欢迎卡片（"系统就绪" / "需要配置"）

        if components:
            for component in components:
                yield component
            yield UiComponent(rich_component=StatusBarUpdateComponent(status="idle", ...))
            yield UiComponent(rich_component=ChatInputUpdateComponent(placeholder="Ask...", disabled=False))

        return   # ★★ 直接返回！不进 LLM 循环！★★
    except Exception as e:
        logger.error(f"Error generating starter UI: {e}")

# agent.py:349 —— 真正空消息（且非启动）→ 直接返回
if not message.strip():
    return
```

**这一步的意义**：空消息/首次进入不调 LLM——返回欢迎界面，省 token、体验好。

## ②点五：构建 system_prompt（agent.py:571-641）—— 告诉 LLM"你是谁、能做什么"

**代码位置**：`agent.py:571`（get_schemas）→ `agent.py:599`（build_system_prompt）→ `agent.py:639`（_build_llm_request）。

### 完整流程（三件套）

```python
# agent.py:571 —— ① 获取用户有权用的工具（Registry 过滤）
tool_schemas = await self.tool_registry.get_schemas(user)
#   → 只返回用户有权限的工具（无权工具不进 prompt）

# agent.py:599 —— ② 构建 system_prompt（角色+日期+工具+指令）
system_prompt = await self.system_prompt_builder.build_system_prompt(
    user, tool_schemas
)
#   → 拼成："你是数据分析助手...今天日期...你能用这些工具：run_sql..."

# agent.py:639 —— ③ 打包成 LLM 请求（会话历史 + 工具 + system_prompt）
request = await self._build_llm_request(conversation, tool_schemas, user, system_prompt)
```

### 构建器实现（`core/system_prompt/default.py`）

```python
class DefaultSystemPromptBuilder(SystemPromptBuilder):
    async def build_system_prompt(self, user, tools):
        # ① 检查有哪些记忆工具（决定加不加记忆指令）
        tool_names = [tool.name for tool in tools]
        has_search = "search_saved_correct_tool_uses" in tool_names

        # ② 基础 prompt（角色 + 日期 + 行为准则）
        prompt_parts = [
            f"You are Vanna, an AI data analyst. Today's date is {today}.",
            "Response Guidelines:",
            "- Any summary should be the final step.",
            "- Use the available tools to help the user accomplish their goals.",
            "- When you execute a query, that raw result is shown to the user outside of your response.",
        ]

        # ③ 工具列表（★ 来自 get_schemas 过滤后的结果）
        if tools:
            prompt_parts.append(f"\nYou have access to the following tools: {', '.join(tool_names)}")

        # ④ 记忆工作流指令（如果配了记忆工具）
        if has_search:
            prompt_parts.append("\nMEMORY SYSTEM:")
            prompt_parts.append("- BEFORE executing any tool, call search_saved_correct_tool_uses...")

        return "\n".join(prompt_parts)
```

### 最终 prompt 长什么样（示例）

```
You are Vanna, an AI data analyst assistant. Today's date is 2026-08-17.

Response Guidelines:
- Any summary of what you did should be the final step.
- Use the available tools to help the user accomplish their goals.
- When you execute a query, that raw result is shown to the user outside of your response.

You have access to the following tools: run_sql, visualize_data, explain_definition

MEMORY SYSTEM:
- BEFORE executing any tool, you MUST first call search_saved_correct_tool_uses...
```

### 关键（get_schemas 的权限作用）

```
get_schemas(user)  →  过滤出有权工具（无权工具物理隔离）
      ↓
build_system_prompt(user, tools)  →  拼成 LLM 能读的 prompt
      ↓
LLM 被告知"你能用 run_sql, visualize_data" → 只能调这些
```

**get_schemas 决定"LLM 能做什么"**（工具过滤，详见 `03_主干03_Registry分派.md` 第四节），**build_system_prompt 决定"LLM 被告诉怎么做事"**（角色+工具+指令）。

### 对照 ai_assistant

你的 `pipeline.py` 现在没有明确的 system_prompt 构建器。改造建议：
- 加 `build_system_prompt(user, tools)` 方法
- 内容：角色（信贷数据分析助手）+ 日期 + 可用工具 + 行为准则（如"先查 Schema 再生成 SQL"）
- 用 `get_schemas(user)` 过滤工具，用户无权指标不进 prompt

## ③ before_message hook（agent.py:363-392）—— 配额/日志/过滤

**代码位置**：`agent.py:363`（循环外，进循环前）。

```python
# agent.py:363 —— 多个钩子按顺序执行
modified_message = message
for hook in self.lifecycle_hooks:
    # ★ 核心调用：hook 的 before_message
    hook_result = await hook.before_message(user, modified_message)
    #   返回值：None=不改；字符串=替换；抛异常=中断处理
    if hook_result is not None:
        modified_message = hook_result   # ★ 用 hook 返回的替换原消息

# agent.py:392 —— 用可能被改写后的消息
message = modified_message
```

**这一步的意义**：配额检查/日志/敏感词过滤都在这插。抛 `AgentError` 可中断——配额超了就拦住，不让 LLM 被调用。

## ④ workflow_handler.try_handle（agent.py:449-480）—— 斜杠命令拦截

**代码位置**：`agent.py:449`（调用）→ `agent.py:458`（should_skip_llm 分支）。

```python
# agent.py:449 —— 让 workflow_handler 尝试处理消息
workflow_result = await self.workflow_handler.try_handle(self, user, conversation, message)
#   返回 WorkflowResult:
#     should_skip_llm=True  → 我处理了（/help 等），别进 LLM
#     should_skip_llm=False → 不归我管，放行进循环

if workflow_result.should_skip_llm:
    # ★ 命令被处理，短路 LLM
    if workflow_result.conversation_mutation:
        await workflow_result.conversation_mutation(conversation)   # 如 /reset 清空历史

    if workflow_result.components:
        if isinstance(workflow_result.components, list):
            for component in workflow_result.components:
                yield component
        else:   # AsyncGenerator，流式 yield
            async for component in workflow_result.components:
                yield component

    yield UiComponent(rich_component=StatusBarUpdateComponent(status="idle", ...))
```

**这一步的意义**：斜杠命令（/help /status /memories /delete）用确定性代码处理，不浪费 token 给 LLM。

## ⑤ while 循环（agent.py:646-1042）★ 核心 + middleware

### 5.1 middleware（在 `_send_llm_request` 里，每次调用都执行）

**代码位置**：`agent.py:1241-1290`。

```python
# agent.py:1241 _send_llm_request
async def _send_llm_request(self, request):
    # ★ 发 LLM 前：before_llm_request 中间件（查缓存/改请求/记日志）
    for middleware in self.llm_middlewares:
        request = await middleware.before_llm_request(request)

    # 真正调用 LLM
    response = await self.llm_service.send_request(request)       # ★ 一次 LLM 调用

    # ★ 拿到响应后：after_llm_response 中间件（写缓存/过滤/记成本）
    for middleware in self.llm_middlewares:
        response = await middleware.after_llm_response(request, response)

    return response
```

### 5.2 核心循环（agent.py:646）

```python
# agent.py:646 —— 有上限的 while 循环（防死循环）
while tool_iterations < self.config.max_tool_iterations:
    # 发 LLM 请求（流式或非流式，都会经过 middleware）
    if self.config.stream_responses:
        response = await self._handle_streaming_response(request)   # 流式
    else:
        response = await self._send_llm_request(request)            # 非流式

    # ★ 判断 LLM 想干什么
    if response.is_tool_call():          # LLM 说"我要调工具"（agent.py:658）
        tool_iterations += 1

        # (a) 存 assistant 消息（含 tool_calls）—— OpenAI API 硬性要求
        assistant_message = Message(
            role="assistant", content=response.content or "", tool_calls=response.tool_calls,
        )
        conversation.add_message(assistant_message)

        # (b) 逐个执行工具
        tool_results = []
        for tool_call in response.tool_calls:
            tool = await self.tool_registry.get_tool(tool_call.name)   # 找到工具
            for hook in self.lifecycle_hooks:
                await hook.before_tool(tool, context)                 # before_tool（787）
            result = await self.tool_registry.execute(tool_call, context)  # ★ 执行（827）
            for hook in self.lifecycle_hooks:
                modified = await hook.after_tool(result)              # after_tool（848）
            tool_results.append({
                "tool_call_id": tool_call.id,
                "content": result.result_for_llm if result.success else result.error,
            })

        # (c) 把工具结果作为 role="tool" 回喂会话
        for tool_result in tool_results:
            conversation.add_message(Message(
                role="tool", content=tool_result["content"], tool_call_id=tool_result["tool_call_id"],
            ))

        # (d) 重建 request（带工具结果）→ 回到 while 顶部
        request = await self._build_llm_request(conversation, tool_schemas, user, system_prompt)

    else:
        # ★ LLM 说"我答完了"（agent.py:1013）
        if response.content:
            conversation.add_message(Message(role="assistant", content=response.content))
            yield UiComponent(rich_component=RichTextComponent(content=response.content, markdown=True), ...)
        break   # 退出循环
```

**这一步的意义**：循环是 Agent 的引擎——LLM 决定要不要调工具、调完看结果再决定，直到说"完了"。

## ⑥ 撞上限兜底（agent.py:1044-1085）—— 死循环安全网

**代码位置**：`agent.py:1044`（while 结束后）。

```python
# agent.py:1044 —— while 循环结束后，判断是否"撞上限退出"
if tool_iterations >= self.config.max_tool_iterations:
    logger.warning(f"Tool iteration limit reached: {tool_iterations}/{self.config.max_tool_iterations}")

    yield UiComponent(rich_component=StatusBarUpdateComponent(
        status="warning", message="Tool limit reached",
        detail=f"Stopped after {tool_iterations} tool executions. The task may be incomplete.",
    ))

    warning_message = f"""⚠️ **Tool Execution Limit Reached**
The agent stopped after executing {tool_iterations} tools (the configured maximum).
You can:
- Ask me to continue where I left off
- Adjust the `max_tool_iterations` setting
- Break the task into smaller steps"""
    yield UiComponent(rich_component=RichTextComponent(content=warning_message, markdown=True), ...)
```

**这一步的意义**：LLM 一直说"再调一次工具"时强制停止——宁可告诉用户"没做完"，也不能无限烧 token。

## ⑦ after_message hook（agent.py:1119）—— 收尾日志/指标

**代码位置**：`agent.py:1111`（遍历 hooks）→ `agent.py:1119`（调用 after_message）。

```python
# agent.py:1111 —— 循环结束后，遍历 hooks 收尾
for hook in self.lifecycle_hooks:
    await hook.after_message(conversation)   # ★ 整条消息处理完（日志/指标/审计）

# agent.py:1135 —— 观测：记录这次消息的关键指标
if self.observability_provider and message_span:
    message_span.set_attribute("tool_iterations", tool_iterations)
    hit_tool_limit = tool_iterations >= self.config.max_tool_iterations
    message_span.set_attribute("hit_tool_limit", hit_tool_limit)
    if hit_tool_limit:
        message_span.set_attribute("incomplete_response", True)   # 标记"可能没做完"
    await self.observability_provider.end_span(message_span)
```

**这一步的意义**：消息处理完后的收尾——日志、指标、审计都在这记。加上"撞上限"标记，观测系统能发现"哪些任务没做完"。

---

# 第三部分：循环外三个扩展点（简略版）

> 详细内容见 `01_循环外扩展 WorkflowHandler,LifecycleHook,LlmMiddleware.md`（每个扩展点独立成节）。

Vanna 用 3 个扩展点让核心循环保持收敛（核心就一个 `is_tool_call`），把灵活性放在循环外：

| 扩展点 | 位置 | 管什么 | 详细见 |
|--------|------|--------|--------|
| **WorkflowHandler** | 进循环前 | 命令拦截（/help /status），should_skip_llm 决定进不进 LLM | 详细文件 ⓐ |
| **LifecycleHook** | 全生命周期 | 4 钩子点（配额/日志/过滤/脱敏/审计），抛异常可中断 | 详细文件 ⓑ |
| **LlmMiddleware** | LLM 调用外层 | 缓存/成本/请求改写/响应过滤，洋葱式嵌套 | 详细文件 ⓒ |

```
用户消息
  → WorkflowHandler（命令拦截？进不进 LLM）
  → LifecycleHook（before_message：配额/过滤）
  → [while 循环：LlmMiddleware → LLM → LlmMiddleware]
  → LifecycleHook（after_message：审计）
```

**核心**：3 个扩展点 = 把"会变的业务规则"从"不变的引擎逻辑"里抽出来，可插拔。业务规则分四层（能力/数据/约束/配置），扩展点是"约束层"的执行时机。

# 第四部分：生产级分支（is_refusal / is_empty 补全）

> Vanna 循环内只有一个 `is_tool_call()` 判断。生产级该补两个响应分类。

## 核实结论

| 方法 | Vanna 有没有 | 证据 |
|------|-------------|------|
| `is_tool_call()` | ✅ | `core/llm/models.py:50` |
| `is_refusal()` | ❌ 没有 | LlmResponse 只有 is_tool_call |
| `is_empty()` | ❌ 没有 | 同上 |
| 空响应处理 | ❌ 没有 | else 分支只 if response.content yield |

## 补全代码（加到 LlmResponse）

```python
class LlmResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    finish_reason: Optional[str] = None   # "stop"/"tool_calls"/"content_filter"/"length"
    usage: Optional[Dict[str, int]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def is_tool_call(self) -> bool:
        return self.tool_calls is not None and len(self.tool_calls) > 0

    def is_refusal(self) -> bool:
        """安全拒绝：content_filter 触发（OpenAI）或 refusal（Anthropic）"""
        return self.finish_reason in ("content_filter", "refusal")

    def is_empty(self) -> bool:
        """空响应：content 和 tool_calls 都空"""
        return not self.content and not self.tool_calls
```

## 补全循环（加在 while 最前）

```python
while tool_iterations < max_tool_iterations:
    response = llm_service.send_request(request)

    # ① 安全检查（最先）
    if response.is_refusal():
        yield "抱歉，我无法回答这个问题"
        break

    # ② 空响应（先重试一次）
    if response.is_empty():
        if retry_count < 1:
            retry_count += 1
            continue
        yield "系统暂时无响应，请重试"
        break

    # ③ 混合响应（思考 + 调工具）
    if response.content and response.tool_calls:
        yield f"[思考] {response.content}"

    # ④ 工具调用（含失败处理）
    if response.tool_calls:
        tool_iterations += 1
        conversation.add_message(assistant_message)
        tool_results = []
        for tool_call in response.tool_calls:
            try:
                result = tool_registry.execute(tool_call, context)
            except Exception as e:
                result = ToolResult(success=False, error=f"执行失败: {e}")
            tool_results.append(result)
            conversation.add_message(tool_response_message)   # 错误也回喂
        request = _build_llm_request(conversation, context)
        continue

    # ⑤ 纯文本回答
    if response.content:
        yield response.content
        break

    # ⑥ 理论到不了的兜底
    logger.error(f"无法解析的响应: {response}")
    yield "系统遇到异常，请重试"
    break

# ⑦ 循环外：撞上限兜底
if tool_iterations >= max_tool_iterations:
    logger.warning(f"达到工具迭代上限")
    yield "任务太复杂没做完，请简化问题或重试"
```

## 生产级完整情况集（LLM 返回后要判断的）

> "Vanna 有没有"一列已逐行核实（`core/llm/models.py` + `agent.py` 646-1154）。

| # | 情况 | 处理 | Vanna |
|---|------|------|-------|
| 1 | tool_calls 有值 | 执行工具、回喂 | ✅ is_tool_call() |
| 2 | 直接回答 | 返回用户 | ✅ else |
| 3 | 工具不存在 | 告诉 LLM 换一个 | ✅ 错误返回 |
| 4 | 工具报错 | 错误回喂让 LLM 修正 | ✅ 错误也回喂 |
| 5 | 权限不足 | 拒绝 + 审计 | ✅ registry.py:161 |
| 6 | 参数不合 schema | 回喂让 LLM 重填 | ✅ registry.py:187 |
| 7 | 达到迭代上限 | 停止 + 警告 | ✅ agent.py:1045 |
| 8 | **空内容** | 兜底重试一次 | ❌ is_empty 不存在 |
| 9 | 日常对话 | 直接 LLM 答 | ✅ else |
| 10 | **refusal** | 明确拒答 | ❌ is_refusal 不存在 |
| 11 | **混合响应** | 先 yield 思考再执行 | ✅ agent.py:670 |

**核实结论**：Vanna 有 7 项、缺 2 项（refusal/empty）——它乐观假设 LLM 总返回有效内容。

---

# 第五部分：3 个易混淆点 + 核心心法

## 易混淆点 1：empty / is_refusal 的位置

**误区**：以为"问题刚进来"先判断。
**真相**：它们是对 **LLM 响应** 的判断，必须在**循环内 `response = llm(...)` 之后**。而且 Vanna 本身没有——是生产级补全。

## 易混淆点 2：4 个钩子的位置

**误区**：以为钩子都在循环外。
**真相**：before_message（373）循环前；before_tool（787）、after_tool（848）循环内；after_message（1119）循环后。

## 易混淆点 3：LlmMiddleware 的位置

**误区**：以为它是"循环前一步"。
**真相**：它在**循环内部每次迭代都跑**（1244 发前 / 1290 拿到后），不是"走完中间件再进循环"。

## 核心心法

> **Agent 循环 = 问 LLM → 判断 → 动手 → 回喂 → 再问 → 直到 LLM 说"完了"**。
> 从"脚本"到"Agent"的分水岭，就是这个 while 循环 + LLM 自主决定下一步。
> Vanna 的"收敛"是设计：核心只留 is_tool_call，灵活性放进三个扩展点。
> 生产级的差距 = 你补上的 is_refusal / is_empty（安全拒绝 + 空响应重试）。
