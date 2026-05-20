"""工具类：数据清洗器。

这个模块的用途是把“不规整的原始输入”变成后续代码更容易处理的格式。
真实项目里很多问题不是算法不会，而是输入数据有空格、大小写、格式混乱。
先把清洗逻辑单独放在这里，后续主流程就不用到处重复写同样的处理。
"""


class DataCleaner:
    """集中放通用清洗方法，方便不同项目复用。"""

    @staticmethod
    def clean_text(text, remove_spaces=True, to_lower=False):
        """清洗普通文本，让同一类输入变得更统一。

        这里主要解决多余空格和大小写不一致的问题。
        在 RAG 检索、关键词匹配、缓存命中这些场景里，文本不统一会导致同一个意思被当成不同输入。

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
        """把招聘网站里的薪资字符串解析成可统计的数字。

        这个函数用于把 `20-35K`、`25K` 这类展示文本变成 `(20, 35)`。
        后续做岗位分析时，只有先结构化，才能算平均值、中位数和薪资区间。

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
        """移除重复项，同时保留原来的顺序。

        真实数据里经常有重复记录。这里保留顺序，是为了不打乱原始数据的优先级或展示顺序。

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
