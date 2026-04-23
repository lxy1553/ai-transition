"""
工具类：JSON解析器

提供JSON数据解析功能
"""

import json
from typing import Any, Optional, List, Dict


class JSONParser:
    """JSON解析器类"""

    @staticmethod
    def parse(json_str: str) -> Optional[Any]:
        """
        解析JSON字符串

        Args:
            json_str: JSON字符串

        Returns:
            解析后的Python对象，失败返回None
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            return None

    @staticmethod
    def to_string(data: Any, indent: int = 2) -> str:
        """
        将Python对象转换为JSON字符串

        Args:
            data: Python对象
            indent: 缩进空格数

        Returns:
            JSON字符串
        """
        return json.dumps(data, ensure_ascii=False, indent=indent)

    @staticmethod
    def get_value(data: Dict, path: str, default: Any = None) -> Any:
        """
        从嵌套JSON中提取值

        Args:
            data: JSON数据（字典）
            path: 路径，用点分隔，如 "weather.0.main"
            default: 默认值

        Returns:
            提取的值，失败返回默认值
        """
        try:
            keys = path.split('.')
            result = data
            for key in keys:
                if key.isdigit():
                    result = result[int(key)]
                else:
                    result = result[key]
            return result
        except (KeyError, IndexError, TypeError):
            return default

    @staticmethod
    def save_to_file(data: Any, file_path: str) -> bool:
        """
        保存JSON数据到文件

        Args:
            data: 要保存的数据
            file_path: 文件路径

        Returns:
            是否成功
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
            return False

    @staticmethod
    def load_from_file(file_path: str) -> Optional[Any]:
        """
        从文件加载JSON数据

        Args:
            file_path: 文件路径

        Returns:
            加载的数据，失败返回None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载文件失败: {e}")
            return None
