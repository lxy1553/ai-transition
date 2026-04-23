"""
工具类：数据验证器

提供常用的数据验证功能
"""


class Validator:
    """数据验证器类"""

    @staticmethod
    def validate_email(email):
        """
        验证邮箱格式

        Args:
            email: 邮箱地址

        Returns:
            bool: 是否有效
        """
        if not email or not isinstance(email, str):
            return False
        if "@" not in email or "." not in email:
            return False
        if email.startswith("@") or email.endswith("@"):
            return False
        return True

    @staticmethod
    def validate_phone(phone):
        """
        验证手机号格式（11位数字）

        Args:
            phone: 手机号

        Returns:
            bool: 是否有效
        """
        if not phone:
            return False
        phone_str = str(phone).replace(" ", "").replace("-", "")
        return len(phone_str) == 11 and phone_str.isdigit()

    @staticmethod
    def validate_not_empty(value):
        """
        验证非空

        Args:
            value: 待验证的值

        Returns:
            bool: 是否非空
        """
        if value is None:
            return False
        if isinstance(value, str):
            return len(value.strip()) > 0
        return True
