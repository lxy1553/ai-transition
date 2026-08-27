# Vanna 阶段 5：服务层 + UI（Agent 变成可部署产品）

> **目标**：理解 Agent 项目怎么从"代码"变成"可部署服务 + 可看界面"。
> 看 FastAPI 服务层（routes/app）+ ChatHandler，理解前后端怎么对接。
>
> **核心**：把 Agent 包成 API（SSE 流式 + WebSocket + 轮询），前端 `<vanna-chat>` 组件渲染。

---

## 三问

- **Q1 解决什么问题**：Agent 是 Python 代码，怎么让前端/用户访问？→ 包成 HTTP API
- **Q2 数据流哪一环**：Agent 之外的一层——前端 → API → ChatHandler → Agent.send_message → 流式返回
- **Q3 删掉会怎样**：Agent 只能在 Python 里调，无法做成网页产品

---

## 一、整体架构（Agent 怎么变产品）

```
浏览器（<vanna-chat> 组件）
  │  HTTP/SSE
  ▼
FastAPI 服务（servers/fastapi/routes.py）
  │  4 个端点：/（页面）、chat_sse（流式）、chat_websocket、chat_poll
  ▼
ChatHandler（servers/base/chat_handler.py）
  │  桥接 HTTP 和 Agent
  ▼
Agent.send_message()（核心循环）
```

**大白话**：浏览器 → FastAPI（HTTP 入口）→ ChatHandler（中转）→ Agent（核心），返回流式结果给前端。

---

## 二、FastAPI 路由（`servers/fastapi/routes.py`）逐段

### 端点 1：首页（`GET /`）

```python
@app.get("/", response_class=HTMLResponse)
async def index():
    """服务主聊天界面"""
    cdn_url = config.get("cdn_url", "https://img.vanna.ai/vanna-components.js")
    api_base_url = config.get("api_base_url", "")

    # 返回 HTML 页面（内含 <vanna-chat> 组件）
    return get_index_html(dev_mode=dev_mode, cdn_url=cdn_url, api_base_url=api_base_url)
```

**大白话**：`GET /` 返回一个网页，网页里嵌了 `<vanna-chat>` 聊天组件（从 CDN 加载）。

### 端点 2：SSE 流式聊天（`POST /api/vanna/v2/chat_sse`）★ 核心

```python
@app.post("/api/vanna/v2/chat_sse")
async def chat_sse(chat_request: ChatRequest, http_request: Request):
    """SSE 流式聊天端点"""
    # ① 把 HTTP 请求信息封装成 RequestContext（供 UserResolver 用）
    chat_request.request_context = RequestContext(
        cookies=dict(http_request.cookies),       # 用户 Cookie
        headers=dict(http_request.headers),       # 请求头（含认证）
        remote_addr=http_request.client.host if http_request.client else None,
        query_params=dict(http_request.query_params),
        metadata=chat_request.metadata,
    )

    # ② 流式生成器：边生成边 yield
    async def generate():
        try:
            # 调 ChatHandler.handle_stream → Agent 流式结果
            async for chunk in chat_handler.handle_stream(chat_request):
                chunk_json = chunk.model_dump_json()
                yield f"data: {chunk_json}\n\n"   # ★ SSE 格式：data: {...}\n\n
            yield "data: [DONE]\n\n"              # 结束标记
        except Exception as e:
            yield f"data: {json.dumps({'type':'error','message':str(e)})}\n\n"

    # ③ 返回 SSE 流（text/event-stream）
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # 关 nginx 缓冲（否则不实时）
        },
    )
```

**大白话**：
- `chat_sse` = 前端发问题，后端**流式**返回答案（打字机效果）
- `SSE 格式`：`data: {...}\n\n`（每块一个事件）
- `X-Accel-Buffering: no` = 关代理缓冲，保证实时

### 端点 3：WebSocket（`/chat_websocket`）

```python
@app.websocket("/api/vanna/v2/chat")
async def chat_websocket(websocket: WebSocket):
    """WebSocket 双向通信（可主动推送）"""
    await websocket.accept()
    while True:
        # 收前端消息
        data = await websocket.receive_json()
        # 调 ChatHandler → 结果
        async for chunk in chat_handler.handle_stream(...):
            await websocket.send_json(chunk)   # 流式推给前端
```

**大白话**：WebSocket = 双向实时（比 SSE 更强），适合需要双向通信的场景。

### 端点 4：轮询（`/chat_poll`）

