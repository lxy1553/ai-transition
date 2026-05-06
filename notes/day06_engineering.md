# Day 6 - 2026-05-07

## 今日主题

工程化基础

## 今日目标

- 掌握配置管理（环境变量、配置文件）
- 学会日志系统（logging模块）
- 理解异常处理（try-except、自定义异常）
- 创建一个带配置、日志和异常处理的FastAPI服务

## 今日任务拆解

### 任务 1：配置管理

**学习内容：**
- [ ] 环境变量（os.environ、python-dotenv）
- [ ] 配置文件（YAML、JSON）
- [ ] 配置类设计（Pydantic Settings）
- [ ] 多环境配置（dev、test、prod）

### 任务 2：日志系统

**学习内容：**
- [ ] logging模块基础
- [ ] 日志级别（DEBUG、INFO、WARNING、ERROR）
- [ ] 日志格式化
- [ ] 日志文件轮转

### 任务 3：异常处理

**学习内容：**
- [ ] try-except基础
- [ ] 自定义异常类
- [ ] 异常链和上下文
- [ ] FastAPI异常处理器

### 任务 4：实战项目

**项目：工程化的FastAPI服务**

基于Day 5的用户管理API，增加：
- [ ] 配置管理（.env文件、配置类）
- [ ] 日志系统（请求日志、错误日志）
- [ ] 异常处理（统一错误响应）
- [ ] 健康检查（数据库连接、配置状态）

## 项目结构

```
day06_engineering_service/
├── main.py              # 主入口
├── config/              # 配置模块
│   ├── settings.py      # 配置类
│   └── .env.example     # 环境变量示例
├── core/                # 核心模块
│   ├── logger.py        # 日志配置
│   └── exceptions.py    # 自定义异常
├── models/              # 数据模型
│   └── user.py          # 用户模型
├── routers/             # 路由模块
│   └── users.py         # 用户路由
├── services/            # 业务逻辑
│   └── user_service.py  # 用户服务
├── logs/                # 日志文件
│   └── app.log          # 应用日志
├── data/                # 数据存储
│   └── users.json       # 用户数据
└── README.md            # 项目说明
```

## 建议时间安排

### 上午（09:30 - 12:00）

- 09:30 - 10:30：配置管理学习
- 10:30 - 11:30：日志系统学习
- 11:30 - 12:00：整理笔记

### 下午（14:00 - 18:00）

- 14:00 - 15:00：异常处理学习
- 15:00 - 17:00：开发工程化服务
- 17:00 - 18:00：测试与优化

## 今日产出物

- [ ] 配置管理示例
- [ ] 日志系统示例
- [ ] 异常处理示例
- [ ] 工程化的FastAPI服务
- [ ] Day 6学习笔记

## 注意事项

⚠️ **今天的重点：**
- 配置和代码分离，不要硬编码
- 日志要分级，便于排查问题
- 异常要统一处理，返回友好的错误信息
- 敏感信息（密码、密钥）不要提交到Git

⚠️ **避免的坑：**
- .env文件不要提交到Git
- 日志文件要定期清理
- 异常信息不要暴露敏感数据
- 生产环境日志级别要设置为INFO或WARNING

---

*开始时间：2026-05-07 上午*

---

## 📚 今日核心知识点详解

### 1️⃣ 配置管理

**为什么需要配置管理？**

大白话：就像你的手机有"设置"一样，程序也需要设置。不同环境（开发、测试、生产）需要不同的设置，不能把设置写死在代码里。

**传统方式的问题：**

```python
# ❌ 硬编码（不好）
app_name = "用户管理API"
host = "127.0.0.1"
port = 8000
log_level = "INFO"

# 问题：
# 1. 改配置要改代码
# 2. 不同环境要维护多份代码
# 3. 敏感信息（密码）暴露在代码里
```

**使用环境变量：**

```python
import os

# 从环境变量读取
app_name = os.getenv("APP_NAME", "默认名称")
host = os.getenv("HOST", "127.0.0.1")
port = int(os.getenv("PORT", "8000"))
```

**使用.env文件：**

```bash
# .env文件
APP_NAME=用户管理API
HOST=127.0.0.1
PORT=8000
LOG_LEVEL=INFO
```

```python
from dotenv import load_dotenv
import os

# 加载.env文件
load_dotenv()

# 读取配置
app_name = os.getenv("APP_NAME")
```

**使用Pydantic Settings（推荐）：**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "用户管理API"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"  # 自动读取.env文件

# 创建配置实例
settings = Settings()

