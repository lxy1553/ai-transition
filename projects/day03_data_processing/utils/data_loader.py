"""工具类：数据加载器。

这个模块专门负责“把外部文件读进程序”。
数据读取单独封装后，主流程不用关心 CSV 编码、读取异常和基础信息展示。
以后如果数据来源从 CSV 换成 Excel、数据库或 API，也只需要替换这一层。
"""

import pandas as pd
from pathlib import Path


class DataLoader:
    """集中管理数据读取和基础查看方法。"""

    @staticmethod
    def load_csv(file_path, encoding='utf-8'):
        """加载 CSV 文件，并返回 pandas DataFrame。

        这里捕获异常，是为了让调用方能得到明确的失败提示。
        真实数据处理任务里，文件路径、编码、列分隔符都可能出错，不能让程序静默失败。

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
        """把处理后的 DataFrame 保存成 CSV。

        保存结果是为了让清洗或分析产物可复查。
        默认不保存索引，因为业务数据通常不需要 pandas 自动生成的行号。

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
        """展示数据的基本质量情况。

        在做任何统计前，先看行数、列名、类型和缺失值。
        这一步能提前发现字段缺失、类型不对、数据为空等问题。

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
