"""工具类：HTTP 客户端。

这个模块把 GET、POST、超时、重试和会话管理封装起来。
后续调用天气 API、LLM API、RAG API 时，业务代码不用重复写请求和异常处理。
"""

import requests
from typing import Dict, Optional
import time


class HTTPClient:
    """带超时和重试的轻量 HTTP 客户端。"""

    def __init__(self, base_url: str = "", timeout: int = 10):
        """初始化客户端。

        `Session` 可以复用连接，适合连续请求同一个服务。
        timeout 是必须有的保护，避免外部接口卡住时拖死整个程序。

        Args:
            base_url: 基础URL
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

    def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        retry: int = 3
    ) -> Optional[requests.Response]:
        """发送 GET 请求，适合查询类接口。

        这里带有限重试，是为了应对偶发网络抖动。
        但如果所有重试都失败，就返回 None，让调用方明确走失败分支。

        Args:
            url: 请求URL
            params: URL参数
            headers: 请求头
            retry: 重试次数

        Returns:
            Response对象，失败返回None
        """
        full_url = self.base_url + url if not url.startswith('http') else url

        # 对外部 API 不能假设永远成功，所以每次请求都要有超时、重试和错误提示。
        for attempt in range(retry):
            try:
                response = self.session.get(
                    full_url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                print(f"❌ 请求失败 (尝试 {attempt + 1}/{retry}): {e}")
                if attempt < retry - 1:
                    time.sleep(1)
                else:
                    return None

    def post(
        self,
        url: str,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        retry: int = 3
    ) -> Optional[requests.Response]:
        """发送 POST 请求，适合提交 JSON 或表单数据。

        LLM 调用、RAG 问答、NL2SQL 查询通常都会用 POST，
        因为请求体里要放 prompt、上下文、用户问题等结构化内容。

        Args:
            url: 请求URL
            data: 表单数据
            json: JSON数据
            headers: 请求头
            retry: 重试次数

        Returns:
            Response对象，失败返回None
        """
        full_url = self.base_url + url if not url.startswith('http') else url

        for attempt in range(retry):
            try:
                response = self.session.post(
                    full_url,
                    data=data,
                    json=json,
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                print(f"❌ 请求失败 (尝试 {attempt + 1}/{retry}): {e}")
                if attempt < retry - 1:
                    time.sleep(1)
                else:
                    return None

    def close(self):
        """关闭会话，释放底层连接资源。

        长时间运行的服务要注意释放连接，否则可能造成连接泄漏。
        """
        self.session.close()
