"""
工具类：数据加载器

提供数据读取和加载功能
"""

import pandas as pd
from pathlib import Path


class DataLoader:
    """数据加载器类"""

    @staticmethod
    def load_csv(file_path, encoding='utf-8'):
        """
        加载CSV文件

        Args:
            file_path: CSV文件路径
            encoding: 文件编码

        Returns:
            DataFrame: pandas数据框
        """
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            print(f"✅ 成功加载数据: {len(df)} 行 x {len(df.columns)} 列")
            return df
        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            return None

    @staticmethod
    def save_csv(df, file_path, encoding='utf-8', index=False):
        """
        保存为CSV文件

        Args:
            df: pandas数据框
            file_path: 保存路径
            encoding: 文件编码
            index: 是否保存索引
        """
        try:
            df.to_csv(file_path, encoding=encoding, index=index)
            print(f"✅ 数据已保存到: {file_path}")
        except Exception as e:
            print(f"❌ 保存数据失败: {e}")

    @staticmethod
    def show_info(df):
        """
        显示数据框基本信息

        Args:
            df: pandas数据框
        """
        print("\n" + "=" * 60)
        print("数据基本信息")
        print("=" * 60)
        print(f"行数: {len(df)}")
        print(f"列数: {len(df.columns)}")
        print(f"\n列名: {list(df.columns)}")
        print(f"\n数据类型:")
        print(df.dtypes)
        print(f"\n缺失值统计:")
        print(df.isnull().sum())
        print("=" * 60)
