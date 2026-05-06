# Day 6 - 工程化基础

## 项目说明

这是一个工程化的FastAPI用户管理系统，展示配置管理、日志系统和异常处理的最佳实践。

## 项目结构

```
day06_engineering_service/
├── main.py              # 主入口
├── config/              # 配置模块
│   ├── settings.py      # 配置类（Pydantic Settings）
│   └── .env.example     # 环境变量示例
├── core/                # 核心模块
│   ├── logger.py        # 日志配置（logging + RotatingFileHandler）
│   └── exceptions.py    # 自定义异常
├── models/              # 数据模型
│   └── user.py          # 用户模型（Pydantic）
├── routers/             # 路由模块
│   └── users.py         # 用户路由
├── services/            # 业务逻辑
│   └── user_service.py  # 用户服务
├── logs/                # 日志文件
│   └── app.log          # 应用日志
├── data/                # 数据存储
│   └── users.json       # 用户数据
├── .env                 # 环境变量（不提交到Git）
├── .gitignore           # Git忽略文件
└── README.md            # 本文件
```

## 功能特性

### 1. 配置管理

- **Pydantic Settings**: 类型安全的配置管理
- **环境变量**: 支持.env文件
- **多环境支持**: dev、test、prod
- **配置验证**: 自动校验配置项

### 2. 日志系统

- **分级日志**: DEBUG、INFO、WARNING、ERROR
- **双输出**: 控制台 + 文件
- **日志轮转**: 自动切割和备份
- **请求日志**: 记录所有HTTP请求
- **格式化**: 时间、级别、文件、行号

### 3. 异常处理

- **自定义异常**: 统一的异常类
- **异常处理器**: 全局异常捕获
- **友好错误**: 统一的错误响应格式
- **日志记录**: 自动记录异常信息

## 安装依赖

```bash
pip3 install fastapi uvicorn pydantic pydantic-settings email-validator
```

## 配置环境

```bash
# 复制环境变量示例文件
cp config/.env.example .env

# 编辑.env文件，修改配置
vim .env
```

## 运行服务

```bash
python3 main.py
```

## API文档

启动服务后，访问：

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|---|---|---|
| APP_NAME | 应用名称 | 用户管理API |
| APP_VERSION | 应用版本 | 1.0.0 |
| DEBUG | 调试模式 | false |
| HOST | 服务器地址 | 127.0.0.1 |
| PORT | 服务器端口 | 8000 |
| LOG_LEVEL | 日志级别 | INFO |
| LOG_FILE | 日志文件路径 | logs/app.log |
| DATA_FILE | 数据文件路径 | data/users.json |
| API_PREFIX | API路径前缀 | /api/v1 |

### 日志级别

- **DEBUG**: 详细的调试信息
- **INFO**: 一般信息（默认）
- **WARNING**: 警告信息
- **ERROR**: 错误信息

## 异常类型

| 异常类 | HTTP状态码 | 说明 |
|---|---|---|
| NotFoundException | 404 | 资源不存在 |
| BadRequestException | 400 | 请求参数错误 |
| ConflictException | 409 | 资源冲突 |
| InternalServerException | 500 | 服务器内部错误 |

## API示例

### 1. 创建用户

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/users" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "zhangsan",
    "email": "zhangsan@example.com",
    "age": 25,
    "city": "北京"
  }'
```

### 2. 获取用户

```bash
curl "http://127.0.0.1:8000/api/v1/users/1"
```

### 3. 更新用户

```bash
curl -X PUT "http://127.0.0.1:8000/api/v1/users/1" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newemail@example.com",
    "city": "上海"
  }'
```

## 日志示例

```
2026-05-07 10:00:00 - app - INFO - main.py:95 - 启动服务: 用户管理API v1.0.0
2026-05-07 10:00:05 - app - INFO - main.py:35 - 请求开始: POST /api/v1/users
2026-05-07 10:00:05 - app - INFO - users.py:28 - API请求: 创建用户 - zhangsan
2026-05-07 10:00:05 - app - INFO - user_service.py:52 - 创建用户: username=zhangsan, email=zhangsan@example.com
2026-05-07 10:00:05 - app - INFO - user_service.py:72 - 用户创建成功: user_id=1, username=zhangsan
2026-05-07 10:00:05 - app - INFO - main.py:43 - 请求完成: POST /api/v1/users 状态码=201 耗时=0.015s
```

## 错误响应示例

```json
{
  "error_code": "NOT_FOUND",
  "message": "用户 999 不存在",
  "details": null,
  "path": "/api/v1/users/999"
}
```

## 学习要点

### 1. 配置管理

- 配置和代码分离
- 使用环境变量
- 类型安全的配置类
- 配置验证

### 2. 日志系统

- 日志分级
- 日志格式化
- 日志轮转
- 请求日志中间件

### 3. 异常处理

- 自定义异常类
- 异常处理器
- 统一错误响应
- 异常日志记录

## 最佳实践

1. **配置管理**
   - 敏感信息使用环境变量
   - .env文件不提交到Git
   - 提供.env.example作为模板

2. **日志系统**
   - 生产环境日志级别设为INFO
   - 日志文件定期清理
   - 敏感信息不记录到日志

3. **异常处理**
   - 统一的异常类
   - 友好的错误信息
   - 详细的日志记录
   - 调试模式显示详细错误

## 依赖库

- `fastapi`: Web框架
- `uvicorn`: ASGI服务器
- `pydantic`: 数据校验
- `pydantic-settings`: 配置管理
- `email-validator`: 邮箱校验