# 使用配置
print(settings.app_name)
print(settings.port)
```

**优势：**
- ✅ 类型安全（自动转换类型）
- ✅ 自动校验（错误的配置会报错）
- ✅ 默认值（配置缺失时使用默认值）
- ✅ IDE提示（自动补全）

---

### 2️⃣ 日志系统

**为什么需要日志？**

大白话：日志就像飞机的黑匣子，记录程序运行的每一步。出问题时，看日志就知道哪里出错了。

**日志级别：**

| 级别 | 用途 | 示例 |
|---|---|---|
| DEBUG | 调试信息 | 变量的值、函数调用 |
| INFO | 一般信息 | 用户登录、操作记录 |
| WARNING | 警告信息 | 用户名已存在、配置缺失 |
| ERROR | 错误信息 | 数据库连接失败、文件读取错误 |
| CRITICAL | 严重错误 | 系统崩溃、数据丢失 |

**基本用法：**

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 创建日志器
logger = logging.getLogger(__name__)

# 记录日志
logger.debug("这是调试信息")
logger.info("这是一般信息")
logger.warning("这是警告信息")
logger.error("这是错误信息")
logger.critical("这是严重错误")
```

**输出到文件：**

```python
import logging

# 配置日志输出到文件
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='app.log',
    filemode='a'  # 追加模式
)

logger = logging.getLogger(__name__)
logger.info("这条日志会写入文件")
```

**日志轮转（自动切割）：**

```python
from logging.handlers import RotatingFileHandler
import logging

# 创建日志器
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

# 创建轮转处理器
handler = RotatingFileHandler(
    filename='app.log',
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,  # 保留5个备份
    encoding='utf-8'
)

# 设置格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

# 添加处理器
logger.addHandler(handler)

# 使用
logger.info("这条日志会自动轮转")
```

**日志格式化：**

```python
# 格式化字符串
format_str = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'

# 说明：
# %(asctime)s - 时间
# %(name)s - 日志器名称
# %(levelname)s - 日志级别
# %(filename)s - 文件名
# %(lineno)d - 行号
# %(message)s - 日志消息

# 输出示例：
# 2026-05-07 10:00:00 - app - INFO - main.py:25 - 用户登录成功
```

---

### 3️⃣ 异常处理

**为什么需要异常处理？**

大白话：程序运行时可能出错（网络断了、文件不存在、数据格式错误），需要优雅地处理这些错误，而不是直接崩溃。

**基本用法：**

```python
try:
    # 可能出错的代码
    result = 10 / 0
except ZeroDivisionError:
    # 处理除零错误
    print("不能除以零")
except Exception as e:
    # 处理其他错误
    print(f"发生错误: {e}")
finally:
    # 无论是否出错都会执行
    print("清理资源")
```

**自定义异常：**

```python
class UserNotFoundException(Exception):
    """用户不存在异常"""
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(f"用户 {user_id} 不存在")

# 使用
def get_user(user_id):
    if user_id not in users:
        raise UserNotFoundException(user_id)
    return users[user_id]

# 捕获
try:
    user = get_user(999)
except UserNotFoundException as e:
    print(e.message)
```

**工程化的异常类：**

```python
class AppException(Exception):
    """应用基础异常"""
    def __init__(self, message, status_code=500, error_code=None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

class NotFoundException(AppException):
    """资源不存在"""
    def __init__(self, message):
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND"
        )

class ConflictException(AppException):
    """资源冲突"""
    def __init__(self, message):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT"
        )
```

**FastAPI异常处理：**

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# 自定义异常处理器
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "path": str(request.url.path)
        }
    )

# 使用
@app.get("/users/{user_id}")
def get_user(user_id: int):
    if user_id not in users:
        raise NotFoundException(f"用户 {user_id} 不存在")
    return users[user_id]
```

---

### 4️⃣ 请求日志中间件

**什么是中间件？**

大白话：中间件就像安检，每个请求进来都要经过它，每个响应出去也要经过它。

**FastAPI中间件：**

```python
import time
from fastapi import FastAPI, Request

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # 请求开始
    start_time = time.time()
    logger.info(f"请求开始: {request.method} {request.url.path}")
    
    # 处理请求
    response = await call_next(request)
    
    # 请求结束
    process_time = time.time() - start_time
    logger.info(
        f"请求完成: {request.method} {request.url.path} "
        f"状态码={response.status_code} 耗时={process_time:.3f}s"
    )
    
    return response