```python
@app.post("/api/vanna/v2/chat")
async def chat_poll(chat_request: ChatRequest):
    """轮询（非流式）：一次请求拿全部结果"""
    response = await chat_handler.handle_poll(chat_request)
    return response
```

**大白话**：轮询 = 非流式，前端发一次请求拿完整答案（不实时但简单）。

---

## 三、ChatHandler（`servers/base/chat_handler.py`）—— HTTP 和 Agent 的桥

```python
class ChatHandler:
    """桥接 HTTP 请求和 Agent"""

    def __init__(self, agent):
        self.agent = agent

    async def handle_stream(self, chat_request):
        """流式处理：调 Agent.send_message，转成前端能读的 chunk"""
        # ① 解析请求
        user = await self.agent.user_resolver.resolve_user(chat_request.request_context)
        # ② 调 Agent（核心循环）
        async for component in self.agent.send_message(
            request_context=chat_request.request_context,
            message=chat_request.message,
            conversation_id=chat_request.conversation_id,
        ):
            # ③ 把组件转成前端格式
            yield component_to_chunk(component)

    async def handle_poll(self, chat_request):
        """轮询处理：非流式拿结果"""
        ...
```

**大白话**：ChatHandler = 中转站——接收 HTTP 请求，调 Agent 核心循环，把结果（组件）转成前端能读的格式返回。

---

## 四、前端怎么用（README 里的 `<vanna-chat>` 组件）

```html
<!-- 前端：嵌一个聊天组件就完事 -->
<script src="https://img.vanna.ai/vanna-components.js"></script>
<vanna-chat
  sse-endpoint="/api/vanna/v2/chat_sse"   <!-- 指向后端 SSE 端点 -->
  theme="dark">
</vanna-chat>
```

**大白话**：前端不用自己写聊天框，`<vanna-chat>` 组件封装好了——你只需指定后端端点，它负责发请求 + 渲染流式结果。

---

## 五、完整请求流程（前端点个按钮，后端发生了什么）

```
浏览器 <vanna-chat>
  │  用户输入"上个月逾期率" → POST /chat_sse
  ▼
FastAPI chat_sse
  │  ① 封装 RequestContext（Cookie/Header）
  │  ② 调 chat_handler.handle_stream
  ▼
ChatHandler
  │  ① resolve_user（谁在问）
  │  ② agent.send_message（核心循环）
  ▼
Agent 循环
  │  ① 构建 system_prompt
  │  ② while 循环（LLM ↔ 工具）
  │  ③ 结果组件
  ▼
ChatHandler → 组件转 chunk
  ▼
SSE 流式返回（data: {...}\n\n）
  ▼
浏览器实时显示（打字机）
```

**大白话**：前端点按钮 → 后端一路传到 Agent 循环 → 结果流式推回 → 前端实时显示。

---

## 六、对照 ai_assistant 的改造动作

你的 ai_assistant 是 Python 函数（`pipeline.ask()`）。服务化改造：

```python
# 现在：Python 函数直接调
answer = pipeline.ask("上个月逾期率", user_role="analyst")

# 改造：FastAPI 服务
from fastapi import FastAPI, Request
app = FastAPI()

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # ① 解析用户（从请求）
    user_role = resolve_role(request.headers.get("Authorization"))
    # ② 调 pipeline
    answer = pipeline.ask(request.query, user_role=user_role)
    return {"answer": answer.answer}

# 流式版（加分项）
@app.post("/api/chat_sse")
async def chat_sse(request: ChatRequest):
    async def generate():
        # pipeline 改成流式（Generator）
        async for chunk in pipeline.ask_stream(request.query):
            yield f"data: {chunk}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

**改造要点**：
1. `pipeline.ask()` → FastAPI 端点
2. 加 `ask_stream()`（流式 Generator）→ SSE 前端打字机
3. 用户角色从请求头解析
4. 前端可用简单 HTML 页面（或加 `<vanna-chat>` 组件）

---

## 七、小结

| 学到 | 一句话 |
|------|--------|
| 4 个端点 | 首页/SSE/WebSocket/轮询 |
| chat_sse | 流式聊天（打字机）核心 |
| SSE 格式 | data: {...}\n\n，关代理缓冲 |
| ChatHandler | HTTP 和 Agent 的桥 |
| 前端组件 | `<vanna-chat>` 封装好，指定端点即可 |
| 服务化改造 | pipeline.ask → FastAPI 端点 + 流式 |

> **核心心法**：Agent 变产品 = 包成 HTTP API（SSE 流式）+ 前端组件渲染。你的 ai_assistant 加 FastAPI 层，就能从"Python 函数"变"网页产品"。
