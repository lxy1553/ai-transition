"""
工具类：数据清洗器

提供数据清洗和预处理功能
"""

import pandas as pd
import re


class DataCleaner:
    """数据清洗器类"""

    @staticmethod
    def clean_salary(salary_str):
        """
        清洗薪资字符串，提取最小值和最大值

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
        """
        提取技能列表

        Args:
            skills_str: 技能字符串，如 "Python,SQL,RAG"

        Returns:
            list: 技能列表
        """
        if pd.isna(skills_str):
            return []

        # 移除引号并分割
        skills_str = str(skills_str).replace('"', '').replace("'", "")
        skills = [s.strip() for s in skills_str.split(',')]
        return skills

    @staticmethod
    def clean_dataframe(df):
        """
        清洗整个数据框

        Args:
            df: 原始数据框

        Returns:
            DataFrame: 清洗后的数据框
        """
        print("🧹 开始数据清洗...")

        # 复制数据框
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
