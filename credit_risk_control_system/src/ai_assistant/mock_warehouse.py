"""
模拟数仓 —— 用 SQLite 落地一个 ADS 层的简化版

小白类比：真实生产里，数据存在 ClickHouse / Iceberg 这些大数据引擎里。
这里用 SQLite（Python 内置，零依赖）模拟一个数仓，让 SQL 能"真的执行、真的返回数据"。

为什么用 SQLite 而不是别的？
  - 零依赖：Python 自带，不用 pip install 任何东西
  - 真 SQL：支持标准 SQL，能让 NL2SQL 生成的语句真的跑起来
  - 够用：学习项目要的是"SQL 真的执行了"，不是"撑住十亿行数据"

生产级思考：
  这里最关键的一点是——执行器(QueryExecutor)只依赖一个"数据库连接"，
  不关心底层是 SQLite 还是 ClickHouse。真实项目里把 SQLite 换成
  ClickHouse 的驱动，执行器代码几乎不用改。这就是"面向接口编程"。
"""

import sqlite3
from pathlib import Path
from typing import Optional


class MockWarehouse:
    """
    模拟数仓 —— 负责建表、插数、提供数据库连接。

    小白理解：这个类就像"仓库管理员"，负责把货架（表）搭好、把货（数据）摆好。
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化。db_path 是 SQLite 文件路径，默认存在项目 data 目录下。
        """
        if db_path is None:
            # 默认存到 data/ 目录（学习项目用文件数据库，方便查看）
            db_path = Path(__file__).resolve().parent.parent.parent / "data" / "mock_warehouse.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # 让查询结果能用 row['字段名'] 访问
        self._setup()

    def _setup(self):
        """建表 + 插数据（幂等：如果表已存在就先删掉重建）。"""
        cursor = self.conn.cursor()

        # ── 表 1：逾期率日报 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ads_delinquency_daily (
                label_date      TEXT PRIMARY KEY,   -- 标签观察日期（月初）
                total_loans     INTEGER,             -- 放贷总笔数
                bad_loans       INTEGER,             -- 逾期笔数（DPD30+）
                delinquency_rate REAL,               -- 逾期率（预计算）
                dt              TEXT                 -- 分区键
            )
        """)

        # ── 表 2：模型监控日报 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ads_model_monitor_daily (
                dt                  TEXT PRIMARY KEY,
                total_applications  INTEGER,
                approval_rate       REAL,
                avg_credit_limit    REAL,
                avg_score           REAL
            )
        """)

        # ── 插入 6 个月的逾期率数据 ──
        # 关键：逾期率要有真实的月度波动，这样"上月 vs 上上月"才有对比意义
        # 数据设计：6月逾期率明显高于5月，演示"环比上升"
        delinquency_data = [
            ("2026-01-01", 10000, 210, 0.021, "2026-01-01"),
            ("2026-02-01", 10500, 235, 0.022, "2026-02-01"),
            ("2026-03-01", 11000, 260, 0.024, "2026-03-01"),
            ("2026-04-01", 10800, 275, 0.025, "2026-04-01"),
            ("2026-05-01", 12000, 336, 0.028, "2026-05-01"),
            ("2026-06-01", 12500, 400, 0.032, "2026-06-01"),  # 6月明显上升
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO ads_delinquency_daily "
            "(label_date, total_loans, bad_loans, delinquency_rate, dt) "
            "VALUES (?, ?, ?, ?, ?)",
            delinquency_data,
        )

        # ── 插入 6 个月的审批指标数据 ──
        monitor_data = [
            ("2026-01-01", 5000, 0.72, 15000, 620),
            ("2026-02-01", 5200, 0.70, 14800, 615),
            ("2026-03-01", 5500, 0.68, 14500, 610),
            ("2026-04-01", 5300, 0.66, 14200, 605),
            ("2026-05-01", 6000, 0.64, 14000, 600),
            ("2026-06-01", 6200, 0.62, 13800, 595),
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO ads_model_monitor_daily "
            "(dt, total_applications, approval_rate, avg_credit_limit, avg_score) "
            "VALUES (?, ?, ?, ?, ?)",
            monitor_data,
        )

        self.conn.commit()
        cursor.close()

    def get_connection(self) -> sqlite3.Connection:
        """返回数据库连接（执行器靠它执行 SQL）。"""
        return self.conn

    def close(self):
        """关闭连接。"""
        self.conn.close()
