# 主干 ④：LlmService 抽象

> **状态**：✅ 已学完
> **代码位置**：
> - 接口：`src/vanna/core/llm/base.py`（40 行）
> - 真实实现：`src/vanna/integrations/openai/llm.py`（OpenAI）
> - Mock 实现：`src/vanna/integrations/mock/llm.py`
>
> **这是 Agent 的"大脑接口"**——所有 LLM（OpenAI/Ollama/Mock）实现同一接口，Agent 只认接口，不关心底层。

---

## 三问

- **Q1 解决什么问题**：统一所有 LLM 的接口，让 Agent 不关心底层是 OpenAI 还是 Ollama
- **Q2 数据流哪一环**：Agent 循环里"发 LLM 请求"那一步：`llm_service.send_request(request)`
- **Q3 删掉会怎样**：每种 LLM 一套调用，换模型要改 Agent 代码 → 耦合，无法可插拔

---

## 一、接口：LlmService（`core/llm/base.py`，全文）

```python
class LlmService(ABC):
    """LLM 服务接口——所有 LLM 实现都要继承"""

    @abstractmethod
    async def send_request(self, request: ABC) -> LlmResponse:
        """非流式：发请求，拿完整回答"""
        pass

    @abstractmethod
    async def stream_request(
        self, request: ABC
    ) -> AsyncGenerator[LlmStreamChunk, None]:
        """流式：边生成边返回 chunk（LLM 打字机效果）"""
        raise NotImplementedError
        yield  # ★ 关键：这是 async generator，必须有 yield

    @abstractmethod
    async def validate_tools(self, tools: List[ToolSchema]) -> List[str]:
        """验证工具 schema，返回错误列表"""
        pass
```

**三个方法**：
- `send_request`：非流式（一次性拿全部）
- `stream_request`：流式（边生成边返回，前端打字机效果）
- `validate_tools`：工具校验（检查工具 schema 是否合法）

**核心**：任何 LLM（OpenAI/Ollama/DeepSeek/Mock）都实现这 3 个方法 → Agent 只认接口，换模型不用改 Agent。

---

## 二、真实实现：OpenAILlmService（`integrations/openai/llm.py`）逐段

> 看一个真实的 LLM 服务怎么实现接口。核心是 `_build_payload`（把请求打包成 OpenAI 格式）+ `send_request`（调用 API）。

### 构造（依赖注入 + 环境变量）

```python
class OpenAILlmService(LlmService):
    def __init__(self, model=None, api_key=None, organization=None, base_url=None, **kwargs):
        # ① 引入 openai 包（没有则报错提示安装）
        from openai import OpenAI
        # ② 参数从环境变量兜底
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5")
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        base_url = base_url or os.getenv("OPENAI_BASE_URL")
        # ③ 创建 OpenAI 客户端
        self._client = OpenAI(api_key=api_key, base_url=base_url, **kwargs)
```

**关键**：model/api_key 从环境变量兜底，支持注入自定义（方便测试）。

### send_request（非流式核心）

```python
async def send_request(self, request: LlmRequest) -> LlmResponse:
    """非流式请求"""
    # ① 打包成 OpenAI 格式的 payload
    payload = self._build_payload(request)

    # ② 调用 OpenAI API（stream=False = 非流式）
    resp = self._client.chat.completions.create(**payload, stream=False)

    if not resp.choices:
        return LlmResponse(content=None, tool_calls=None, finish_reason=None)

    # ③ 提取响应内容
    choice = resp.choices[0]
    content = getattr(choice.message, "content", None)          # 文字回答
    tool_calls = self._extract_tool_calls_from_message(choice.message)   # 工具调用

    # ④ 提取 token 用量
    usage = {"prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...}

    return LlmResponse(content=content, tool_calls=tool_calls, finish_reason=..., usage=usage)
```

**关键**：LLM 返回的响应 → 转成 `LlmResponse`（content + tool_calls + usage）——这正是 Agent 循环判断 `is_tool_call()` 的数据来源。

### _build_payload（★ 工具 schema 怎么注入）

```python
def _build_payload(self, request):
    messages = []
    # ① system prompt 作为第一条
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})

    # ② 会话历史（含工具结果）
    for m in request.messages:
        msg = {"role": m.role, "content": m.content}
        if m.role == "tool" and m.tool_call_id:
            msg["tool_call_id"] = m.tool_call_id   # 工具结果关联
        elif m.role == "assistant" and m.tool_calls:
            # 把 tool_calls 转成 OpenAI 格式
            msg["tool_calls"] = [{
                "id": tc.id, "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}
            } for tc in m.tool_calls]
        messages.append(msg)

    # ③ ★★ 工具 schema 注入（function calling 的本质）★★
    tools_payload = None
    if request.tools:
        tools_payload = [{
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,   # JSON Schema
            },
        } for t in request.tools]

    payload = {"model": self.model, "messages": messages}
    if tools_payload:
        payload["tools"] = tools_payload
        payload["tool_choice"] = "auto"   # ★ 让 LLM 自动决定调哪个工具
    return payload
```

**关键洞察**：**工具 schema 注入 = function calling 的本质**——把 Tool 的 name/description/parameters 转成
OpenAI 的 `tools` 参数，LLM 才知道"能调什么工具、参数怎么填"。这就是主干② Tool 抽象 → LlmService 的落地连接。

### _extract_tool_calls_from_message（LLM 返回的工具调用提取）

