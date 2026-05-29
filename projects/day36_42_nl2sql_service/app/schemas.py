"""接口请求和响应模型。

Pydantic schema 是 API 契约的一部分。它让调用方明确知道能传什么字段、
会返回什么结构，也让服务在进入业务逻辑前先拦住明显非法输入。
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """NL2SQL 问答请求。"""

    question: str = Field(..., min_length=1, max_length=300, description="业务自然语言问题")
    user_id: Optional[str] = Field(None, max_length=80, description="用户标识，用于审计")
    include_trace: bool = Field(True, description="是否返回解析、生成、校验等链路信息")


class AskResponse(BaseModel):
    """NL2SQL 问答响应。

    成功和安全阻断都走同一个响应模型。
    区别体现在 `final_status`、`pipeline` 和 `risk_notes`，这样前端不需要为每类结果写不同解析逻辑。
    """

    request_id: str
    question: str
    final_status: str
    answer: str
    key_findings: list[str]
    risk_notes: list[str]
    follow_up_questions: list[str]
    pipeline: Optional[dict[str, str]]
    sql: Optional[str]


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str
    app_name: str
    env: str
    version: str
    demo_ready: bool


class TraceResponse(BaseModel):
    """审计追踪响应。"""

    request_id: str
    question: str
    user_id: Optional[str]
    final_status: str
    created_at: str
    details: dict[str, Any]

