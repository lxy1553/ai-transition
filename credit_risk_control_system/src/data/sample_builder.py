"""
训练样本构建器 — 标签拼接 + 特征快照（防止时间泄漏）

PRODUCTION: 使用 Feast PIT Join（见 src/feature_store/pit_join.py）
  本模块是简化版，演示样本构建的核心流程。
"""

import pandas as pd
from datetime import datetime


class TrainingSampleBuilder:
    """
    训练样本构建器。

    流程:
    1. 取申请记录 + T+30 表现标签（左表）
    2. 取申请时刻的特征快照（右表）
    3. 拼接为训练样本
    """

    def build(
        self,
        applications: pd.DataFrame,          # {user_id, application_id, application_time, label}
        feature_snapshots: pd.DataFrame,      # {user_id, dt, feature_1, feature_2, ...}
        performance_window_days: int = 30,
    ) -> pd.DataFrame:
        """
        构建训练样本。

        PRODUCTION: 严格 PIT Join
          特征快照的 dt <= application_time
          且取最近的一天（通常是前一日 T-1）
        """
        apps = applications.copy()
        apps['application_date'] = pd.to_datetime(
            apps['application_time']
        ).dt.strftime('%Y-%m-%d')

        features = feature_snapshots.copy()

        # 按用户和日期合并（简化: 取申请日期的特征快照）
        samples = apps.merge(
            features,
            left_on=['user_id', 'application_date'],
            right_on=['user_id', 'dt'],
            how='left',
        )

        # 移除标签泄露列
        drop_cols = ['application_date', 'dt']
        samples = samples.drop(columns=[c for c in drop_cols if c in samples.columns])

        return samples
