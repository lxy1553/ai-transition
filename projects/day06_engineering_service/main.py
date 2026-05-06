"""
Day 6 - 工程化基础
主函数：工程化的FastAPI服务

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

# 配置日志
setup_logger(
    name="app",
    log_file=settings.log_file,
    log_level=settings.log_level,
    max_bytes=settings.log_max_bytes,
    backup_count=settings.log_backup_count
)

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    description="工程化的用户管理系统",
    version=settings.app_version,
    debug=settings.debug
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求"""
    start_time = time.time()

    # 记录请求
    logger.info(f"请求开始: {request.method} {request.url.path}")

    # 处理请求
    response = await call_next(request)

    # 记录响应
    process_time = time.time() - start_time
    logger.info(
        f"请求完成: {request.method} {request.url.path} "
        f"状态码={response.status_code} 耗时={process_time:.3f}s"
    )

    return response


# 根路径
@app.get("/", summary="根路径")
def root():
    """
    API根路径，返回欢迎信息
    """
    logger.info("访问根路径")
    return {
        "message": f"欢迎使用{settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "day": 6,
        "topic": "工程化基础"
    }


# 健康检查
@app.get("/health", summary="健康检查")
def health_check():
    """
    健康检查接口
    """
    logger.debug("健康检查")
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug
    }


# 注册路由
app.include_router(users.router, prefix=settings.api_prefix)


# 自定义异常处理器
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """
    处理自定义应用异常
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


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    处理未捕获的异常
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
