"""工具类：JSON 解析器。

这个模块负责 JSON 字符串、Python 对象和文件之间的转换。
AI 应用里模型响应、API 返回、配置文件和日志经常都是 JSON，
所以 JSON 解析失败和字段缺失都必须显式处理。
"""

import json
from typing import Any, Optional, Dict


class JSONParser:
    """集中处理 JSON 解析、保存、读取和嵌套取值。"""

    @staticmethod
    def parse(json_str: str) -> Optional[Any]:
        """解析 JSON 字符串。

        外部 API 和模型返回不一定永远合法。
        解析失败时返回 None，让调用方可以拒绝继续处理，避免后面字段访问报错。

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
        """把 Python 对象转换成 JSON 字符串。

        `ensure_ascii=False` 是为了中文可读。
        学习笔记、日志和接口样例里保留中文，比转义字符更容易复盘。

        Args:
            data: Python对象
            indent: 缩进空格数

        Returns:
            JSON字符串
        """
        return json.dumps(data, ensure_ascii=False, indent=indent)

    @staticmethod
    def get_value(data: Dict, path: str, default: Any = None) -> Any:
        """按点分路径从嵌套 JSON 里取值。

        真实 API 返回常常是多层结构。这个方法让主流程不用写很多层 `data["a"]["b"]`，
        字段缺失时也能返回默认值，避免程序直接崩掉。

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
        """把 JSON 数据保存到文件。

        保存请求历史或样例响应，是为了后续能复盘接口行为，
        也方便把结果作为项目产物提交到仓库。

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
        """从文件读取 JSON 数据。

        这里失败时返回 None，调用方可以决定用空列表、默认配置或直接退出。
        这样比让异常一路抛出更适合学习阶段的脚本。

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
