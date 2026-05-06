"""
核心模块：自定义异常

定义应用的自定义异常类
"""

from typing import Optional, Any


class AppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Any] = None
    ):
        """
        初始化异常

        Args:
            message: 错误消息
            status_code: HTTP状态码
            error_code: 错误码
            details: 详细信息
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or f"ERR_{status_code}"
        self.details = details
        super().__init__(self.message)


class NotFoundException(AppException):
    """资源不存在异常"""

    def __init__(self, message: str = "资源不存在", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details
        )


class BadRequestException(AppException):
    """请求参数错误异常"""

    def __init__(self, message: str = "请求参数错误", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="BAD_REQUEST",
            details=details
        )


class ConflictException(AppException):
    """资源冲突异常"""

    def __init__(self, message: str = "资源冲突", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details
        )


class InternalServerException(AppException):
    """服务器内部错误异常"""

    def __init__(self, message: str = "服务器内部错误", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="INTERNAL_SERVER_ERROR",
            details=details
        )
