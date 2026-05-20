"""Day 1 最小 FastAPI 服务。

这个文件的用途不是做完整业务系统，而是验证本地 Python、FastAPI 和接口访问链路已经打通。
后续所有 AI 应用、RAG 问答、NL2SQL 服务，都会先从这种最小可访问 API 形态扩展出来。
"""

from fastapi import FastAPI


# app 是整个 Web 服务的入口对象。
# FastAPI 会根据它收集路由，并自动生成接口文档，方便确认服务是否真的启动成功。
app = FastAPI(title="AI Transition Day 1 Demo")


@app.get("/health")
def health() -> dict:
    """健康检查接口，用来确认服务进程还活着。

    生产服务通常都会有 health 接口，部署平台或监控系统会定期访问它。
    如果这个接口都不通，就说明服务启动、端口、依赖或进程状态至少有一处出了问题。
    """
    return {
        "status": "ok",
        "day": 1,
        "topic": "positioning-and-environment-setup",
    }
