"""
工具类：API认证管理

提供API认证功能
"""

from typing import Dict, Optional


class APIAuth:
    """API认证管理类"""

    @staticmethod
    def api_key_header(api_key: str, key_name: str = "X-API-Key") -> Dict[str, str]:
        """
        生成API Key认证头

        Args:
            api_key: API密钥
            key_name: 密钥字段名

        Returns:
            包含认证信息的请求头字典
        """
        return {key_name: api_key}

    @staticmethod
    def bearer_token_header(token: str) -> Dict[str, str]:
        """
        生成Bearer Token认证头

        Args:
            token: 访问令牌

        Returns:
            包含认证信息的请求头字典
        """
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def basic_auth_header(username: str, password: str) -> Dict[str, str]:
        """
        生成Basic Auth认证头

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
        """
        自定义请求头

        Args:
            headers: 自定义请求头字典

        Returns:
            请求头字典
        """
        return headers
