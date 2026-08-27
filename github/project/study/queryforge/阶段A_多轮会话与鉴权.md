# QueryForge 阶段 A：多轮会话 + 鉴权

> **这是产品级必备**——单轮查询 → 登录 + 会话 + 多轮历史。
> 对比你 ai_assistant：你的单轮 Python 函数，QueryForge 有 JWT 登录 + 会话 + 多轮上下文。
>
> **代码位置**：`app/api/v1/auth.py` + `app/api/v1/sessions.py` + `app/core/security.py` + `app/services/auth_store.py` + `app/services/session_store.py`

---

## 三问

- **Q1 解决什么问题**：产品要"谁在用"（鉴权）+ "聊过什么"（会话/多轮）
- **Q2 数据流哪一环**：最外层——登录拿 token → 带 token 访问 → 会话里多轮问答
- **Q3 删掉会怎样**：无鉴权（谁都能用）、无多轮（每轮重新开始）

---

## 一、鉴权：JWT（security.py 逐段）

### 密码哈希（bcrypt）

```python
_MAX_BCRYPT_BYTES = 72   # bcrypt 只取前 72 字节

def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode()[:72], bcrypt.gensalt()).decode()

def verify_password(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode()[:72], hashed.encode())
```

**大白话**：密码不存明文，bcrypt 哈希（单向）。登录时比对哈希。

### JWT token

```python
def create_access_token(user_id: int, username: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),          # 主题（用户ID）
        "username": username,         # 用户名
        "iat": now,                   # 签发时间
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),   # 过期时间
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
```

**大白话**：登录成功后发一个 JWT（含用户ID + 过期时间，用密钥签名）。后续请求带 token，服务端解码校验。**token 过期 = 需重新登录**。

---

## 二、注册/登录接口（auth.py）

```python
@router.post("/register")
async def register(body):
    if await auth_store.get_user_by_username(body.username):
        raise HTTPException(409, "用户名已存在")
    user = await auth_store.create_user(body.username, hash_password(body.password))
    token = create_access_token(user["id"], user["username"])
    return TokenResponse(access_token=token, username=user["username"])

@router.post("/login")
async def login(body):
    user = await auth_store.get_user_by_username(body.username)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")
    token = create_access_token(user["id"], user["username"])
    return TokenResponse(access_token=token, username=user["username"])

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return UserInfo(id=user["id"], username=user["username"])
```

**大白话**：注册 = 存用户（密码哈希）；登录 = 验密码发 token；/me = 看当前用户。

---

## 三、get_current_user（鉴权依赖）

```python
# app/api/deps.py —— 从请求头解析用户
async def get_current_user(authorization=Header(None)):
    token = authorization.replace("Bearer ", "")   # 从 Authorization 头取 token
    payload = decode_access_token(token)           # 解码校验
    user = await auth_store.get_user(payload["sub"])
    return user   # 返回用户（供接口用）
```

**大白话**：`Depends(get_current_user)` 挂在受保护接口上——请求带有效 token 才放行，返回用户信息。

---

## 四、多轮会话（sessions.py + session_store.py）

```python
# 创建会话
@router.post("/sessions")
async def create_session(user=Depends(get_current_user)):
    return await session_store.create_session(user["id"])

# 会话里聊天（多轮）
@router.post("/sessions/{id}/chat")
async def chat(id, body, user=Depends(get_current_user)):
    # ① 读历史（从 chat_message 表）
    history = await session_store.get_messages(id)
    # ② 带历史上下文调用 run_query
    return await run_query(QueryRequest(question=body.question, history=history))
```

**大白话**：会话 = 一个聊天记录容器。聊天时读历史作为上下文传入，**这就是多轮**——"这个指标"能指代上一轮的"逾期率"。

### 关键设计（CLAUDE.md）

```python
# 多轮历史由 chat_message 表提供（DB 是历史唯一真相来源）
# 不依赖 LangGraph checkpointer
# 带历史的请求会自动跳过缓存（答案依赖上下文）
```

**大白话**：多轮上下文存在数据库（DB 唯一真相），不靠 LangGraph 的 checkpointer。带历史的请求跳过缓存（因为答案依赖上下文，缓存会错）。

---

## 五、完整流程（登录 → 会话 → 多轮问答）

```
① 注册/登录 → 拿 JWT token
② 创建会话 → 拿 session_id
③ 会话聊天（带 token + session_id）
  → 读历史（chat_message 表）
  → run_query（带 history，跳过缓存）
  → LangGraph 多轮（history 参与改写）
  → 存消息（写 chat_message）
  → 返回答案
```

---

## 六、对照 ai_assistant 的改造动作

```python
# ① 加 JWT 鉴权
from jose import jwt
def create_token(user_id): 
    return jwt.encode({"sub": user_id, "exp": now + 1h}, SECRET, "HS256")

# ② 加多轮（你的 pipeline 加 history 参数）
def ask(query, user_role, history=None):
    if history:               # 有历史 → 跳过缓存 + 用上下文改写
        query = rewrite_with_history(query, history)
    return pipeline.ask(query, user_role)

# ③ 会话存储（简单版：内存/DB 存历史）
sessions = {}
def chat(session_id, query):
    history = sessions.get(session_id, [])
    answer = ask(query, "analyst", history)
    history.append({"role": "user", "content": query})
    history.append({"role": "assistant", "content": answer})
    sessions[session_id] = history
    return answer
```

**改造要点**：加 JWT 鉴权 + 会话 + history 参数（多轮上下文）。

---

## 七、小结

| 学到 | 一句话 |
|------|--------|
| bcrypt | 密码哈希，不存明文 |
| JWT | 登录发 token，过期重登 |
| get_current_user | 鉴权依赖，保护接口 |
| 会话 | 聊天记录容器 |
| 多轮 | history 传上下文 + 跳过缓存 |

> **核心心法**：产品级 = 鉴权（JWT）+ 会话 + 多轮（history 传上下文）。你的 ai_assistant 加 JWT + 会话 + history 参数，就从单轮变产品。
