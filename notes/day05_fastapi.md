bi# Day 5 - 2026-05-06

## 今日主题

FastAPI入门

## 今日目标

- 掌握FastAPI路由设计
- 学会参数校验（Pydantic）
- 理解请求和响应模型
- 创建一个最小FastAPI服务

## 大白话解释

“FastAPI入门”这一天要解决的是一个很具体的工程问题：先把基础能力、工具或项目环节讲清楚，再把它变成能运行、能检查、能复盘的产物。
学习时不要只看代码是否跑通，还要能说清楚它为什么需要、输入输出是什么、出错后怎么定位。

## 今日任务拆解

### 任务 1：FastAPI基础

**学习内容：**
- [ ] FastAPI框架介绍
- [ ] 路由定义（@app.get、@app.post）
- [ ] 路径参数和查询参数
- [ ] 请求体（Request Body）

### 任务 2：参数校验

**学习内容：**
- [ ] Pydantic模型定义
- [ ] 数据类型校验
- [ ] 必填和可选参数
- [ ] 默认值设置

### 任务 3：响应模型

**学习内容：**
- [ ] 响应模型定义
- [ ] 状态码设置
- [ ] 错误处理
- [ ] 自动生成API文档

### 任务 4：实战项目

**项目：用户管理API服务**

基于FastAPI，完成：
- [ ] 用户注册接口（POST /users）
- [ ] 用户查询接口（GET /users/{user_id}）
- [ ] 用户列表接口（GET /users）
- [ ] 用户更新接口（PUT /users/{user_id}）
- [ ] 参数校验和错误处理
- [ ] 自动生成API文档

## 项目结构

```
day05_fastapi_service/
├── main.py              # 主入口
├── models/              # 数据模型
│   └── user.py          # 用户模型
├── routers/             # 路由模块
│   └── users.py         # 用户路由
├── services/            # 业务逻辑
│   └── user_service.py  # 用户服务
├── data/                # 数据存储
│   └── users.json       # 用户数据
└── README.md            # 项目说明
```

## 建议时间安排

### 上午（09:30 - 12:00）

- 09:30 - 10:30：FastAPI基础学习
- 10:30 - 11:30：参数校验学习
- 11:30 - 12:00：整理笔记

### 下午（14:00 - 18:00）

- 14:00 - 15:00：响应模型学习
- 15:00 - 17:00：开发用户管理API
- 17:00 - 18:00：测试与优化

## 今日产出物

- [ ] FastAPI路由示例
- [ ] Pydantic模型示例
- [ ] 用户管理API服务
- [ ] API文档（自动生成）
- [ ] Day 5学习笔记

## 注意事项

⚠️ **今天的重点：**
- FastAPI的核心是类型注解和Pydantic
- 路由要清晰，遵循RESTful规范
- 参数校验要完善，防止脏数据
- 利用自动生成的API文档

⚠️ **避免的坑：**
- 路由顺序问题（具体路由要在通用路由前面）
- 异步函数的使用（async/await）
- 请求体和查询参数的区别
- CORS跨域问题

---

*开始时间：2026-05-06 上午*

---

## 📚 今日核心知识点详解

### 1️⃣ FastAPI是什么？

**大白话：** Fdi。

**为什么选FastAPI？**
- 自动生成API文档（Swagger UI）
- 自动校验参数（基于类型注解）
- 性能高（基于Starlette和Pydantic）
- 代码简洁（类型注解即文档）

**基本示例：**
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello World"}

# 运行：uvicorn main:app --reload
```

---

### 2️⃣ 路由设计

**什么是路由？** 路由就是URL和函数的映射关系。访问某个URL，就执行对应的函数。

**HTTP方法对应的操作：**

- 表格行 1
  - HTTP方法：GET
  - 操作：获取数据
  - 示例：查询用户信息
- 表格行 2
  - HTTP方法：POST
  - 操作：创建数据
  - 示例：创建新用户
- 表格行 3
  - HTTP方法：PUT
  - 操作：更新数据
  - 示例：更新用户信息
- 表格行 4
  - HTTP方法：DELETE
  - 操作：删除数据
  - 示例：删除用户

**路由定义：**

```python
from fastapi import FastAPI

app = FastAPI()

# GET请求
@app.get("/users")
def get_users():
    return {"users": []}

# POST请求
@app.post("/users")
def create_user():
    return {"message": "用户创建成功"}

# 路径参数（动态路由）
@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}

# 查询参数
@app.get("/search")
def search(keyword: str, page: int = 1):
    return {"keyword": keyword, "page": page}
