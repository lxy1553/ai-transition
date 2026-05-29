"""Week 6 - NL2SQL 服务化入口。

这个 FastAPI 应用把 Day 35 的 NL2SQL 助手演示包封装成 HTTP 服务。
它覆盖第 6 周的核心目标：后端结构、接口规范、错误处理、配置管理、审计存储和测试入口。
"""

from fastapi import Depends, FastAPI

from .config import Settings, load_settings
from .errors import register_error_handlers
from .schemas import AskRequest, AskResponse, HealthResponse, TraceResponse
from .services import Nl2SqlService
from .storage import AuditStore


settings = load_settings()
audit_store = AuditStore(settings.audit_db_path)
nl2sql_service = Nl2SqlService(settings=settings, audit_store=audit_store)

app = FastAPI(
    title=settings.app_name,
    description="Week 6 NL2SQL service API",
    version=settings.version,
)
register_error_handlers(app)


def get_service() -> Nl2SqlService:
    """依赖注入服务对象。

    生产里可以在这里接权限上下文、数据库连接池或服务容器。
    测试时也可以覆盖这个依赖，避免直接访问真实资源。
    """

    return nl2sql_service


@app.get("/health", response_model=HealthResponse)
def health(service: Nl2SqlService = Depends(get_service)) -> dict:
    """健康检查接口。"""

    return service.health()


@app.get("/nl2sql/questions")
def list_questions(service: Nl2SqlService = Depends(get_service)) -> dict:
    """列出演示版当前支持的问题。"""

    return {"success": True, "questions": service.list_questions()}


@app.post("/nl2sql/ask", response_model=AskResponse)
def ask(request: AskRequest, service: Nl2SqlService = Depends(get_service)) -> dict:
    """NL2SQL 问答接口。

    成功查询和安全阻断都返回 200，因为安全阻断是预期业务结果；
    参数错误、未命中样例和内部故障才走统一错误响应。
    """

    return service.ask(
        question=request.question,
        user_id=request.user_id,
        include_trace=request.include_trace,
    )


@app.get("/nl2sql/trace/{request_id}", response_model=TraceResponse)
def get_trace(request_id: str, service: Nl2SqlService = Depends(get_service)) -> dict:
    """按 request_id 查询审计轨迹。"""

    return service.get_trace(request_id)

