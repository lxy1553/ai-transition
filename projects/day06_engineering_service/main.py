"""Day 6 - 工程化基础主入口：带配置、日志和异常处理的 FastAPI 服务。

这个文件在 Day 5 用户管理 API 的基础上补齐工程化能力：
配置从代码里拆出来、请求过程写日志、业务异常统一返回稳定结构。
这些能力决定服务能不能从“本地能跑”走向“线上可排查、可维护”。

项目结构：
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
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import time

from config.settings import settings
from core.logger import setup_logger, logger
from core.exceptions import AppException
from routers import users

# 启动时先配置日志。后续请求、业务错误和未捕获异常都会进入同一套日志系统，方便排查。
setup_logger(
    name="app",
    log_file=settings.log_file,
    log_level=settings.log_level,
    max_bytes=settings.log_max_bytes,
    backup_count=settings.log_backup_count
)

# 应用基础信息来自配置对象。这样换端口、版本、日志级别时，不需要直接改业务代码。
app = FastAPI(
    title=settings.app_name,
    description="工程化的用户管理系统",
    version=settings.app_version,
    debug=settings.debug
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录每个 HTTP 请求的开始、结束、状态码和耗时。

    生产排查时，第一步通常是确认请求有没有进来、返回了什么状态码、慢在哪里。
    中间件放在所有路由外层，所以不用每个接口都手写同样的日志。
    """
    start_time = time.time()

    # 请求开始先记方法和路径，方便和后面的完成日志配对。
    logger.info(f"请求开始: {request.method} {request.url.path}")

    # call_next 会继续执行真正的路由处理逻辑。
    response = await call_next(request)

    # 记录耗时和状态码。以后排查慢接口或 5xx 错误时，这类日志最直接。
    process_time = time.time() - start_time
    logger.info(
        f"请求完成: {request.method} {request.url.path} "
        f"状态码={response.status_code} 耗时={process_time:.3f}s"
    )

    return response


@app.get("/", summary="根路径")
def root():
    """API 根路径，返回服务基本信息。

    这个接口用于快速确认服务名称、版本和文档入口。
    真实项目里也常用根路径给调用方提供最小服务说明。
    """
    logger.info("访问根路径")
    return {
        "message": f"欢迎使用{settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "day": 6,
        "topic": "工程化基础"
    }


@app.get("/health", summary="健康检查")
def health_check():
    """健康检查接口。

    监控和部署平台可以调用它判断服务是否存活。
    返回 debug 和版本信息，也方便确认当前环境配置是否符合预期。
    """
    logger.debug("健康检查")
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug
    }


# 路由统一挂在配置里的 API 前缀下，方便以后做版本管理，比如 `/api/v1`、`/api/v2`。
app.include_router(users.router, prefix=settings.api_prefix)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """处理业务层主动抛出的应用异常。

    这些异常是我们预期内的错误，比如用户不存在、用户名冲突。
    统一转换成稳定 JSON，前端和调用方才能按 `error_code` 做处理。
    """
    logger.error(
        f"应用异常: {exc.error_code} - {exc.message} "
        f"路径={request.url.path} 状态码={exc.status_code}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """处理所有未捕获异常。

    这层是最后兜底，避免内部异常直接暴露堆栈给用户。
    debug 模式下返回 details 方便本地排查，生产模式下隐藏细节更安全。
    """
    logger.exception(
        f"未捕获的异常: {type(exc).__name__} - {str(exc)} "
        f"路径={request.url.path}"
    )

    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "服务器内部错误",
            "details": str(exc) if settings.debug else None,
            "path": str(request.url.path)
        }
    )


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info(f"启动服务: {settings.app_name} v{settings.app_version}")
    logger.info("=" * 70)
    logger.info(f"配置信息:")
    logger.info(f"  - 主机: {settings.host}:{settings.port}")
    logger.info(f"  - 调试模式: {settings.debug}")
    logger.info(f"  - 日志级别: {settings.log_level}")
    logger.info(f"  - 日志文件: {settings.log_file}")
    logger.info(f"  - 数据文件: {settings.data_file}")
    logger.info(f"  - API前缀: {settings.api_prefix}")
    logger.info("=" * 70)
    logger.info(f"API文档地址:")
    logger.info(f"  - Swagger UI: http://{settings.host}:{settings.port}/docs")
    logger.info(f"  - ReDoc: http://{settings.host}:{settings.port}/redoc")
    logger.info("=" * 70)

    # 启动服务
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower()
    )
