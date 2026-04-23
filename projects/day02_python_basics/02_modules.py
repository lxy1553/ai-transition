"""
Day 2 - Python模块与包练习

演示如何使用自定义模块
"""

# 方式1：导入整个模块
import utils.validators as validators
import utils.cleaners as cleaners

# 方式2：从模块导入特定函数
from utils import validate_email, clean_text, parse_salary

# 方式3：导入所有（不推荐，但演示用）
# from utils import *


def process_user_data(name, email, phone, salary):
    """
    处理用户数据

    Args:
        name: 姓名
        email: 邮箱
        phone: 手机号
        salary: 薪资字符串

    Returns:
        dict: 处理后的数据
    """
    # 清洗姓名
    clean_name = clean_text(name)

    # 验证邮箱
    email_valid = validate_email(email)

    # 验证手机号
    phone_valid = validators.validate_phone(phone)

    # 解析薪资
    min_sal, max_sal = parse_salary(salary)

    return {
        "name": clean_name,
        "email": email,
        "email_valid": email_valid,
        "phone": phone,
        "phone_valid": phone_valid,
        "salary_range": f"{min_sal}-{max_sal}K",
        "is_valid": email_valid and phone_valid and len(clean_name) > 0
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Day 2 - Python模块与包练习")
    print("=" * 60)

    # 测试数据
    test_users = [
        {
            "name": "  张三  ",
            "email": "zhangsan@example.com",
            "phone": "13812345678",
            "salary": "20-35K"
        },
        {
            "name": "李四",
            "email": "invalid-email",
            "phone": "123456",
            "salary": "25K"
        },
        {
            "name": "",
            "email": "wangwu@test.com",
            "phone": "13987654321",
            "salary": "18-30K"
        }
    ]

    print("\n处理用户数据：\n")
    for i, user in enumerate(test_users, 1):
        print(f"用户 {i}:")
        result = process_user_data(
            user["name"],
            user["email"],
            user["phone"],
            user["salary"]
        )

        for key, value in result.items():
            print(f"  {key:15s}: {value}")
        print()

    print("=" * 60)
    print("模块导入演示完成！")
    print("=" * 60)

    print("\n💡 学到的知识点：")
    print("1. 创建自定义模块（.py文件）")
    print("2. 创建包（包含__init__.py的目录）")
    print("3. 不同的import方式")
    print("4. 模块化代码组织")