```

**RESTful API设计规范：**

```
GET    /users          # 获取用户列表
POST   /users          # 创建用户
GET    /users/{id}     # 获取单个用户
PUT    /users/{id}     # 更新用户
DELETE /users/{id}     # 删除用户
```

---

### 3️⃣ Pydantic数据校验

**Pydantic是什么？** Pydantic是一个数据校验库，用类型注解来定义数据模型，自动校验数据。

**为什么需要数据校验？**
- 防止脏数据进入系统
- 自动转换数据类型
- 生成清晰的错误信息
- 自动生成API文档

**基本用法：**

```python
from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class User(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=150)
    city: Optional[str] = None

# 使用
user = User(
    username="zhangsan",
    email="zhangsan@example.com",
    age=25,
    city="北京"
)

print(user.username)  # zhangsan
print(user.model_dump())  # 转换为字典
```

**字段约束：**

```python
from pydantic import Field

class User(BaseModel):
    # 必填字段（...表示必填）
    username: str = Field(..., description="用户名")

    # 字符串长度限制
    password: str = Field(..., min_length=6, max_length=20)

    # 数字范围限制
    age: int = Field(..., ge=0, le=150)  # ge=大于等于, le=小于等于

    # 可选字段（Optional或默认值）
    city: Optional[str] = None
    phone: str = Field("", description="手机号")

    # 邮箱校验
    email: EmailStr
```

**在FastAPI中使用：**

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class UserCreate(BaseModel):
    username: str
    email: str
    age: int

@app.post("/users")
def create_user(user: UserCreate):
    # FastAPI自动校验user参数
    # 如果数据不符合要求，自动返回400错误
    return {"username": user.username, "email": user.email}
```

---

### 4️⃣ 请求参数类型

**1. 路径参数（Path Parameters）**

```python
@app.get("/users/{user_id}")
def get_user(user_id: int):
    # user_id从URL路径中获取
    # 访问：/users/123
    return {"user_id": user_id}
```

**2. 查询参数（Query Parameters）**

```python
from fastapi import Query

@app.get("/users")
def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    # skip和limit从URL查询字符串获取
    # 访问：/users?skip=0&limit=10
    return {"skip": skip, "limit": limit}
```

**3. 请求体（Request Body）**

```python
from pydantic import BaseModel

class User(BaseModel):
    username: str
    email: str

@app.post("/users")
def create_user(user: User):
    # user从请求体（JSON）中获取
    # POST /users
    # Body: {"username": "zhangsan", "email": "zhangsan@example.com"}
    return user
```

**4. 请求头（Headers）**

```python
from fastapi import Header

@app.get("/items")
def get_items(user_agent: str = Header(None)):
    # user_agent从请求头获取
    return {"User-Agent": user_agent}
```

---

### 5️⃣ 响应模型

**为什么需要响应模型？**
- 定义返回数据的结构
- 自动过滤不需要的字段
- 生成清晰的API文档
- 类型安全

**定义响应模型：**

```python
from pydantic import BaseModel

class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    created_at: str

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    # 返回的数据会自动按照UserResponse格式化
    return {
        "user_id": user_id,
        "username": "zhangsan",
        "email": "zhangsan@example.com",
        "created_at": "2026-05-06 10:00:00",
        "password": "secret"  # 这个字段不会返回给客户端
    }
```

**设置状态码：**

```python
@app.post("/users", status_code=201)  # 201 Created
def create_user(user: UserCreate):
    return {"message": "创建成功"}

@app.delete("/users/{user_id}", status_code=204)  # 204 No Content
def delete_user(user_id: int):
    return None
```

---

### 6️⃣ 错误处理

**使用HTTPException：**

```python
from fastapi import HTTPException

@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = get_user_from_db(user_id)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail=f"用户 {user_id} 不存在"
        )
    return user
```

**全局异常处理：**

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc)
        }
    )
```

---

### 7️⃣ 路由模块化

**为什么要模块化？**
- 代码组织清晰
- 便于维护
- 团队协作方便

**使用APIRouter：**

```python
# routers/users.py
from fastapi import APIRouter

router = APIRouter(
    prefix="/users",  # 路由前缀
    tags=["users"]    # 文档标签
)

@router.get("")
def get_users():
    return {"users": []}

@router.post("")
def create_user():
    return {"message": "创建成功"}
```

```python
# main.py
from fastapi import FastAPI
from routers import users

app = FastAPI()

