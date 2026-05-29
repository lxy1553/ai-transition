"""统一错误定义和 FastAPI 错误处理。

Day 37 的重点是接口响应规范。错误不能散落在业务代码里随便抛字符串，
否则前端和调用方很难判断是参数错误、未命中问题，还是服务内部故障。
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ServiceError(Exception):
    """可预期业务错误。

    `code` 给机器判断，`message` 给调用方阅读。
    生产里还会补充 trace_id、docs_url 和可重试标记。
    """

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def register_error_handlers(app: FastAPI) -> None:
    """注册统一错误响应，避免接口把 Python 异常直接暴露出去。"""

    @app.exception_handler(ServiceError)
    async def handle_service_error(_: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                },
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        # 对外隐藏底层异常细节，避免泄露文件路径、SQL、表名或环境信息。
        # 真实生产里详细异常应写入日志系统，并通过 request_id 关联。
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "internal_error",
                    "message": "服务内部错误，请根据 request_id 排查日志。",
                },
            },
        )

