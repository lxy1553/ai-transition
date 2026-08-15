# Vanna 学习 04：主干① Agent 循环（agent.py 646-1060）

> 7 个主干逐个拆解的第 1 个。Agent 循环是整个 Vanna 的**心脏**——理解它 = 理解"Agent"这个词的本质。
>
> 代码位置：`src/vanna/core/agent/agent.py:646-1060`
> 关键配套：
> - `LlmResponse.is_tool_call()` —— 循环判断开关（`core/llm/models.py`）
> - `ToolRegistry.execute()` —— 循环里被调用的工具执行器（`core/registry.py`）

---

## 三问（先想清楚再读代码）

### Q1：它解决什么问题？

**回答一个根本问题：用户说了一句话，系统怎么决定"下一步做什么"。**

没有 Agent 循环时，系统是"脚本"——你写死 8 步流程，它按部就班走。但真实对话是动态的：
- 用户问"逾期率多少" → 要查数据库
- 用户问"逾期率怎么算" → 要解释，不用查库
- 用户接着问"那通过率呢" → 要记住上文，再查一次

**Agent 循环让 LLM 自己决定**："这一步我该直接回答，还是该调工具？调完工具我要不要再看结果继续？"
这就是 `Agent = LLM + 循环` 里的"循环"。

### Q2：它在数据流哪一环？

**它是数据流的"引擎"，所有其他主干都围绕它转：**

```
用户提问
  → ① 解析用户身份（主干⑥ UserResolver）
  → ② 构建 system_prompt（含所有工具 schema）
  → ③ ★进入 Agent 循环（本主干）★
        ├─ 发请求给 LLM（主干④ LlmService）
        ├─ LLM 说要调工具 → 调 Registry（主干③）→ 执行 Tool（主干②）
        ├─ 结果回喂给 LLM → 再问
        └─ LLM 说答完了 → 返回给用户
```

**一句话**：循环是"大脑转动的过程"，其他主干是"大脑需要的零件"。

### Q3：如果删掉它会怎样？

系统退化成"死脚本"：
- 没有自主性——LLM 不能决定调不调工具
- 没有多步推理——问"查一下再对比"这种任务做不了
- 无法失败回退——工具报错了，脚本不知道下一步该干啥

**这就是为什么 Vanna 是"Agent 框架"而不是"SQL 生成库"**——多出来的就是一个循环。

---

## 核心结构（先看骨架，再看细节）

```
while tool_iterations < max_tool_iterations:   ← ① 循环，有上限（防死循环）
    response = llm_service.send_request(request)  ← ② 问 LLM

    if response.is_tool_call():                  ← ③ LLM 说"我要调工具"
        tool_iterations += 1
        # ④ 把 LLM 的 tool_calls 存进会话历史
        conversation.add_message(assistant_message)
        # ⑤ 逐个执行工具
        for tool_call in response.tool_calls:
            result = tool_registry.execute(tool_call, context)  # 执行！
            tool_results.append(result.result_for_llm)
        # ⑥ 把工具结果作为 tool 消息回喂
        for tr in tool_results:
            conversation.add_message(tool_response_message)
        # ⑦ 重新构建 request（带工具结果）→ 回到循环顶部
        request = _build_llm_request(...)
    else:                                        ← ⑧ LLM 说"我答完了"
        yield response.content                    # 返回给用户
        break                                     # 退出循环
```

---

## 逐步拆解（每段代码 + 为什么）

### 步骤 ①：while 循环 + 迭代上限

```python
# agent.py:646
while tool_iterations < self.config.max_tool_iterations:
```

**为什么**：循环可能无限转下去（LLM 一直说"再调一次工具"），必须有个上限兜底。
`max_tool_iterations` 在 `AgentConfig` 里配，默认有限值。这是**防死循环的安全网**。

### 步骤 ②：问 LLM

```python
# agent.py:652-655
if self.config.stream_responses:
    response = await self._handle_streaming_response(request)   # 流式（打字机效果）
else:
    response = await self._send_llm_request(request)            # 非流式（一次性）
```

**为什么**：LLM 是循环的"大脑"，每次循环都要问它一次。
流式 = 边生成边返回（前端体验好）；非流式 = 全部生成完再返回（调试方便）。
我们阶段 1 的脚本用 `stream_responses=False`，就是为了看清一次完整响应。

### 步骤 ③：判断 LLM 想干什么

```python
# agent.py:658
if response.is_tool_call():
```

**关键**：`is_tool_call()` 是循环的开关。看它的实现（`core/llm/models.py`）：

```python
def is_tool_call(self) -> bool:
    """Check if this response contains tool calls."""
    return self.tool_calls is not None and len(self.tool_calls) > 0
```

**本质**：LLM 返回的响应里有没有 `tool_calls` 字段。
- 有 → LLM 说"我要调工具，参数是这些"
- 没有 → LLM 说"我直接回答你"

