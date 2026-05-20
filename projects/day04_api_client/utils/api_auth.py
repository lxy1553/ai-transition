"""工具类：API 认证管理。

这个模块专门生成常见认证请求头。
认证信息集中处理，能避免在业务代码里到处拼接 token、key 和密码。
真实项目里还要注意：密钥不能写死在代码里，应该来自环境变量或密钥管理系统。
"""

from typing import Dict


class APIAuth:
    """把不同认证方式封装成统一的 header 生成方法。"""

    @staticmethod
    def api_key_header(api_key: str, key_name: str = "X-API-Key") -> Dict[str, str]:
        """生成 API Key 认证头。

        API Key 常用于内部服务或第三方平台调用。
        这里允许自定义字段名，因为不同平台可能叫 `X-API-Key`、`api-key` 或其他名称。

        Args:
            api_key: API密钥
            key_name: 密钥字段名

        Returns:
            包含认证信息的请求头字典
        """
        return {key_name: api_key}

    @staticmethod
    def bearer_token_header(token: str) -> Dict[str, str]:
        """生成 Bearer Token 认证头。

        Bearer Token 常见于 OAuth、云服务和模型 API。
        生产里 token 通常有有效期，需要配合刷新和过期处理。

        Args:
            token: 访问令牌

        Returns:
            包含认证信息的请求头字典
        """
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def basic_auth_header(username: str, password: str) -> Dict[str, str]:
        """生成 Basic Auth 认证头。

        Basic Auth 会把用户名和密码做 base64 编码，但这不是加密。
        真实生产里必须配合 HTTPS 使用，也不要把密码打印到日志里。

        Args:
            username: 用户名
            password: 密码

        Returns:
            包含认证信息的请求头字典
        """
        import base64
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    @staticmethod
    def custom_header(headers: Dict[str, str]) -> Dict[str, str]:
        """直接返回自定义请求头。

        有些接口会要求特殊 header，比如租户 ID、trace ID、业务域等。
        这个方法给这些非标准字段留一个统一入口。

        Args:
            headers: 自定义请求头字典

        Returns:
            请求头字典
        """
        return headers
