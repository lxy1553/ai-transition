"""
Day 2 - Python基础补齐
主函数：日志分析器

项目结构：
- main.py           # 主函数入口
- utils/            # 工具类模块
  ├── log_analyzer.py  # 日志分析器类

  ├── validator.py     # 数据验证器类
  └── cleaner.py       # 数据清洗器类
- examples/         # 示例数据
  └── app.log          # 示例日志文件
- output/           # 产出报告
  └── log_report.txt   # 生成的分析报告
"""

from pathlib import Path
from utils import LogAnalyzer, Validator, DataCleaner


def demo_validator():
    """演示数据验证器"""
    print("\n" + "=" * 70)
    print("1. 数据验证器演示")
    print("=" * 70)

    # 测试邮箱验证
    test_emails = ["test@example.com", "invalid", "@test.com"]
    print("\n邮箱验证：")
    for email in test_emails:
        result = "✅ 有效" if Validator.validate_email(email) else "❌ 无效"
        print(f"  {email:25s} -> {result}")

    # 测试手机号验证
    test_phones = ["13812345678", "1234567", "138-1234-5678"]
    print("\n手机号验证：")
    for phone in test_phones:
        result = "✅ 有效" if Validator.validate_phone(phone) else "❌ 无效"
        print(f"  {phone:25s} -> {result}")


def demo_cleaner():
    """演示数据清洗器"""
    print("\n" + "=" * 70)
    print("2. 数据清洗器演示")
    print("=" * 70)

    # 测试文本清洗
    print("\n文本清洗：")
    text = "  Hello   World  "
    print(f"  原始文本: '{text}'")
    print(f"  清洗后: '{DataCleaner.clean_text(text)}'")
    print(f"  转小写: '{DataCleaner.clean_text(text, to_lower=True)}'")

    # 测试薪资解析
    print("\n薪资解析：")
    salaries = ["20-35K", "25K", "15-30K"]
    for salary in salaries:
        min_sal, max_sal = DataCleaner.parse_salary(salary)
        print(f"  {salary:10s} -> 最小: {min_sal}K, 最大: {max_sal}K")


def demo_log_analyzer():
    """演示日志分析器"""
    print("\n" + "=" * 70)
    print("3. 日志分析器演示")
    print("=" * 70)

    # 设置路径
    log_file = Path("examples/app.log")
    output_file = Path("output/log_report.txt")

    # 确保输出目录存在
    output_file.parent.mkdir(exist_ok=True)

    # 运行日志分析
    print()
    analyzer = LogAnalyzer(log_file)
    analyzer.run(output_file=output_file)


def main():
    """主函数"""
    print("=" * 70)
    print("Day 2 - Python基础补齐：工具类实战")
    print("=" * 70)

    # 演示1：数据验证器
    demo_validator()

    # 演示2：数据清洗器
    demo_cleaner()

    # 演示3：日志分析器
    demo_log_analyzer()

    print("\n" + "=" * 70)
    print("✅ 所有演示完成！")
    print("=" * 70)

    print("\n📦 项目结构：")
    print("  - main.py           # 主函数入口")
    print("  - utils/            # 工具类模块")
    print("    ├── log_analyzer.py  # 日志分析器")
    print("    ├── validator.py     # 数据验证器")
    print("    └── cleaner.py       # 数据清洗器")
    print("  - examples/         # 示例数据")
    print("  - output/           # 产出报告")

    print("\n💡 今日学习要点：")
    print("  1. 面向对象编程：使用类封装功能")
    print("  2. 模块化设计：工具类分离，职责清晰")
    print("  3. 静态方法：@staticmethod装饰器")
    print("  4. 文件操作：读取、解析、生成报告")
    print("  5. 正则表达式：解析日志格式")
    print("  6. 数据统计：Counter计数器")


if __name__ == "__main__":
    main()