```

**日志输出：**

```
2026-05-07 10:00:00 - app - INFO - 请求开始: POST /api/v1/users
2026-05-07 10:00:00 - app - INFO - 请求完成: POST /api/v1/users 状态码=201 耗时=0.015s
```

---

### 5️⃣ 完整的工程化实践

**项目结构：**

```
project/
├── main.py              # 主入口
├── config/              # 配置模块
│   ├── settings.py      # 配置类
│   └── .env.example     # 环境变量示例
├── core/                # 核心模块
│   ├── logger.py        # 日志配置
│   └── exceptions.py    # 自定义异常
├── models/              # 数据模型
├── routers/             # 路由模块
├── services/            # 业务逻辑
├── logs/                # 日志文件
├── data/                # 数据存储
└── .gitignore           # Git忽略文件
```

**.gitignore（重要）：**

```
# 环境变量（敏感信息）
.env

# 日志文件
logs/
*.log

# 数据文件
data/
*.db

# Python
__pycache__/
*.pyc
```

**配置文件示例：**

```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 应用配置
    app_name: str = "用户管理API"
    debug: bool = False
    
    # 服务器配置
    host: str = "127.0.0.1"
    port: int = 8000
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**日志配置示例：**

```python
# core/logger.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name, log_file, log_level):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 文件处理器
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,
        backupCount=5
    )
    
    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger

logger = setup_logger("app", "logs/app.log", "INFO")
```

**异常处理示例：**

```python
# core/exceptions.py
class AppException(Exception):
    def __init__(self, message, status_code, error_code):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

class NotFoundException(AppException):
    def __init__(self, message):
        super().__init__(message, 404, "NOT_FOUND")

# main.py
@app.exception_handler(AppException)
async def handle_app_exception(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message
        }
    )
```

---

## 💡 关键概念总结

| 概念 | 大白话 | 代码示例 |
|---|---|---|
| 配置管理 | 程序的设置 | `Settings(BaseSettings)` |
| 环境变量 | 外部传入的配置 | `.env文件` |
| 日志级别 | 日志的重要程度 | `DEBUG/INFO/WARNING/ERROR` |
| 日志轮转 | 自动切割日志文件 | `RotatingFileHandler` |
| 自定义异常 | 自己定义的错误类型 | `class AppException(Exception)` |
| 异常处理器 | 统一处理错误 | `@app.exception_handler` |
| 中间件 | 请求的拦截器 | `@app.middleware("http")` |

---

## 📊 今日实战成果

### 项目：工程化的FastAPI服务

**功能实现：**
- ✅ 配置管理（Pydantic Settings + .env）
- ✅ 日志系统（logging + RotatingFileHandler）
- ✅ 异常处理（自定义异常 + 异常处理器）
- ✅ 请求日志（中间件记录所有请求）
- ✅ 统一错误响应（error_code + message + path）
- ✅ 用户CRUD操作

**测试结果：**
- ✅ 配置加载成功
- ✅ 日志记录正常（控制台 + 文件）
- ✅ 异常处理正常（404、409错误）
- ✅ 请求日志完整（开始、完成、耗时）
- ✅ 错误响应统一

**日志示例：**
```
2026-05-07 10:00:00 - app - INFO - 请求开始: POST /api/v1/users
2026-05-07 10:00:00 - app - INFO - 创建用户: username=zhangsan
2026-05-07 10:00:00 - app - INFO - 用户创建成功: user_id=1
2026-05-07 10:00:00 - app - INFO - 请求完成: 状态码=201 耗时=0.015s
```

**错误响应示例：**
```json
{
  "error_code": "NOT_FOUND",
  "message": "用户 999 不存在",
  "details": null,
  "path": "/api/v1/users/999"
}
```

---

## 🎯 今日收获

**技术能力：**
- ✅ 掌握配置管理（Pydantic Settings）
- ✅ 学会日志系统（logging + 轮转）
- ✅ 理解异常处理（自定义异常 + 处理器）
- ✅ 实现请求日志中间件
- ✅ 统一错误响应格式

**工程能力：**
- ✅ 配置和代码分离
- ✅ 敏感信息保护（.env不提交）
- ✅ 日志分级和轮转
- ✅ 异常统一处理
- ✅ 请求全链路追踪

**最佳实践：**
- ✅ 使用环境变量管理配置
- ✅ 日志记录关键操作
- ✅ 异常要有明确的错误码
- ✅ 生产环境日志级别设为INFO
- ✅ .env文件不提交到Git

---

*完成时间：2026-05-07 下午*
