"""
工具模块：数据验证

提供常用的数据验证函数
"""


def validate_email(email):
    """验证邮箱格式"""
    if not email or not isinstance(email, str):
        return False
    if "@" not in email or "." not in email:
        return False
    if email.startswith("@") or email.endswith("@"):
        return False
    return True


def validate_phone(phone):
    """验证手机号格式（11位数字）"""
    if not phone:
        return False
    phone_str = str(phone).replace(" ", "").replace("-", "")
    return len(phone_str) == 11 and phone_str.isdigit()


def validate_not_empty(value):
    """验证非空"""
    if value is None:
        return False
    if isinstance(value, str):
        return len(value.strip()) > 0
    return True
