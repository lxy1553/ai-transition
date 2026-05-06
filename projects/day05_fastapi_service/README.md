# Day 5 - FastAPI入门

## 项目说明

这是一个完整的FastAPI用户管理系统，展示路由设计、参数校验和RESTful API开发。

## 项目结构

```
day05_fastapi_service/
├── main.py              # 主入口
├── models/              # 数据模型
│   └── user.py          # 用户模型（Pydantic）
├── routers/             # 路由模块
│   └── users.py         # 用户路由
├── services/            # 业务逻辑
│   └── user_service.py  # 用户服务
├── data/                # 数据存储
│   └── users.json       # 用户数据
└── README.md            # 本文件
```

## 功能模块

### 1. 数据模型 (Pydantic)

- **UserCreate**: 用户创建模型（带校验）
- **UserUpdate**: 用户更新模型
- **UserResponse**: 用户响应模型

### 2. 路由设计 (RESTful)

- `POST /users` - 创建用户
- `GET /users/{user_id}` - 获取用户信息
- `GET /users` - 获取用户列表（分页）
- `PUT /users/{user_id}` - 更新用户信息
- `DELETE /users/{user_id}` - 删除用户

### 3. 业务逻辑

- 用户CRUD操作
- 数据持久化（JSON文件）
- 用户名唯一性校验
- 分页查询

## 运行方式

```bash
# 安装依赖
pip3 install fastapi uvicorn pydantic[email]

# 运行服务
python3 main.py

# 或者使用uvicorn命令
uvicorn main:app --reload
```

## API文档

启动服务后，访问：

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## API示例

### 1. 创建用户

```bash
curl -X POST "http://127.0.0.1:8000/users" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "zhangsan",
    "email": "zhangsan@example.com",
    "age": 25,
    "city": "北京"
  }'
```

### 2. 获取用户信息

```bash
curl "http://127.0.0.1:8000/users/1"
```

### 3. 获取用户列表

```bash
curl "http://127.0.0.1:8000/users?skip=0&limit=10"
```

### 4. 更新用户信息

```bash
curl -X PUT "http://127.0.0.1:8000/users/1" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newemail@example.com",
    "age": 26,
    "city": "上海"
  }'
```

### 5. 删除用户

```bash
curl -X DELETE "http://127.0.0.1:8000/users/1"
```

## 学习要点

### 1. FastAPI基础

- 路由定义（@app.get、@app.post等）
- 路径参数（/{user_id}）
- 查询参数（?skip=0&limit=10）
- 请求体（Request Body）

### 2. Pydantic模型

- 数据类型校验
- 字段约束（min_length、max_length、ge、le）
- 必填和可选参数
- 示例数据（json_schema_extra）

### 3. 路由组织

- APIRouter（路由器）
- 路由前缀（prefix）
- 路由标签（tags）
- 路由模块化

### 4. 响应处理

- 响应模型（response_model）
- 状态码（status_code）
- 异常处理（HTTPException）
- 全局异常处理器

### 5. 自动文档

- Swagger UI（交互式文档）
- ReDoc（美观的文档）
- 自动生成API文档
- 示例数据展示

## 参数校验示例

```python
from pydantic import BaseModel, Field, EmailStr

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=150)
    city: Optional[str] = Field(None, max_length=50)
```

## RESTful设计规范

| 方法 | 路径 | 说明 | 状态码 |
|---|---|---|---|
| POST | /users | 创建用户 | 201 |
| GET | /users/{id} | 获取用户 | 200 |
| GET | /users | 获取列表 | 200 |
| PUT | /users/{id} | 更新用户 | 200 |
| DELETE | /users/{id} | 删除用户 | 204 |

## 依赖库

- `fastapi`: Web框架
- `uvicorn`: ASGI服务器
- `pydantic`: 数据校验
- `pydantic[email]`: 邮箱校验

## 注意事项

- 路由顺序：具体路由要在通用路由前面
- 参数校验：使用Pydantic自动校验
- 错误处理：使用HTTPException返回错误
- 文档生成：自动生成，无需手写
