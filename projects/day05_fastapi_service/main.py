"""Day 5 - FastAPI 入门主入口：用户管理 API 服务。

这个文件把 FastAPI 应用、路由注册和全局异常处理放在一起。
用途是练习后端服务的基本骨架：入口层负责启动和挂载路由，具体业务逻辑放到 service 层。
以后 RAG、SQL 解释和 NL2SQL 服务也会沿用这种分层方式。

项目结构：
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
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

from routers import users

# 创建 FastAPI 应用。这里配置标题、描述和版本，是为了让自动生成的接口文档更容易读。
app = FastAPI(
    title="用户管理API",
    description="基于FastAPI的用户管理系统",
    version="1.0.0"
)


@app.get("/", summary="根路径")
def root():
    """API 根路径，返回服务基本信息。

    根路径适合放服务说明和文档入口，方便第一次打开接口的人知道这个服务是什么。
    """
    return {
        "message": "欢迎使用用户管理API",
        "version": "1.0.0",
        "docs": "/docs",
        "day": 5,
        "topic": "FastAPI入门"
    }


@app.get("/health", summary="健康检查")
def health_check():
    """健康检查接口。

    部署平台和监控系统通常会访问这个接口判断服务是否存活。
    业务接口出问题时，也可以先用它确认进程和端口是否正常。
    """
    return {
        "status": "ok",
        "service": "user-management-api"
    }


# 注册用户路由。入口文件只挂载路由，不直接写用户增删改查细节，便于后续扩展更多模块。
app.include_router(users.router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器。

    兜住没有被业务代码捕获的异常，避免服务直接返回一大段堆栈。
    真实生产里这里还会记录 request_id 和错误日志，并隐藏敏感内部信息。
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    print("=" * 70)
    print("Day 5 - FastAPI入门：用户管理API服务")
    print("=" * 70)
    print("\n🚀 启动服务...")
    print("\n📖 API文档地址：")
    print("   - Swagger UI: http://127.0.0.1:8000/docs")
    print("   - ReDoc: http://127.0.0.1:8000/redoc")
    print("\n💡 示例请求：")
    print("   - GET  http://127.0.0.1:8000/")
    print("   - GET  http://127.0.0.1:8000/health")
    print("   - POST http://127.0.0.1:8000/users")
    print("   - GET  http://127.0.0.1:8000/users/1")
    print("   - GET  http://127.0.0.1:8000/users?skip=0&limit=10")
    print("   - PUT  http://127.0.0.1:8000/users/1")
    print("   - DELETE http://127.0.0.1:8000/users/1")
    print("\n" + "=" * 70)
    print()

    # 启动服务
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
