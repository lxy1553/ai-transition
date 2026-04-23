"""
工具类：HTTP客户端

提供HTTP请求功能
"""

import requests
from typing import Dict, Optional, Any
import time


class HTTPClient:
    """HTTP客户端类"""

    def __init__(self, base_url: str = "", timeout: int = 10):
        """
        初始化HTTP客户端

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
        """
        发送GET请求

        Args:
            url: 请求URL
            params: URL参数
            headers: 请求头
            retry: 重试次数

        Returns:
            Response对象，失败返回None
        """
        full_url = self.base_url + url if not url.startswith('http') else url

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
        """
        发送POST请求

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
        """关闭会话"""
        self.session.close()
