"""工具类：数据清洗器。

这个模块负责把招聘 CSV 里的文本字段整理成可统计字段。
原始岗位数据通常是给人看的，比如 `20-35K`、`Python,SQL,RAG`。
清洗后才能计算薪资均值、技能词频，也方便后续写入数据库做 SQL 查询。
"""

import pandas as pd

class DataCleaner:
    """集中处理招聘数据里的字段清洗规则。"""

    @staticmethod
    def clean_salary(salary_str):
        """清洗薪资字符串，提取最小值、最大值和平均值。

        招聘网站的薪资是展示文本，不能直接参与统计。
        解析成数字后，后续才能计算平均薪资、中位数和不同岗位的薪资区间。

        Args:
            salary_str: 薪资字符串，如 "20-35K"

        Returns:
            tuple: (最小值, 最大值, 平均值)
        """
        if pd.isna(salary_str):
            return (None, None, None)

        try:
            salary_str = str(salary_str).upper().replace("K", "").strip()
            if "-" in salary_str:
                parts = salary_str.split("-")
                min_sal = int(parts[0])
                max_sal = int(parts[1])
                avg_sal = (min_sal + max_sal) / 2
                return (min_sal, max_sal, avg_sal)
            else:
                salary = int(salary_str)
                return (salary, salary, salary)
        except:
            return (None, None, None)

    @staticmethod
    def extract_skills(skills_str):
        """把技能字符串拆成技能列表。

        技能词频统计需要列表结构。先把一整段字符串拆开，
        后续才能统计 Python、SQL、RAG 等关键词出现次数。

        Args:
            skills_str: 技能字符串，如 "Python,SQL,RAG"

        Returns:
            list: 技能列表
        """
        if pd.isna(skills_str):
            return []

        # 原始 CSV 里技能可能带引号，先去掉这些展示符号，再按逗号拆分。
        skills_str = str(skills_str).replace('"', '').replace("'", "")
        skills = [s.strip() for s in skills_str.split(',')]
        return skills

    @staticmethod
    def clean_dataframe(df):
        """清洗整个招聘数据表。

        这里把单字段清洗规则集中应用到 DataFrame：
        去重保证样本不被重复统计，薪资解析保证能做数值分析，技能拆分保证能做词频统计。

        Args:
            df: 原始数据框

        Returns:
            DataFrame: 清洗后的数据框
        """
        print("🧹 开始数据清洗...")

        # 复制一份再清洗，避免破坏原始数据。真实项目里原始数据要保留，方便追溯和重跑。
        df_clean = df.copy()

        # 移除完全重复的行（在添加新列之前）
        before_count = len(df_clean)
        df_clean = df_clean.drop_duplicates()
        after_count = len(df_clean)
        if before_count > after_count:
            print(f"  移除重复行: {before_count - after_count} 条")

        # 清洗薪资
        if 'salary' in df_clean.columns:
            salary_data = df_clean['salary'].apply(DataCleaner.clean_salary)
            df_clean['salary_min'] = salary_data.apply(lambda x: x[0])
            df_clean['salary_max'] = salary_data.apply(lambda x: x[1])
            df_clean['salary_avg'] = salary_data.apply(lambda x: x[2])

        # 提取技能列表
        if 'skills' in df_clean.columns:
            df_clean['skills_list'] = df_clean['skills'].apply(DataCleaner.extract_skills)

        print("✅ 数据清洗完成")
        return df_clean
