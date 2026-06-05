"""工具类：数据库管理器。

这个模块把 SQLite 连接、保存和查询操作封装起来。
用途是让数据处理结果能落到数据库里，后续可以用 SQL 继续查询。
这也是后面 NL2SQL 项目的基础：自然语言问题最终也要落到安全 SQL 查询上。
"""

import sqlite3
import json
import pandas as pd


class DatabaseManager:
    """用上下文管理器管理 SQLite 连接，避免忘记关闭数据库。"""

    def __init__(self, db_path):
        """初始化数据库路径。

        这里先不立刻连接，等进入 `with DatabaseManager(...)` 时再打开连接。
        这样连接的生命周期更清楚，也更不容易资源泄露。

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """连接 SQLite 数据库。

        SQLite 适合本地学习和小型 Demo，不需要额外启动数据库服务。
        后续如果换成 MySQL 或 PostgreSQL，可以保留上层调用方式，只替换这一层实现。
        """
        try:
            self.conn = sqlite3.connect(self.db_path)
            print(f"✅ 成功连接数据库: {self.db_path}")
        except Exception as e:
            print(f"❌ 连接数据库失败: {e}")

    def close(self):
        """关闭数据库连接，释放文件句柄。

        数据库连接用完要关掉，否则可能导致文件被占用或写入没有及时落盘。
        """
        if self.conn:
            self.conn.close()
            print("✅ 数据库连接已关闭")

    def save_dataframe(self, df, table_name, if_exists='replace'):
        """把 DataFrame 保存为数据库表。

        这一步把内存里的分析数据变成可查询资产。
        默认覆盖同名表，是为了学习阶段每次重跑都得到最新结果。
        SQLite 只能直接保存字符串、数字、日期这类基础类型。
        清洗后的 `skills_list` 是列表，写库前要转成 JSON 字符串，否则会出现绑定参数失败。

        Args:
            df: pandas数据框
            table_name: 表名
            if_exists: 如果表存在的处理方式 ('fail', 'replace', 'append')
        """
        try:
            df_to_save = df.copy()
            for column in df_to_save.columns:
                df_to_save[column] = df_to_save[column].apply(
                    lambda value: json.dumps(value, ensure_ascii=False)
                    if isinstance(value, (list, dict))
                    else value
                )
            df_to_save.to_sql(table_name, self.conn, if_exists=if_exists, index=False)
            print(f"✅ 数据已保存到表: {table_name} ({len(df)} 行)")
        except Exception as e:
            print(f"❌ 保存数据失败: {e}")

    def query(self, sql):
        """执行 SQL 查询，并返回 DataFrame。

        这里用 pandas 读取查询结果，方便继续做分析或打印展示。
        如果 SQL 写错，函数返回 None，让调用方能做失败处理。

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
        """获取当前 SQLite 文件里已有的表名。

        这个方法用于确认数据是否真的写入成功，也方便后续检查数据库结构。
        """
        sql = "SELECT name FROM sqlite_master WHERE type='table'"
        df = self.query(sql)
        if df is not None:
            return df['name'].tolist()
        return []

    def __enter__(self):
        """进入 `with` 语句时打开连接。"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出 `with` 语句时关闭连接。

        即使中间查询失败，也尽量释放数据库连接，减少资源占用。
        """
        self.close()
