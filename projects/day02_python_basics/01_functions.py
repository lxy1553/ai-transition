"""
Day 2 - Python函数基础练习

学习内容：
1. 函数定义与调用
2. 参数传递（位置参数、关键字参数、默认参数）
3. 返回值
4. 文档字符串
"""


# ============ 1. 基础函数定义 ============

def greet(name):
    """
    简单的问候函数

    Args:
        name: 用户名

    Returns:
        问候语字符串
    """
    return f"你好，{name}！"


# ============ 2. 带默认参数的函数 ============

def greet_with_time(name, time="早上"):
    """
    带时间的问候函数

    Args:
        name: 用户名
        time: 时间段，默认为"早上"

    Returns:
        带时间的问候语
    """
    return f"{time}好，{name}！"


# ============ 3. 数据清洗函数 ============

def clean_text(text, remove_spaces=True, to_lower=False):
    """
    清洗文本数据

    Args:
        text: 原始文本
        remove_spaces: 是否移除多余空格，默认True
        to_lower: 是否转小写，默认False

    Returns:
        清洗后的文本
    """
    if text is None:
        return ""

    # 转字符串
    text = str(text)

    # 移除首尾空格
    text = text.strip()

    # 移除多余空格
    if remove_spaces:
        text = " ".join(text.split())

    # 转小写
    if to_lower:
        text = text.lower()

    return text


# ============ 4. 数据验证函数 ============

def validate_email(email):
    """
    验证邮箱格式是否正确

    Args:
        email: 邮箱地址

    Returns:
        bool: 是否有效
    """
    if not email or not isinstance(email, str):
        return False

    # 简单验证：包含@和.
    if "@" not in email or "." not in email:
        return False

    # @不能在开头或结尾
    if email.startswith("@") or email.endswith("@"):
        return False

    return True


def validate_phone(phone):
    """
    验证手机号格式（简化版，只验证11位数字）

    Args:
        phone: 手机号

    Returns:
        bool: 是否有效
    """
    if not phone:
        return False

    # 转字符串并移除空格和横线
    phone_str = str(phone).replace(" ", "").replace("-", "")

    # 验证是否为11位数字
    if len(phone_str) == 11 and phone_str.isdigit():
        return True

    return False


# ============ 5. 数据转换函数 ============

def parse_salary(salary_str):
    """
    解析薪资字符串，提取最小值和最大值

    Args:
        salary_str: 薪资字符串，如 "20-35K"

    Returns:
        tuple: (最小值, 最大值)，单位：千元
    """
    if not salary_str:
        return (0, 0)

    try:
        # 移除K
        salary_str = salary_str.upper().replace("K", "")

        # 分割
        if "-" in salary_str:
            parts = salary_str.split("-")
            min_salary = int(parts[0])
            max_salary = int(parts[1])
            return (min_salary, max_salary)
        else:
            # 单一值
            salary = int(salary_str)
            return (salary, salary)
    except:
        return (0, 0)


# ============ 6. 列表处理函数 ============

def filter_valid_items(items, validator_func):
    """
    过滤列表中的有效项

    Args:
        items: 待过滤的列表
        validator_func: 验证函数

    Returns:
        list: 有效项列表
    """
    return [item for item in items if validator_func(item)]


# ============ 测试代码 ============

if __name__ == "__main__":
    print("=" * 50)
    print("Day 2 - Python函数基础练习")
    print("=" * 50)

    # 测试1：基础问候
    print("\n1. 基础问候函数：")
    print(greet("小明"))
    print(greet_with_time("小红"))
    print(greet_with_time("小刚", "晚上"))

    # 测试2：文本清洗
    print("\n2. 文本清洗函数：")
    print(f"原始: '  Hello   World  '")
    print(f"清洗后: '{clean_text('  Hello   World  ')}'")
    print(f"转小写: '{clean_text('  Hello   World  ', to_lower=True)}'")

    # 测试3：邮箱验证
    print("\n3. 邮箱验证函数：")
    test_emails = ["test@example.com", "invalid", "@test.com", "test@"]
    for email in test_emails:
        result = "✅ 有效" if validate_email(email) else "❌ 无效"
        print(f"{email:20s} -> {result}")

    # 测试4：手机号验证
    print("\n4. 手机号验证函数：")
    test_phones = ["13812345678", "1234567", "138-1234-5678"]
    for phone in test_phones:
        result = "✅ 有效" if validate_phone(phone) else "❌ 无效"
        print(f"{phone:20s} -> {result}")

    # 测试5：薪资解析
    print("\n5. 薪资解析函数：")
    test_salaries = ["20-35K", "25K", "15-30K"]
    for salary in test_salaries:
        min_sal, max_sal = parse_salary(salary)
        print(f"{salary:10s} -> 最小: {min_sal}K, 最大: {max_sal}K")

    # 测试6：列表过滤
    print("\n6. 列表过滤函数：")
    emails = ["test@example.com", "invalid", "user@domain.com", "@wrong"]
    valid_emails = filter_valid_items(emails, validate_email)
    print(f"原始邮箱列表: {emails}")
    print(f"有效邮箱列表: {valid_emails}")

    print("\n" + "=" * 50)
    print("所有测试完成！")
    print("=" * 50)
