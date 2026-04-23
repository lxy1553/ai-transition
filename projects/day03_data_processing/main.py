"""
Day 3 - 数据处理基础
主函数：招聘数据分析器

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


def main():
    """主函数"""
    print("=" * 70)
    print("Day 3 - 数据处理基础：招聘数据分析器")
    print("=" * 70)

    # 1. 加载数据
    print("\n" + "=" * 70)
    print("步骤 1：加载数据")
    print("=" * 70)
    data_file = Path("data/jobs.csv")
    df = DataLoader.load_csv(data_file)

    if df is None:
        print("❌ 数据加载失败，程序退出")
        return

    # 显示数据基本信息
    DataLoader.show_info(df)

    # 显示前几行数据
    print("\n前5行数据预览:")
    print(df.head())

    # 2. 数据清洗
    print("\n" + "=" * 70)
    print("步骤 2：数据清洗")
    print("=" * 70)
    df_clean = DataCleaner.clean_dataframe(df)

    # 显示清洗后的数据
    print("\n清洗后的数据预览:")
    print(df_clean[['position', 'city', 'salary_min', 'salary_max', 'salary_avg']].head())

    # 3. 数据分析
    print("\n" + "=" * 70)
    print("步骤 3：数据分析")
    print("=" * 70)
    analyzer = DataAnalyzer(df_clean)
    report_file = Path("output/analysis_report.txt")
    report_file.parent.mkdir(exist_ok=True)
    analyzer.run_analysis(output_file=report_file)

    # 4. 保存到数据库
    print("\n" + "=" * 70)
    print("步骤 4：保存到数据库")
    print("=" * 70)
    db_file = Path("output/jobs.db")

    with DatabaseManager(db_file) as db:
        # 保存原始数据
        db.save_dataframe(df, 'jobs_raw')

        # 保存清洗后的数据
        db.save_dataframe(df_clean, 'jobs_clean')

        # 查询示例
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
