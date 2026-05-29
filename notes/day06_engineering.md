# Day 6 - 2026-05-07

## 今日主题

he

## 今日目标

- 掌握配置管理（环境变量、配置文件）
- 学会日志系统（logging模块）
- 理解异常处理（try-except、自定义异常）
- 创建一个带配置、日志和异常处理的FastAPI服务

## 大白话解释

“he”这一天要解决的是一个很具体的工程问题：先把基础能力、工具或项目环节讲清楚，再把它变成能运行、能检查、能复盘的产物。
学习时不要只看代码是否跑通，还要能说清楚它为什么需要、输入输出是什么、出错后怎么定位。

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

- 表格行 1
  - 级别：DEBUG
  - 用途：调试信息
  - 示例：变量的值、函数调用
- 表格行 2
  - 级别：INFO
  - 用途：一般信息
  - 示例：用户登录、操作记录
- 表格行 3
  - 级别：WARNING
  - 用途：警告信息
  - 示例：用户名已存在、配置缺失
- 表格行 4
  - 级别：ERROR
  - 用途：错误信息
  - 示例：数据库连接失败、文件读取错误
- 表格行 5
  - 级别：CRITICAL
  - 用途：严重错误
  - 示例：系统崩溃、数据丢失

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
format_str = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d -
  %(message)s'

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

- 表格行 1
  - 概念：配置管理
  - 大白话：程序的设置
  - 代码示例：`Settings(BaseSettings)`
- 表格行 2
  - 概念：环境变量
  - 大白话：外部传入的配置
  - 代码示例：`.env文件`
- 表格行 3
  - 概念：日志级别
  - 大白话：日志的重要程度
  - 代码示例：`DEBUG/INFO/WARNING/ERROR`
- 表格行 4
  - 概念：日志轮转
  - 大白话：自动切割日志文件
  - 代码示例：`RotatingFileHandler`
- 表格行 5
  - 概念：自定义异常
  - 大白话：自己定义的错误类型
  - 代码示例：`class AppException(Exception)`
- 表格行 6
  - 概念：异常处理器
  - 大白话：统一处理错误
  - 代码示例：`@app.exception_handler`
- 表格行 7
  - 概念：中间件
  - 大白话：请求的拦截器
  - 代码示例：`@app.middleware("http")`

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

---

## 生产实际

工程化在金融信贷 AI 项目里直接关系到稳定性和审计。配置管理决定开发、测试、生产环境能否隔离；日志决定一次错误回答、越权查询或 SQL 慢查询能否回放；
异常处理决定模型、数据库或外部 API 出问题时，业务系统是否还能给出清楚反馈。

真实生产不会只问“功能能不能跑”，还会问 request_id 有没有、错误有没有分级、敏感字段有没有脱敏、配置有没有泄露。
这些能力是后续 RAG API、权限过滤和 NL2SQL 校验的底座。

---

## 常见坑

- 表格行 1
  - 类型：目标
  - 可能的问题：只完成 Demo，不知道对应真实项目环节
  - 生产处理方式：把“he”映射到 RAG、NL2SQL、SQL 解释助手或服务化链路
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

对“2026-05-07”这类能力，学习阶段更看重可解释和可复盘；生产阶段再根据准确率、延迟、成本、安全和维护成本决定是否引入更复杂的方案。

## 本地练习

本地练习产物优先放在：

```text
projects/day06_engineering_service/
```

运行或检查时，先从项目 README、脚本入口和输出目录开始。代码里需要保留大白话注释，说明每个核心函数为什么存在、输入输出是什么， 以及它在真实 AI
应用链路里对应哪个环节。

## 面试沉淀

Q020：AI API 服务为什么需要配置、日志和异常处理？

### 回答

AI API 服务的不确定性比普通接口更高，因为它依赖外部模型、检索结果、Prompt 和用户输入。
配置管理能把模型名、超时、top-k、路径和密钥从代码里拆出来，避免改代码才能调参数。
日志能记录 request_id、输入摘要、检索结果、耗时、成本和错误原因， 方便线上排查。
异常处理能把模型超时、解析失败、参数错误和无答案场景变成稳定的错误结构，而不是直接崩溃。

Q026：AI 应用上线后需要监控哪些指标？

### 回答

AI 应用上线后不能只看接口是否 200。还要监控延迟、错误率、token 成本、模型调用失败率、解析失败率、缓存命中率和用户反馈。
RAG 场景还要看召回命中率、引用准确性、无答案率、权限拦截次数和 bad case 分布。
这些指标能帮助团队判断问题来自接口、检索、模型生成、资料质量还是权限策略。

---

## 术语更新

本日涉及的核心术语统一维护在 `notes/terminology_glossary.md`。
后续如果新增术语，必须补充英文 / 缩写、大白话解释和金融信贷业务例子， 避免只记录一个名词但不知道它在真实项目里怎么用。

---

## 每日核心问题自测

> 回答通过校验后，才把当天学习状态标记为完成。
> 用户回答通过校验前，不提前写参考答案；通过后在对应问题后追加参考答案。

### A. 今日核心问题

### 1. AI API 服务为什么需要配置、日志和异常处理？
我的回答：

### 2. 为什么密钥、端口和运行环境不应该硬编码在代码里？
我的回答：

### 3. 日志里应该记录哪些信息，哪些敏感信息不能记录？
我的回答：

### 4. 统一异常处理对前端、调用方和排查有什么价值？
我的回答：

### 5. 工程化能力如何支撑后续 RAG API 的稳定性？
我的回答：

### B. 前两天核心回顾

### 6. [Day 4] HTTP API 在 AI 应用系统里通常承担什么角色？
我的回答：

### 7. [Day 4] 调用外部 API 时为什么要处理鉴权、超时和重试？
我的回答：

### 8. [Day 5] FastAPI 在 AI 应用服务化里一般承担什么角色？
我的回答：

### 9. [Day 5] Pydantic 请求模型为什么比手写字典解析更稳定？
我的回答：
