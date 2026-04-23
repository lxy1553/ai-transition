
"""
工具类：数据清洗器

提供常用的数据清洗功能
"""


class DataCleaner:
    """数据清洗器类"""

    @staticmethod
    def clean_text(text, remove_spaces=True, to_lower=False):
        """
        清洗文本数据

        Args:
            text: 原始文本
            remove_spaces: 是否移除多余空格
            to_lower: 是否转小写

        Returns:
            str: 清洗后的文本
        """
        if text is None:
            return ""
        text = str(text).strip()
        if remove_spaces:
            text = " ".join(text.split())
        if to_lower:
            text = text.lower()
        return text

    @staticmethod
    def parse_salary(salary_str):
        """
        解析薪资字符串

        Args:
            salary_str: 薪资字符串，如 "20-35K"

        Returns:
            tuple: (最小值, 最大值)
        """
        if not salary_str:
            return (0, 0)
        try:
            salary_str = salary_str.upper().replace("K", "")
            if "-" in salary_str:
                parts = salary_str.split("-")
                return (int(parts[0]), int(parts[1]))
            else:
                salary = int(salary_str)
                return (salary, salary)
        except:
            return (0, 0)

    @staticmethod
    def remove_duplicates(items):
        """
        移除列表中的重复项，保持顺序

        Args:
            items: 原始列表

        Returns:
            list: 去重后的列表
        """
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
