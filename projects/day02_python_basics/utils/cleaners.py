"""
工具模块：数据清洗

提供常用的数据清洗函数
"""


def clean_text(text, remove_spaces=True, to_lower=False):
    """清洗文本数据"""
    if text is None:
        return ""
    text = str(text).strip()
    if remove_spaces:
        text = " ".join(text.split())
    if to_lower:
        text = text.lower()
    return text


def parse_salary(salary_str):
    """解析薪资字符串，如 "20-35K" """
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


def remove_duplicates(items):
    """移除列表中的重复项，保持顺序"""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
