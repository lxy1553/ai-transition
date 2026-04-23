"""
工具类：数据库管理器

提供SQLite数据库操作功能
"""

import sqlite3
import pandas as pd


class DatabaseManager:
    """数据库管理器类"""

    def __init__(self, db_path):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            print(f"✅ 成功连接数据库: {self.db_path}")
        except Exception as e:
            print(f"❌ 连接数据库失败: {e}")

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print("✅ 数据库连接已关闭")

    def save_dataframe(self, df, table_name, if_exists='replace'):
        """
        保存数据框到数据库

        Args:
            df: pandas数据框
            table_name: 表名
            if_exists: 如果表存在的处理方式 ('fail', 'replace', 'append')
        """
        try:
            df.to_sql(table_name, self.conn, if_exists=if_exists, index=False)
            print(f"✅ 数据已保存到表: {table_name} ({len(df)} 行)")
        except Exception as e:
            print(f"❌ 保存数据失败: {e}")

    def query(self, sql):
        """
        执行SQL查询

        Args:
            sql: SQL查询语句

        Returns:
            DataFrame: 查询结果
        """
        try:
            df = pd.read_sql_query(sql, self.conn)
            print(f"✅ 查询成功: {len(df)} 行")
            return df
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            return None

    def get_tables(self):
        """获取所有表名"""
        sql = "SELECT name FROM sqlite_master WHERE type='table'"
        df = self.query(sql)
        if df is not None:
            return df['name'].tolist()
        return []

    def __enter__(self):
        """上下文管理器：进入"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器：退出"""
        self.close()
