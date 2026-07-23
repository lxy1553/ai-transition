"""
离线特征存储 — 历史特征快照（Parquet/Iceberg）

PRODUCTION: Apache Iceberg on S3/HDFS
  - ACID事务: 特征回填不会破坏已有数据
  - Time Travel: 可回溯任意历史时刻的特征
  - Schema演进: 新增特征列不影响已有数据

DEV: 本地 Parquet 文件

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §1.4
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


class OfflineFeatureStore:
    """
    离线特征存储。

    职责:
    1. 存储每日特征快照（按 dt 分区）
    2. 支持历史回溯查询
    3. 为模型训练提供批量特征数据

    数据分层: DWS（用户风险特征宽表）
      分区键: dt (YYYY-MM-DD)
      主键: user_id
      内容: 基础画像 + 行为衍生 + 征信衍生 + 多头 + 设备 + ... 共 50+ 列
    """

    def __init__(self, storage_path: str = "./data/offline_features"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def write_daily_snapshot(
        self, dt: str, features_df: pd.DataFrame
    ) -> None:
        """
        写入每日特征快照。

        PRODUCTION: 写入 Iceberg 表
          INSERT OVERWRITE dws.user_risk_feature_wide
          PARTITION (dt = '2026-01-15')
          SELECT ...

        DEV: 写入 Parquet 文件
        """
        partition_path = self.storage_path / f"dt={dt}"
        partition_path.mkdir(parents=True, exist_ok=True)

        file_path = partition_path / "features.parquet"
        features_df.to_parquet(file_path, index=False)

        print(f"[OfflineStore] 写入 {dt}: {len(features_df)} 用户, "
              f"{len(features_df.columns)} 特征")

    def read_daily_snapshot(self, dt: str) -> pd.DataFrame:
        """读取指定日期的特征快照"""
        file_path = self.storage_path / f"dt={dt}" / "features.parquet"
        if not file_path.exists():
            raise FileNotFoundError(
                f"未找到 {dt} 的特征快照: {file_path}"
            )
        return pd.read_parquet(file_path)

    def read_time_range(
        self, start_dt: str, end_dt: str
    ) -> pd.DataFrame:
        """读取时间范围内的所有特征"""
        dfs = []
        current = datetime.strptime(start_dt, '%Y-%m-%d')
        end = datetime.strptime(end_dt, '%Y-%m-%d')

        while current <= end:
            dt_str = current.strftime('%Y-%m-%d')
            try:
                df = self.read_daily_snapshot(dt_str)
                df['dt'] = dt_str
                dfs.append(df)
            except FileNotFoundError:
                pass
            current += timedelta(days=1)

        if not dfs:
            raise FileNotFoundError(
                f"时间范围 {start_dt} ~ {end_dt} 没有特征数据"
            )
        return pd.concat(dfs, ignore_index=True)

    def get_historical_feature(
        self, user_id: str, as_of_date: str
    ) -> Optional[dict]:
        """
        Point-in-Time 查询: 获取用户在某日期的特征快照。

        PRODUCTION: Iceberg Time Travel
          SELECT * FROM dws.user_risk_feature_wide
          TIMESTAMP AS OF '2026-01-15 00:00:00'
          WHERE user_id = 'xxx'
        """
        try:
            df = self.read_daily_snapshot(as_of_date)
            row = df[df['user_id'] == user_id]
            if not row.empty:
                return row.iloc[0].to_dict()
        except FileNotFoundError:
            pass
        return None

    # ── 模拟数据生成（DEV用）──────────────────────────

    @staticmethod
    def generate_mock_features(
        user_ids: list[str], dt: str, n_features: int = 25
    ) -> pd.DataFrame:
        """
        生成模拟用户特征宽表（50+ 列，模拟 DWS 层输出）。

        用于本地开发和测试。
        """
        np.random.seed(hash(dt) % 2**32)
        n = len(user_ids)

        data = {
            'user_id': user_ids,
            'dt': [dt] * n,

            # 基础画像
            'age': np.random.randint(18, 65, n),
            'age_bucket': np.random.choice(
                ['<22', '22-30', '30-40', '40-50', '50+'], n
            ),
            'monthly_income': np.random.choice(
                [3000, 5000, 8000, 12000, 20000, 35000], n
            ),
            'income_level': np.random.choice(
                ['<3k', '3-8k', '8-15k', '15-30k', '30k+'], n
            ),
            'education': np.random.choice(
                ['high', 'bachelor', 'master', 'phd'], n,
                p=[0.4, 0.4, 0.15, 0.05]
            ),

            # 行为特征
            'apply_cnt_7d': np.random.poisson(1, n),
            'apply_cnt_30d': np.random.poisson(3, n),
            'night_ops_ratio_30d': np.random.beta(2, 5, n),
            'avg_session_duration_7d': np.random.exponential(60, n),
            'device_change_cnt_30d': np.random.poisson(0.5, n),

            # 征信衍生
            'credit_score_raw': np.random.normal(600, 80, n).clip(300, 900).astype(int),
            'credit_score_normalized': np.random.beta(5, 3, n),
            'debt_to_income_ratio': np.random.beta(3, 5, n),
            'overdue_cnt_hist': np.random.poisson(0.5, n),
            'query_cnt_3m': np.random.poisson(1, n),

            # 多头借贷
            'multi_head_cnt_7d': np.random.poisson(1, n),
            'multi_head_cnt_30d': np.random.poisson(3, n),

            # 设备指纹
            'device_risk_score': np.random.beta(2, 6, n),
            'device_rooted_flag': np.random.choice([0, 1], n, p=[0.95, 0.05]),
            'device_linked_users': np.random.poisson(0.5, n),
            'sim_change_cnt_30d': np.random.poisson(0.3, n),

            # 反欺诈
            'fraud_score': np.random.beta(1, 8, n),
            'identity_verified': np.random.choice(
                [True, False], n, p=[0.97, 0.03]
            ),
        }

        return pd.DataFrame(data)