```python
def _extract_tool_calls_from_message(self, message):
    tool_calls = []
    raw = getattr(message, "tool_calls", None) or []
    for tc in raw:
        fn = getattr(tc, "function", None)
        if not fn: continue
        args_raw = getattr(fn, "arguments", "{}")
        # ★ LLM 返回的 args 是 JSON 字符串 → 解析成 dict
        try:
            loaded = json.loads(args_raw)
            args_dict = loaded if isinstance(loaded, dict) else {"args": loaded}
        except:
            args_dict = {"_raw": args_raw}
        tool_calls.append(ToolCall(
            id=getattr(tc, "id", "tool_call"),
            name=getattr(fn, "name", "tool"),
            arguments=args_dict,   # ★ 关键：解析后的参数 dict
        ))
    return tool_calls
```

**关键**：LLM 返回的 tool_calls（JSON 字符串）→ 解析成 `ToolCall` 对象（含 arguments dict）→ Agent 循环才能 `registry.execute(tool_call)`。

---

## 三、流式：stream_request（打字机效果）

```python
async def stream_request(self, request):
    """流式请求——边生成边 yield"""
    payload = self._build_payload(request)
    # 调用 API（stream=True）
    stream = self._client.chat.completions.create(**payload, stream=True)
    for chunk in stream:
        # 每个 chunk 是一个增量片段
        delta = chunk.choices[0].delta
        yield LlmStreamChunk(
            content=getattr(delta, "content", None),
            finish_reason=getattr(chunk.choices[0], "finish_reason", None),
        )
```

**关键**：流式 = 每次 yield 一个增量 chunk，前端实时显示（打字机）。对应 `agent.py` 里的 `_handle_streaming_response`。

---

## 四、validate_tools：工具校验

```python
async def validate_tools(self, tools):
    """验证工具 schema，返回错误列表"""
    errors = []
    for tool in tools:
        # 检查：name 非空、description 非空、parameters 是合法 JSON Schema
        if not tool.name: errors.append(f"Tool missing name: {tool}")
        if not tool.description: errors.append(f"Tool missing description: {tool.name}")
    return errors
```

**关键**：LLM 服务在调用前校验工具 schema，避免把非法工具发给 LLM。

---

## 五、Mock 实现（`integrations/mock/llm.py`）—— 测试用

```python
class MockLlmService(LlmService):
    """假 LLM——不调 API，返回预设内容（测试/开发用）"""
    def __init__(self, response_content="Hello!"):
        self.response_content = response_content

    async def send_request(self, request):
        # 模拟延迟
        await asyncio.sleep(0.1)
        return LlmResponse(
            content=f"{self.response_content} (Request #{self.call_count})",
            finish_reason="stop",
            usage={...},
        )

    async def stream_request(self, request):
        # 模拟流式：逐词 yield
        for word in self.response_content.split():
            await asyncio.sleep(0.05)
            yield LlmStreamChunk(content=word + " ", finish_reason=None)
```

**关键**：Mock 也实现同一接口 → 测试/开发时用 Mock（不花钱、不联网），生产换真实实现。

---

## 六、对照 ai_assistant 的改造动作

你的 `LLMClient` 接口（`llm_client.py`）是雏形，对比缺什么：

```python
# 你的 LLMClient（现在）
class LLMClient(ABC):
    @abstractmethod
    def chat(self, prompt) -> str: ...        # 文本
    @abstractmethod
    def chat_json(self, prompt) -> dict: ...  # JSON

# Vanna 的 LlmService（对比）
class LlmService(ABC):
    send_request(request) -> LlmResponse       # 非流式 ✅ 你有雏形
    stream_request(request)                    # 流式 ❌ 你缺
    validate_tools(tools)                      # 工具校验 ❌ 你缺
```

**改造建议**：
```python
# 你的 LLMClient 补两个方法
class LLMClient(ABC):
    async def send_request(self, request) -> LlmResponse:
        # 非流式：现有 chat/chat_json 重构
        ...
    async def stream_request(self, request):
        # ★ 新增：流式（对接 SSE 前端打字机效果）
        async for chunk in self._stream():
            yield LlmStreamChunk(content=chunk)
    async def validate_tools(self, tools):
        # ★ 新增：工具 schema 校验
        ...
```

**改造要点**：
1. `chat`/`chat_json` → 重构成 `send_request`（收 LlmRequest，返 LlmResponse）
2. 加 `stream_request`（流式）
3. 加 `validate_tools`（工具校验）
4. 换模型时只换实现类（DeepSeekLLM → OpenAILlm），Agent 代码不变

---

## 七、小结

| 学到 | 一句话 |
|------|--------|
| LlmService 接口 | 3 方法：send_request / stream_request / validate_tools |
| 工具注入 | `_build_payload` 把 Tool schema 转成 OpenAI tools 参数 |
| tool_choice="auto" | 让 LLM 自动决定调哪个工具 |
| 工具调用提取 | LLM 返回的 tool_calls JSON → ToolCall 对象 |
| 流式 | 逐 chunk yield，前端打字机 |
| Mock 实现 | 测试用，同一接口 |
| 可插拔 | 换模型只换实现类，Agent 不变 |

> **核心心法**：LlmService 是"大脑接口"——所有 LLM 实现同一接口，Agent 只认接口。
> 工具注入（_build_payload）是 function calling 的本质，连接主干② Tool 和主干① 循环。