### 步骤 ④：把 LLM 的 tool_calls 存进会话历史

```python
# agent.py:663-668
assistant_message = Message(
    role="assistant",
    content=response.content or "",
    tool_calls=response.tool_calls,    # ★ 把"LLM 想调工具"这个意图存下来
)
conversation.add_message(assistant_message)
```

**为什么**：OpenAI API 有个硬性要求——**tool 消息必须跟在带 tool_calls 的 assistant 消息后面**。
如果不存这一步，后面回喂工具结果时 API 会报错。

### 步骤 ⑤：逐个执行工具（循环的"动手"环节）

```python
# agent.py:704-704
for i, tool_call in enumerate(response.tool_calls or []):
    ...
    # 关键两行（agent.py:785, 827）
    tool = await self.tool_registry.get_tool(tool_call.name)          # ① 按名字找到工具
    result = await self.tool_registry.execute(tool_call, context)     # ② 执行工具（带权限/校验）
```

**为什么分两步**：
- `get_tool(name)`：LLM 只说了工具名（如 "run_sql"），Agent 要从注册表里找到那个真实工具对象
- `execute(tool_call)`：真正执行，内部会做权限校验、参数校验、审计（这些在主干③详细讲）

**这一步是循环的"灵魂"**——工具真的被调用了，真的去查了数据库。

### 步骤 ⑥：把工具结果回喂给 LLM

```python
# agent.py:987-997（收集结果）
tool_results.append({
    "tool_call_id": tool_call.id,          # 对应 LLM 的 tool_call.id
    "content": result.result_for_llm       # ★ 给 LLM 看的结果（不是给用户看的）
})

# agent.py:1001-1007（回喂会话）
for tool_result in tool_results:
    conversation.add_message(Message(
        role="tool",                       # ★ role 是 "tool"
        content=tool_result["content"],
        tool_call_id=tool_result["tool_call_id"],
    ))
```

**为什么**：LLM 说了"调 run_sql"，但 LLM 自己看不到查询结果——它只是"告诉代码去查"。
**代码把结果作为 role="tool" 消息塞回会话，LLM 才能"看到"结果**，进而基于结果回答。

这是 Agent 循环最关键的一环：**LLM 是大脑，工具是手脚，消息是神经**。

### 步骤 ⑦：重新构建 request，回到循环顶部

```python
# agent.py:1010-1012
request = await self._build_llm_request(conversation, tool_schemas, user, system_prompt)
# 然后 while 继续，再次发请求给 LLM（这次请求里带了工具结果）
```

**为什么**：会话历史现在 = 用户问题 + LLM 说"要调run_sql" + 工具结果。把这个完整历史再发给 LLM，
LLM 就能基于"实际查询结果"决定下一步——要么回答，要么再调一次工具。

### 步骤 ⑧：LLM 答完了，退出循环

```python
# agent.py:1013-1042
else:   # 不是 tool_call，说明 LLM 直接回答了
    if response.content:
        conversation.add_message(Message(role="assistant", content=response.content))
        yield UiComponent(   # 返回给用户（可渲染成富文本）
            rich_component=RichTextComponent(content=response.content, markdown=True),
            simple_component=SimpleTextComponent(text=response.content),
        )
    break   # ★ 退出循环
```

**为什么**：LLM 没返回 tool_calls = 它觉得不需要再调工具了 = 答完了。把最终回答 yield 给前端，break 退出。

### 步骤 ⑨：迭代上限兜底

```python
# agent.py:1044-1058
if tool_iterations >= self.config.max_tool_iterations:
    logger.warning(f"Tool iteration limit reached: ...")
    # 给用户一个警告：任务可能没完成
```

**为什么**：如果 LLM 一直说"再调一次工具"（比如陷入死循环），达到上限后强制退出，并警告用户。
这是最后的兜底——**宁可告诉用户"没做完"，也不能无限烧 token**。

---

## 完整数据流转（一次真实对话的循环轨迹）

以阶段 1 的脚本 2（`02_触发工具调用.py`）为例，问"数据库里有多少客户？"：

```
第 1 次循环：
  发送请求（含用户问题 + 工具schema）
  → LLM 返回 {tool_calls: [run_sql: "SELECT COUNT(*) FROM Customer"], finish_reason: "tool_calls"}
  → is_tool_call() == True
  → 存 assistant 消息（含 tool_calls）
  → get_tool("run_sql") 找到工具
  → execute() 执行 SQL → 真查了 SQLite，返回 59
  → 把结果作为 role="tool" 消息加进会话
  → 重新构建 request（现在会话里有工具结果了）
  ↓
第 2 次循环：
  发送请求（含用户问题 + LLM的tool_calls + 工具结果"59"）
  → LLM 看到了结果，返回 {content: "查到了！数据库里共有 59 个客户", finish_reason: "stop"}
  → is_tool_call() == False
  → yield 最终回答给用户
  → break
```

