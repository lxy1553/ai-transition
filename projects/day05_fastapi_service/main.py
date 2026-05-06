"""
Day 5 - FastAPI入门
主函数：用户管理API服务

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

# 创建FastAPI应用
app = FastAPI(
    title="用户管理API",
    description="基于FastAPI的用户管理系统",
    version="1.0.0"
)


# 根路径
@app.get("/", summary="根路径")
def root():
    """
    API根路径，返回欢迎信息
    """
    return {
        "message": "欢迎使用用户管理API",
        "version": "1.0.0",
        "docs": "/docs",
        "day": 5,
        "topic": "FastAPI入门"
    }


# 健康检查
@app.get("/health", summary="健康检查")
def health_check():
    """
    健康检查接口
    """
    return {
        "status": "ok",
        "service": "user-management-api"
    }


# 注册路由
app.include_router(users.router)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    全局异常处理器
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
