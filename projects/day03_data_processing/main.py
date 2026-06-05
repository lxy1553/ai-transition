"""Day 3 - 数据处理基础主入口：招聘数据分析器。

这个脚本模拟一条最小数据处理链路：读取原始 CSV、清洗字段、做统计分析、落到 SQLite。
它的用途不是只练 pandas 语法，而是建立“原始数据 -> 清洗数据 -> 分析结果 -> 可查询存储”的思路。
后续做 Boss 岗位统计、RAG 知识入库、NL2SQL 示例库，都会复用这条链路。

项目结构：
├── main.py              # 主函数入口
├── utils/               # 工具类模块
│   ├── data_loader.py   # 数据加载器
│   ├── data_cleaner.py  # 数据清洗器
│   ├── data_analyzer.py # 数据分析器
│   └── db_manager.py    # 数据库管理器
├── data/                # 原始数据
│   └── jobs.csv         # JD数据
├── output/              # 产出报告
│   ├── analysis_report.txt
│   └── jobs.db          # SQLite数据库
└── README.md            # 项目说明
"""

from pathlib import Path
from utils import DataLoader, DataCleaner, DataAnalyzer, DatabaseManager

PROJECT_DIR = Path(__file__).resolve().parent


def main():
    """按数据处理的真实顺序运行完整流程。

    主函数只负责串联步骤，具体读取、清洗、分析、入库分别交给工具类。
    这样后续某一步要替换实现时，不会把整个流程都改乱。
    """
    print("=" * 70)
    print("Day 3 - 数据处理基础：招聘数据分析器")
    print("=" * 70)

    # 第一步先加载原始数据。只有把原始数据读成 DataFrame，后面才能统一清洗和分析。
    print("\n" + "=" * 70)
    print("步骤 1：加载数据")
    print("=" * 70)
    data_file = PROJECT_DIR / "data" / "jobs.csv"
    df = DataLoader.load_csv(data_file)

    if df is None:
        print("❌ 数据加载失败，程序退出")
        return

    # 先看行数、列名、类型和缺失值，避免在不了解数据质量的情况下直接统计。
    DataLoader.show_info(df)

    # 看前几行是为了确认字段含义和样例格式，尤其是薪资、技能这类需要解析的文本字段。
    print("\n前5行数据预览:")
    print(df.head())

    # 第二步做清洗，把展示给人的薪资、技能文本整理成机器更容易统计的结构化字段。
    print("\n" + "=" * 70)
    print("步骤 2：数据清洗")
    print("=" * 70)
    df_clean = DataCleaner.clean_dataframe(df)

    # 显示清洗后的数据
    print("\n清洗后的数据预览:")
    print(df_clean[['position', 'city', 'salary_min', 'salary_max', 'salary_avg']].head())

    # 第三步做分析，重点看薪资、城市、岗位方向和技能频率，这些直接服务后续求职判断。
    print("\n" + "=" * 70)
    print("步骤 3：数据分析")
    print("=" * 70)
    analyzer = DataAnalyzer(df_clean)
    report_file = PROJECT_DIR / "output" / "analysis_report.txt"
    report_file.parent.mkdir(exist_ok=True)
    analyzer.run_analysis(output_file=report_file)

    # 第四步保存到数据库。这样分析结果不是只停留在内存里，后续可以继续用 SQL 查询和复盘。
    print("\n" + "=" * 70)
    print("步骤 4：保存到数据库")
    print("=" * 70)
    db_file = PROJECT_DIR / "output" / "jobs.db"

    with DatabaseManager(db_file) as db:
        # 原始表用于追溯来源，清洗错了还能回到最初数据重新处理。
        db.save_dataframe(df, 'jobs_raw')

        # 清洗表用于后续查询和统计，避免每次分析都重复解析薪资和技能字段。
        db.save_dataframe(df_clean, 'jobs_clean')

        # 查询示例说明：数据入库后就能用 SQL 继续分析，这也是 NL2SQL 项目的基础。
        print("\n查询示例：北京地区的岗位")
        sql = "SELECT position, city, salary FROM jobs_raw WHERE city='北京'"
        result = db.query(sql)
        if result is not None:
            print(result)

        # 显示所有表
        print("\n数据库中的表:")
        tables = db.get_tables()
        for table in tables:
            print(f"  - {table}")

    # 5. 完成
    print("\n" + "=" * 70)
    print("✅ 所有步骤完成！")
    print("=" * 70)

    print("\n📦 产出文件：")
    print(f"  - {report_file}  # 分析报告")
    print(f"  - {db_file}      # SQLite数据库")

    print("\n💡 今日学习要点：")
    print("  1. pandas基础：DataFrame操作")
    print("  2. 数据清洗：处理缺失值、提取信息")
    print("  3. 数据分析：统计、分组、聚合")
    print("  4. SQLite：数据库连接、查询、存储")
    print("  5. 完整数据处理流程：加载→清洗→分析→存储")


if __name__ == "__main__":
    main()
