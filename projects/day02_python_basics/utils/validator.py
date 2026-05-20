"""工具类：数据验证器。

这个模块的用途是把明显不合法的数据提前拦住。
真实项目里，越早发现坏输入，后续清洗、入库、接口调用和模型调用就越稳定。
"""


class Validator:
    """集中放常见校验方法，让主流程不用重复写判断逻辑。"""

    @staticmethod
    def validate_email(email):
        """验证邮箱格式是否基本可用。

        这里不是完整 RFC 邮箱校验，而是学习阶段的轻量校验。
        目的是说明：业务系统要先拦截明显错误输入，再进入后续处理。

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
        """验证手机号是否能整理成 11 位数字。

        这里允许用户输入空格或短横线，因为真实输入经常不完全规整。
        先做简单归一化，再判断长度和数字格式。

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
        """验证字段是否真的有内容。

        空字符串、全空格和 None 都应该被视为无效输入。
        很多接口错误、SQL 条件缺失、RAG 空问题都可以先用这种规则拦住。

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