**实际运行输出**（阶段 1 跑出来的）：
```
🤖 让我查一下数据库里的客户数量...      ← 第1次循环：LLM 返回 ToolCall
🤖 Tool completed successfully        ← 第1次循环：Agent 执行了 run_sql
🤖 查到了！数据库里共有 59 个客户。      ← 第2次循环：LLM 看到结果后回答
```

---

## 对照 ai_assistant 的改造动作

你的 `_handle_indicator_query` 现在是固定 8 步：

```python
# 你现在（固定顺序）：
intent = intent_classifier.classify(query)        # 步骤1
rewritten = query_rewriter.rewrite(query)         # 步骤2
indicator = catalog.get_indicator(indicator_name) # 步骤3
sql = sql_generator.generate(indicator, ...)      # 步骤4
validation = sql_validator.validate(sql)          # 步骤5
result = executor.execute(sql)                    # 步骤6
answer = explainer.explain(indicator, result)     # 步骤7
audit.log(...)                                    # 步骤8
```

改造目标（学 Vanna 的循环）——让"是否查数"由 LLM 决定：

```python
# 改造方向：while 循环 + LLM 决定下一步
while iterations < max_iterations:
    response = llm.send_request(request)           # 问 LLM（带工具schema）
    if response.is_tool_call():                     # LLM 说"要查数"
        for tc in response.tool_calls:
            result = registry.execute(tc)          # 执行工具（查数/解释/血缘）
            request.add_tool_result(result)        # 结果回喂
    else:
        answer = response.content                  # LLM 直接回答
        break
```

**改造要点**：
1. 你的 `intent_classifier` 从"决定走哪条路"变成"LLM 在循环里自己决定"
2. 你的 `sql_generator` / `executor` / `explainer` 变成一个个 **Tool**
3. 新增"循环 + 结果回喂"——LLM 能看到查询结果，能多步推理

---

## 附：生产级 Agent 循环——不止"调不调工具"一种 if

> 你在读 Vanna 的循环时问了一个关键问题："if 条件里只有 is_tool_call() 一种，实际生产肯定不止"。答案：对，生产级循环的分支远比这多。
> 这一节先看 Vanna 实际有哪些分支，再给完整情况集 + 修正版代码。

### Vanna 实际的分支（不止循环里的 2 个）

`_send_message` 是"大函数套小循环"，分三层：

**层级 1：循环外（发请求前）就有 3 道分叉**
```
_send_message(request_context, message)
  ├─ A. is_starter_request?（空消息/首次进入）
  │     → workflow_handler.get_starter_ui()  返回欢迎卡片，不调 LLM
  ├─ B. lifecycle_hooks 的 before_message 钩子
  │     → 钩子可改写 message（过滤敏感词、配额检查）
  └─ C. workflow_handler.try_handle(message)  ★ 命令拦截
        → 识别 /help /status /memories /delete 等斜杠命令
        → 命中则 should_skip_llm=True，直接返回命令结果，不进循环
```

**层级 2：循环内（646-1060），核心 2 个大分支 + 工具子分支**
```
while ...:
    response = llm(...)
    if response.is_tool_call():   ← 分支①：LLM 要调工具
        ...执行工具、回喂...
    else:                         ← 分支②：LLM 直接答
        yield content; break
```
但 ① 内部每个工具调用又有一堆子分支：
- 工具没找到（`get_tool` 返回 None）
- **权限不足**（`_validate_tool_permissions` 失败）
- **参数校验失败**（Pydantic 解析）
- **transform_args 返回 ToolRejection**（参数转换拒绝）
- 工具执行抛异常（try/except 包着）

**层级 3：循环外（结束后）还有兜底**
```
while 结束
  ├─ 撞上 max_tool_iterations → 警告"任务可能没做完"
  └─ error_recovery_strategy（若配置）→ 重试/降级
```

### 生产级完整情况集（LLM 返回后要判断的）

> ⚠️ **"Vanna 有没有"一列已经逐行核实过源码**（`core/llm/models.py` + `core/agent/agent.py` 646-1154），不是猜的。

