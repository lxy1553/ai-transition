# QueryForge 阶段 E：前端（产品界面）

> **这是产品的"脸"**——零构建单页应用，会话 + 聊天 + 多轮。
> 对比你 ai_assistant：你的没界面，QueryForge 有完整前端（登录/会话/聊天）。
>
> **代码位置**：`static/`（index.html + app.js + style.css，零构建原生前端）

---

## 三问

- **Q1 解决什么问题**：让用户能网页上用——登录、建会话、聊天、多轮
- **Q2 数据流哪一环**：最外层——前端 → API（auth/sessions/chat）→ 后端
- **Q3 删掉会怎样**：只能 API 调，无产品界面

---

## 一、前端结构（static/）

```
static/
├── index.html   # 页面结构（聊天框 + 消息列表）
├── app.js       # 逻辑（登录/会话/发送聊天）
└── style.css    # 样式
```

**大白话**：零构建原生前端（无 React/Vue），直接 `uvicorn` 挂到 `/ui`。

---

## 二、页面结构（index.html）

```html
<main class="chat">
  <div id="chat-title">选择或新建一个会话开始</div>
  <div id="messages" class="messages"></div>    <!-- 消息列表 -->
  <form id="chat-form" class="chat-form">
    <input id="chat-input" placeholder="用自然语言提问，例如：我们有多少歌手？" disabled />
    <button id="chat-send" disabled>发送</button>
  </form>
</main>
```

**大白话**：页面 = 标题 + 消息列表 + 输入框。选中会话才启用输入框。

---

## 三、前端逻辑（app.js）

### 发送聊天

```javascript
async function sendChat(e) {
  const question = $("chat-input").value;
  // 调 /sessions/{id}/chat（带历史，多轮）
  const resp = await api(`/sessions/${currentSession.id}/chat`, {
    method: "POST", body: { question }
  });
  // 显示回答
  appendMessage("user", question);
  appendMessage("assistant", resp.answer);
}
```

**大白话**：输入问题 → 调后端 chat 接口（带会话 ID，多轮）→ 显示回答。

### 建会话 + 选库

```javascript
// 新建会话（选库）
$("chat-title").textContent = `${s.title}  ·  库：${s.db_id}`;
$("chat-input").disabled = false;   // 选中会话才启用输入
```

**大白话**：每个会话绑一个库（db_id），选中会话才能提问。

---

## 四、完整前后端流程（一图）

```
浏览器（static/）
  │  登录（JWT token）
  │  建会话（选库）
  │  聊天：POST /sessions/{id}/chat（带 token + session_id + 问题）
  ▼
FastAPI
  │  get_current_user（验证 token）
  │  读历史（chat_message 表）→ run_query（多轮）
  ▼
返回 answer → 前端显示
```

**大白话**：前端登录 → 建会话 → 聊天（带 token + 历史）→ 后端处理 → 前端显示。

---

## 五、对照 ai_assistant 的改造动作

```python
# ① 后端加 /ui（挂静态页面）
from fastapi.staticfiles import StaticFiles
app.mount("/ui", StaticFiles(directory="static"), name="ui")

# ② 前端最小页面（发送问题 → 显示回答）
# index.html：输入框 + 按钮 + 消息区
# app.js：fetch('/query', {question}) → 显示 answer

# ③ 可选：加会话（前端存 session_id）
```

**改造要点**：加静态页面 + 一个 fetch 聊天——你的 ai_assistant 就能网页用了。

---

## 六、小结

| 学到 | 一句话 |
|------|--------|
| 零构建前端 | 原生 HTML/JS，无需框架 |
| 会话 | 绑库 + 多轮 |
| 聊天 | fetch 调 API |
| 前端流程 | 登录 → 会话 → 聊天 |

> **核心心法**：产品界面 = 零构建前端 + 会话 + 聊天。你的 ai_assistant 加 static/ + 一个 fetch，就成网页产品。
