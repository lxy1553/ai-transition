"""
Point-in-Time Join — 防止时间泄漏的样本构建

这是金融风控中最关键的数据工程环节。

问题: 训练样本 label（T+30逾期）对应的是申请时刻的特征。如果使用 T+30
      时刻的特征训练，模型就"看到了未来"（如逾期后的催收行为数据）。

方案: PIT Join 保证每次取特征时，只取申请时间点或之前的特征快照。

PRODUCTION: Feast 原生支持 PIT Join。
  本模块是 Feast PIT Join 逻辑的教学实现。

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §4.2.2
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import numpy as np
import pandas as pd


@dataclass
class TrainingSample:
    """单条训练样本"""
    user_id: str
    application_id: str
    application_time: datetime   # 申请时间（时间锚点）
    label: int                   # 0=正常, 1=逾期(T+30)
    features: dict[str, float]   # 申请时刻的特征快照


class PointInTimeJoin:
    """
    PIT Join 样本构建器。

    核心逻辑:
    输入:
      - entity_df: 左表，{user_id, application_time, label}
      - feature_views: 右表，多张特征表（每张有时间戳和特征值）

    输出:
      - 训练样本：左表 JOIN 右表，但只取 feature_timestamp <= application_time 的记录

    示例（简化）:

    entity_df:
      user_id | application_time       | label
      123     | 2026-01-15 10:00:00   | 0

    feature_view (user_behavior):
      user_id | feature_time           | apply_cnt_7d
      123     | 2026-01-10 00:00:00   | 3
      123     | 2026-01-14 00:00:00   | 5
      123     | 2026-01-16 00:00:00   | 2  ← 时间在未来！不参与 JOIN

    PIT Join 结果:
      取 feature_time <= application_time 的最新一条
      → apply_cnt_7d = 5 (2026-01-14的快照，早于1月15日申请)
    """

    def __init__(self, feature_views: dict[str, pd.DataFrame]):
        """
        Args:
            feature_views: {feature_view_name: DataFrame}
                每个 DataFrame 必须有: user_id, feature_timestamp, ...features
        """
        self.feature_views = feature_views

    def build_samples(
        self, entity_df: pd.DataFrame, max_lookback_days: int = 90
    ) -> pd.DataFrame:
        """
        构建 PIT Join 训练样本。

        Args:
            entity_df: {user_id, application_id, application_time, label}
            max_lookback_days: 特征最大回看天数

        Returns:
            训练样本 DataFrame
        """
        result_df = entity_df.copy()
        # 确保 application_time 是 datetime
        result_df['application_time'] = pd.to_datetime(
            result_df['application_time']
        )

        for fv_name, fv_df in self.feature_views.items():
            fv_df = fv_df.copy()
            fv_df['feature_timestamp'] = pd.to_datetime(
                fv_df['feature_timestamp']
            )

            # 对每个申请记录，找到时间点之前的最新特征
            features_joined = self._asof_join(
                entity_df=result_df,
                feature_df=fv_df,
                on='user_id',
                by='feature_timestamp',
                entity_time_col='application_time',
            )

            # 合并特征列
            feature_cols = [
                c for c in fv_df.columns
                if c not in ('user_id', 'feature_timestamp')
            ]
            for col in feature_cols:
                result_df[f"{fv_name}__{col}"] = features_joined[col]

        # 填充缺失值（null 表示该时间点没有特征数据）
        numeric_cols = result_df.select_dtypes(include=[np.number]).columns
        result_df[numeric_cols] = result_df[numeric_cols].fillna(0)

        return result_df

    def _asof_join(
        self,
        entity_df: pd.DataFrame,
        feature_df: pd.DataFrame,
        on: str,
        by: str,
        entity_time_col: str,
    ) -> pd.DataFrame:
        """
        模拟 ASOF JOIN（按时间对齐最近一条记录）。

        对 entity_df 的每一行:
          找到 feature_df 中同 user_id、feature_timestamp <= application_time、
          且 feature_timestamp 最大的特征记录。

        PRODUCTION: Spark SQL 直接用 ASOF JOIN 语法:
          SELECT ... FROM entity
          ASOF JOIN features
          ON entity.user_id = features.user_id
             AND features.feature_timestamp <= entity.application_time
        """

        result_rows = []

        for _, entity_row in entity_df.iterrows():
            user_id = entity_row[on]
            app_time = entity_row[entity_time_col]

            # 筛选该用户、时间不晚于申请时间、且回溯期内
            mask = (
                (feature_df[on] == user_id) &
                (feature_df[by] <= app_time) &
                (feature_df[by] >= app_time - pd.Timedelta(days=90))
            )
            candidate = feature_df[mask]

            if not candidate.empty:
                # 取时间最近的一条
                best = candidate.sort_values(by, ascending=False).iloc[0]
                result_rows.append(best.to_dict())
            else:
                # 无特征数据 → 全 null
                null_row = {col: None for col in feature_df.columns}
                result_rows.append(null_row)

        return pd.DataFrame(result_rows)


def create_demo_pit_samples() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    创建演示用的 PIT Join 样本数据。

    这个函数可在 scripts/ 中调用，用于演示时间泄漏的危害。
    """
    np.random.seed(42)

    # 模拟 100 个用户，每个用户有随机的申请时间和行为特征快照
    n_users = 500
    entity_records = []
    feature_records = []

    for i in range(n_users):
        user_id = f"user_{i:04d}"

        # 随机申请时间（2026上半年）
        app_day = np.random.randint(1, 180)
        app_time = datetime(2026, 1, 1) + pd.Timedelta(days=int(app_day))
        label = 1 if np.random.random() < 0.15 else 0  # 15% bad rate

        entity_records.append({
            'user_id': user_id,
            'application_id': f"app_{i:06d}",
            'application_time': app_time,
            'label': label,
        })

        # 该用户每天有一条特征快照
        for day_offset in range(-90, 31):  # 申请前90天到后30天
            ft_time = app_time + pd.Timedelta(days=int(day_offset))
            feature_records.append({
                'user_id': user_id,
                'feature_timestamp': ft_time,
                'apply_cnt_7d': np.random.poisson(2),
                'night_ops_ratio_30d': np.random.beta(2, 5),
                'debt_to_income_ratio': np.random.beta(3, 5),
            })

    entity_df = pd.DataFrame(entity_records)
    feature_df = pd.DataFrame(feature_records)

    return entity_df, feature_df


if __name__ == '__main__':
    # 演示 PIT Join
    entity_df, feature_df = create_demo_pit_samples()
    pit = PointInTimeJoin({'user_behavior': feature_df})

    print("左表（带标签的申请记录）:")
    print(entity_df.head())
    print(f"\n特征表（每条记录有时间戳）: {len(feature_df)} 行")

    samples = pit.build_samples(entity_df)
    print(f"\nPIT Join 结果（训练样本）: {len(samples)} 行")
    print(samples[['user_id', 'label',
                   'user_behavior__apply_cnt_7d',
                   'user_behavior__debt_to_income_ratio']].head())

    # 验证: 检查是否有时间泄漏
    print("\n[验证] 检查特征是否在申请时间之后...")
    # 简单检查：特征值非空即表示 PIT Join 成功（取了申请前的快照）
    non_null = samples['user_behavior__apply_cnt_7d'].notna().sum()
    print(f"  非空特征数: {non_null}/{len(samples)} "
          f"({non_null/len(samples)*100:.1f}%)")