| # | LLM 返回的情况 | 处理动作 | Vanna 有没有 |
|---|--------------|---------|-------------|
| 1 | `tool_calls` 有值 → 要调工具 | 执行工具、回喂结果 | ✅ `is_tool_call()` |
| 2 | `tool_calls` 空 → 直接回答 | 返回给用户 | ✅ else 分支 |
| 3 | **要调的工具不存在** | 告诉 LLM"这个工具没有"，让它换一个 | ✅ `registry.get_tool` 返回 None → ToolResult 错误 |
| 4 | **工具执行报错**（SQL 语法错/网络断）| 错误回喂给 LLM，让它修正重试 | ✅ `agent.py:991` `if result.success else result.error`，错误也回喂 |
| 5 | **权限不足** | 拒绝 + 审计，不让 LLM 绕过 | ✅ `registry.py:161` `_validate_tool_permissions` |
| 6 | **参数不合 schema**（LLM 填错参数）| 校验失败，回喂"参数无效"让 LLM 重填 | ✅ `registry.py:187` Pydantic 校验 |
| 7 | **达到迭代上限** | 停止 + 警告"任务可能没完成" | ✅ `agent.py:1045` |
| 8 | **LLM 返回空内容**（content 和 tool_calls 都空）| 兜底提示，重试一次 | ❌ **没有** `is_empty()` 不存在，空 content 就 yield 空 |
| 9 | **意图是日常对话**（无需工具）| 直接 LLM 答（就是分支②）| ✅ else 分支 |
| 10 | **refusal（安全拒绝）**（content_filter 触发）| 明确拒答，不进入后续 | ❌ **没有** `is_refusal()` 不存在，无法识别 |
| 11 | **混合响应（思考 + 调工具）**| 先 yield 思考，再执行工具 | ✅ `agent.py:670` `if response.content is not None` 在 tool_call 分支内 → 先 yield content 再执行工具 |

**核实结论**：
- Vanna **有**：混合响应（先 yield 思考再执行工具）、工具失败回喂、权限不足、参数校验、撞上限兜底
- Vanna **没有**：`is_refusal()`、`is_empty()`——它假设 LLM 总是返回有效 content 或 tool_calls，不单独处理"拒绝/空响应"
- 这正是"生产级要补"的地方（见下面的修正版循环，⑧⑨ 分支）

### 修正版完整循环（整合所有分支 + 你写的 + 补漏）


tool_iterations = 0
retry_count = 0

while tool_iterations < max_tool_iterations:
    response = llm_service.send_request(request)

    # ---------- ① 安全检查（最先，安全红线） ----------
    if response.is_refusal():
        yield "抱歉，我无法回答这个问题"
        break

    # ---------- ② 空响应（先重试一次，别直接放弃） ----------
    if response.is_empty():
        if retry_count < 1:
            retry_count += 1
            continue                     # 重新发请求
        yield "系统暂时无响应，请重试"
        break

    # ---------- ③ 混合响应（思考 + 调工具） ----------
    if response.content and response.tool_calls:
        yield f"[思考] {response.content}"   # 先让用户看到思考
        # 不 break，继续走工具执行（靠下方 ④）

    # ---------- ④ 工具调用（含失败处理，核心） ----------
    if response.tool_calls:
        tool_iterations += 1
        conversation.add_message(assistant_message)

        tool_results = []
        for tool_call in response.tool_calls:
            try:                                   # ★ 关键：包异常
                result = tool_registry.execute(tool_call, context)
            except Exception as e:
                result = ToolResult(success=False, error=f"执行失败: {e}")
            tool_results.append(result)
            conversation.add_message(tool_response_message)   # ★ 错误也回喂

        request = _build_llm_request(conversation, context)
        continue                                 # 显式进入下一轮

    # ---------- ⑤ 纯文本回答（最终答案） ----------
    if response.content:
        yield response.content
        break

    # ---------- ⑥ 理论到不了的兜底（防御 + 日志） ----------
    logger.error(f"无法解析的响应: {response}")
    yield "系统遇到异常，请重试"
    break

# ---------- ⑦ 循环外：撞上限兜底 ----------
if tool_iterations >= max_tool_iterations:
    logger.warning(f"达到工具迭代上限: {tool_iterations}")
    yield "任务太复杂没做完，请简化问题或重试"
```

### 三条核心心法

1. **错误也是给 LLM 的反馈**——工具失败不是终点，回喂让 LLM 修正参数重试
2. **空响应先重试一次**——往往是临时抖动，别直接放弃
3. **循环外也要兜底**——否则 LLM 陷入工具死循环，用户看到的是"没答案也没报错"

---

## 小结（这一步的收获）

| 学到的 | 一句话 |
|--------|--------|
| while 循环 | Agent 的引擎，让 LLM 自主决定下一步 |
| is_tool_call() | 循环开关：有 tool_calls = 还要调工具 |
| tool_calls 存会话 | OpenAI API 硬性要求 |
| 工具结果 role="tool" 回喂 | LLM 靠这个"看到"结果 |
| break | LLM 答完了就退出 |
| max_tool_iterations | 防死循环的安全网 |

**核心心法**：Agent 循环 = 问 LLM → 判断 → 动手 → 回喂 → 再问 → 直到 LLM 说"完了"。
这是从"脚本"到"Agent"的分水岭。