# 注册路由
app.include_router(users.router)
```

---

### 8️⃣ 自动生成API文档

**FastAPI的杀手级特性：** 启动服务后，自动生成两种API文档：

**1. Swagger UI（交互式文档）**
- 访问：http://127.0.0.1:8000/docs
- 可以直接在浏览器测试API
- 自动显示参数、响应示例

**2. ReDoc（美观的文档）**
- 访问：http://127.0.0.1:8000/redoc
- 更适合阅读
- 自动生成，无需手写

**如何让文档更清晰？**

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    username: str = Field(..., description="用户名", example="zhangsan")
    email: str = Field(..., description="邮箱地址", example="zhangsan@example.com")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "zhangsan",
                "email": "zhangsan@example.com"
            }
        }

@app.post("/users", summary="创建用户", description="创建一个新用户")
def create_user(user: User):
    """
    创建新用户：

    - **username**: 用户名（必填）
    - **email**: 邮箱地址（必填）
    """
    return user
```

---

### 9️⃣ 完整项目结构

**专业的FastAPI项目结构：**

```
project/
├── main.py              # 主入口
├── models/              # 数据模型（Pydantic）
│   └── user.py
├── routers/             # 路由模块
│   └── users.py
├── services/            # 业务逻辑
│   └── user_service.py
├── database/            # 数据库相关
│   └── db.py
├── config/              # 配置文件
│   └── settings.py
└── tests/               # 测试文件
    └── test_users.py
```

**分层架构：**

```
请求 → 路由(Router) → 服务(Service) → 数据库(Database)
响应 ← 路由(Router) ← 服务(Service) ← 数据库(Database)
```

---

## 💡 关键概念总结

- 表格行 1
  - 概念：路由
  - 大白话：URL和函数的映射
  - 代码示例：`@app.get("/users")`
- 表格行 2
  - 概念：路径参数
  - 大白话：URL中的变量
  - 代码示例：`/users/{user_id}`
- 表格行 3
  - 概念：查询参数
  - 大白话：URL后面的参数
  - 代码示例：`/users?skip=0&limit=10`
- 表格行 4
  - 概念：请求体
  - 大白话：POST的JSON数据
  - 代码示例：`user: UserCreate`
- 表格行 5
  - 概念：Pydantic
  - 大白话：数据校验
  - 代码示例：`class User(BaseModel)`
- 表格行 6
  - 概念：响应模型
  - 大白话：返回数据格式
  - 代码示例：`response_model=UserResponse`
- 表格行 7
  - 概念：HTTPException
  - 大白话：错误处理
  - 代码示例：`raise HTTPException(404)`
- 表格行 8
  - 概念：APIRouter
  - 大白话：路由模块化
  - 代码示例：`router = APIRouter()`
- 表格行 9
  - 概念：自动文档
  - 大白话：Swagger UI
  - 代码示例：`/docs`

---

## 📊 今日实战成果

### 项目：用户管理API服务

**功能实现：**
- ✅ 用户CRUD操作（创建、查询、更新、删除）
- ✅ Pydantic数据校验（邮箱、年龄、用户名长度）
- ✅ RESTful API设计
- ✅ 路由模块化（APIRouter）
- ✅ 业务逻辑分离（Service层）
- ✅ 数据持久化（JSON文件）
- ✅ 错误处理（HTTPException）
- ✅ 自动生成API文档

**测试结果：**
- ✅ 创建用户成功
- ✅ 查询用户信息成功
- ✅ 更新用户信息成功
- ✅ 用户列表分页查询成功
- ✅ 邮箱格式校验成功
- ✅ 用户名重复校验成功

**产出文件：**
- `main.py` - 主入口
- `models/user.py` - 用户模型
- `routers/users.py` - 用户路由
- `services/user_service.py` - 用户服务
- `data/users.json` - 用户数据

---

## 🎯 今日收获

**技术能力：**
- ✅ 掌握FastAPI路由设计
- ✅ 学会Pydantic数据校验
- ✅ 理解RESTful API规范
- ✅ 实现完整的CRUD操作
- ✅ 掌握路由模块化
- ✅ 学会错误处理
- ✅ 利用自动生成的API文档

**工程能力：**
- ✅ 分层架构设计（Router → Service → Data）
- ✅ 代码模块化组织
- ✅ 数据持久化
- ✅ 参数校验和错误处理
- ✅ API文档自动生成

**关键代码模板：**

```python
# 1. 定义数据模型
from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3)
    email: str

# 2. 定义路由
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate):
    try:
        result = service.create_user(user)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 3. 注册路由
app = FastAPI()
app.include_router(router)
```

---

*完成时间：2026-05-06 下午*

---

## 生产实际

