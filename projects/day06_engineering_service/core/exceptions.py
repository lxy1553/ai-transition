"""核心模块：自定义异常。

这个模块把常见业务错误统一成应用异常。
路由和服务层只需要抛出明确异常，入口层会统一转换成稳定 HTTP 响应。
这样前端不会收到各种不一致的错误格式。
"""

from typing import Optional, Any


class AppException(Exception):
    """应用基础异常类。

    所有业务异常都继承它，统一携带 message、HTTP 状态码、业务错误码和详情。
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Any] = None
    ):
        """初始化异常对象。

        error_code 用于程序判断错误类型，message 用于给人看。
        details 可以保存额外上下文，但生产环境要注意不要放敏感信息。

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
    """资源不存在异常，用于查询不到用户、文档或记录的场景。"""

    def __init__(self, message: str = "资源不存在", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details
        )


class BadRequestException(AppException):
    """请求参数错误异常，用于业务规则不接受当前输入的场景。"""

    def __init__(self, message: str = "请求参数错误", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="BAD_REQUEST",
            details=details
        )


class ConflictException(AppException):
    """资源冲突异常，用于用户名重复、重复创建等冲突场景。"""

    def __init__(self, message: str = "资源冲突", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details
        )


class InternalServerException(AppException):
    """服务器内部错误异常，用于数据文件读写失败等服务端问题。"""

    def __init__(self, message: str = "服务器内部错误", details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="INTERNAL_SERVER_ERROR",
            details=details
        )