FastAPI 在生产 AI 应用里通常承担服务化入口，把本地脚本封装成 HTTP 能力。
在金融信贷场景里，可以把 SQL 解释、授信政策问答、风控规则检索、 NL2SQL 生成封装成接口，给内部运营、数据分析、风控和研发工具调用。

上线时要关注请求体验证、统一响应格式、异常处理、日志、鉴权和接口文档。FastAPI 自动文档很好用，但不能替代权限控制和生产级审计。

---

## 常见坑

- 表格行 1
  - 类型：目标
  - 可能的问题：只完成 Demo，不知道对应真实项目环节
  - 生产处理方式：把“FastAPI入门”映射到 RAG、NL2SQL、SQL 解释助手或服务化链路
- 表格行 2
  - 类型：数据
  - 可能的问题：输入样例过干净，真实数据有缺失、重复、格式不统一
  - 生产处理方式：增加校验、异常分支和边界样例
- 表格行 3
  - 类型：工程
  - 可能的问题：代码能跑但缺少日志、配置、错误提示和复盘材料
  - 生产处理方式：保留 README、输出文件、运行命令和关键结果
- 表格行 4
  - 类型：安全
  - 可能的问题：忽略密钥、权限、敏感字段或外部调用风险
  - 生产处理方式：使用环境变量、权限控制、脱敏和审计记录
- 表格行 5
  - 类型：维护
  - 可能的问题：只写临时代码，后续无法扩展或讲清楚
  - 生产处理方式：按模块拆分，并补充大白话注释说明设计原因

## 工程取舍

这一天优先采用最小可运行方案，是为了先建立稳定基线。真实项目里不能一开始就追求复杂架构，应该先把输入、处理逻辑、输出和失败场景跑通，再逐步增加模型调用、 检索、
数据库、权限和评测。

对“运行：uvicorn main:app --reload”这类能力，学习阶段更看重可解释和可复盘；
生产阶段再根据准确率、延迟、成本、安全和维护成本决定是否引入更复杂的方案。

## 本地练习

本地练习产物优先放在：

```text
projects/day05_fastapi_service/
```

运行或检查时，先从项目 README、脚本入口和输出目录开始。代码里需要保留大白话注释，说明每个核心函数为什么存在、输入输出是什么， 以及它在真实 AI
应用链路里对应哪个环节。

## 面试沉淀

Q019：FastAPI 在 AI 应用服务化里一般承担什么角色？
重要程度：5/5

### 回答

FastAPI 通常承担 AI 应用的服务入口，把本地脚本封装成可调用、可校验、可监控的 HTTP API。
它负责接收请求、做参数校验、调用后端模型或检索链路，并把结果按稳定结构返回给前端、平台或其他系统。 生产里还会结合鉴权、日志、异常处理、健康检查、
限流和接口文档。
对于 RAG、SQL 解释助手和数据问答项目，FastAPI 是从 Demo 走向可集成系统的重要一层。

---

## 术语更新

本日涉及的核心术语统一维护在 `notes/terminology_glossary.md`。
后续如果新增术语，必须补充英文 / 缩写、大白话解释和金融信贷业务例子， 避免只记录一个名词但不知道它在真实项目里怎么用。

---

## 每日核心问题自测

> 回答通过校验后，才把当天学习状态标记为完成。
> 用户回答通过校验前，不提前写参考答案；通过后在对应问题后追加参考答案。

### A. 今日核心问题

### 1. FastAPI 在 AI 应用服务化里一般承担什么角色？
  重要程度：5/5
我的回答：

### 2. Pydantic 请求模型为什么比手写字典解析更稳定？
  重要程度：5/5
我的回答：

### 3. 路由层、模型层和服务层为什么要分开？
  重要程度：5/5
我的回答：

### 4. API 里为什么要把业务异常转换成稳定的 HTTP 响应？
  重要程度：5/5
我的回答：

### 5. `/health`、用户接口和后续 RAG API 之间有什么共同设计思路？
  重要程度：5/5
我的回答：

### B. 前两天核心回顾

### 6. [Day 3] 数据处理流程为什么要包含加载、清洗、分析和存储几个阶段？
  重要程度：4/5
我的回答：

### 7. [Day 3] 数据处理能力和后续 RAG/NL2SQL 项目有什么关系？
  重要程度：4/5
我的回答：

### 8. [Day 4] HTTP API 在 AI 应用系统里通常承担什么角色？
  重要程度：4/5
我的回答：

### 9. [Day 4] 调用外部 API 时为什么要处理鉴权、超时和重试？
  重要程度：4/5
我的回答：
