"""
DWS 层 (Data Warehouse Summary) — 汇总数据层 ★ 核心

职责: 按主题聚合明细数据，构建"用户风险特征宽表"。

这是整个数仓的核心层:
  - 下游 ADS 层的模型训练样本直接取自此层
  - 实时特征在 Flink 中计算，离线特征在 Spark 中计算
  - 每行 = 一个用户在某一天的完整风险画像

特征工程范畴:
  ┌────────────────────────────────────────────────────┐
  │  基础画像    → 从 dwd_application 聚合              │
  │  行为衍生    → 从 dwd_user_behavior 滑动窗口聚合     │
  │  征信衍生    → 从征信 API 结果计算                   │
  │  多头衍生    → 从多头查询结果计算                     │
  │  设备衍生    → 从设备指纹记录聚合                    │
  │  还款表现    → 从 dwd_repayment 聚合                │
  └────────────────────────────────────────────────────┘

PRODUCTION:
  离线: Spark SQL 每天凌晨执行，写入 Iceberg DWS 层
  实时: Flink SQL 计算滑动窗口特征，写入 Redis + ClickHouse
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass


class DWSLayer:
    """
    DWS 层 — 用户风险特征宽表构建。

    核心特征分类（5大类，50+ 特征）:
    """

    def __init__(self, storage_path: str = "./data/warehouse/dws"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def build_wide_table(
        self,
        dwd_application: pd.DataFrame,
        dwd_behavior: pd.DataFrame,
        dwd_repayment: pd.DataFrame,
        dt: str,
    ) -> pd.DataFrame:
        """
        构建用户风险特征宽表 — 将所有 DWD 层数据聚合为用户粒度。

        输入: 各 DWD 表（明细粒度）
        输出: DWS 宽表（用户粒度，一行 = 一个用户在某天的风险画像）

        PRODUCTION SQL (Spark):
          INSERT OVERWRITE TABLE dws.user_risk_feature_wide
          PARTITION (dt = '${dt}')
          SELECT
            a.user_id,
            -- 基础画像
            a.age, a.age_bucket, a.monthly_income, a.education,
            -- 行为衍生 (从行为埋点聚合)
            COALESCE(b.apply_cnt_7d, 0),
            COALESCE(b.apply_cnt_30d, 0),
            ...
          FROM dwd.dwd_application a
          LEFT JOIN dws_behavior_agg b ON a.user_id = b.user_id
          LEFT JOIN dws_repayment_agg r ON a.user_id = r.user_id
        """
        print(f"\n[DWS] 构建 {dt} 用户风险特征宽表...")

        # ── 1. 基础画像特征（从 dwd_application）──
        profile_features = self._build_profile_features(dwd_application)

        # ── 2. 行为衍生特征（从 dwd_behavior 滑动窗口）──
        behavior_features = self._build_behavior_features(dwd_behavior, dt)

        # ── 3. 还款表现特征（从 dwd_repayment）──
        repayment_features = self._build_repayment_features(dwd_repayment)

        # ── 4. 合并为宽表 ──
        wide_table = profile_features.merge(
            behavior_features, on='user_id', how='left'
        ).merge(
            repayment_features, on='user_id', how='left'
        )

        # 填充缺失值
        numeric_cols = wide_table.select_dtypes(include=[np.number]).columns
        wide_table[numeric_cols] = wide_table[numeric_cols].fillna(0)

        wide_table['dt'] = dt

        print(f"  DWS 宽表: {len(wide_table)} 用户, "
              f"{len(wide_table.columns)} 特征列")

        return wide_table

    # ── 基础画像特征 ─────────────────────────────────

    def _build_profile_features(self, app_df: pd.DataFrame) -> pd.DataFrame:
        """
        基础画像特征（用户粒度）。

        PRODUCTION SQL:
          SELECT user_id,
            MAX(age) AS age,
            CASE WHEN MAX(age) < 22 THEN '<22'
                 WHEN MAX(age) < 30 THEN '22-30'
                 ... END AS age_bucket,
            MAX(monthly_income) AS monthly_income,
            MAX(education) AS education,
            MAX(occupation) AS occupation,
            MAX(city) AS city,
            COUNT(DISTINCT application_id) AS total_apply_cnt,
            COUNT(DISTINCT device_id) AS device_cnt
          FROM dwd.dwd_application
          GROUP BY user_id
        """
        agg = app_df.groupby('user_id').agg(
            apply_amount_avg=('apply_amount', 'mean'),
            apply_amount_max=('apply_amount', 'max'),
            monthly_income=('monthly_income', 'max'),
            total_apply_cnt=('application_id', 'nunique'),
            distinct_device_cnt=('device_id', 'nunique'),
            distinct_city_cnt=('city', 'nunique'),
        ).reset_index()

        return agg

    # ── 行为衍生特征 ─────────────────────────────────

    def _build_behavior_features(
        self, behavior_df: pd.DataFrame, dt: str
    ) -> pd.DataFrame:
        """
        行为衍生特征 — 从埋点流做时间窗口聚合。

        特征列表:
          apply_cnt_7d         近7天提交申请次数
          apply_cnt_30d        近30天提交申请次数
          night_ops_ratio_30d  近30天夜间(22-06)操作占比
          avg_session_duration_7d  近7天平均会话时长
          page_view_cnt_7d     近7天页面浏览次数
          input_cnt_7d         近7天输入操作次数
          error_event_cnt_7d   近7天错误事件次数

        PRODUCTION Flink SQL:
          SELECT user_id,
            COUNT(DISTINCT CASE WHEN event_type='submit'
              AND event_time >= NOW()-INTERVAL '7' DAY
              THEN session_id END) AS apply_cnt_7d,
            ...
          FROM dwd_user_behavior
          GROUP BY user_id
        """
        if behavior_df.empty:
            return pd.DataFrame(columns=['user_id'])

        ref_date = datetime.strptime(dt, '%Y-%m-%d')
        behavior_df['event_time'] = pd.to_datetime(behavior_df['event_time'])

        result_rows = []
        for user_id, group in behavior_df.groupby('user_id'):
            # 时间窗口过滤
            in_7d = group['event_time'] >= ref_date - timedelta(days=7)
            in_30d = group['event_time'] >= ref_date - timedelta(days=30)

            group_7d = group[in_7d]
            group_30d = group[in_30d]

            # 申请次数（submit 事件数）
            apply_cnt_7d = (group_7d['event_type'] == 'submit').sum()
            apply_cnt_30d = (group_30d['event_type'] == 'submit').sum()

            # 夜间操作占比 (event_time 的小时在 22-05)
            night_hours = group_30d['event_time'].dt.hour.isin(
                [22, 23, 0, 1, 2, 3, 4, 5]
            )
            night_ops_ratio = night_hours.mean() if len(group_30d) > 0 else 0

            # 页面浏览和输入
            page_view_7d = (group_7d['event_type'] == 'page_view').sum()
            input_7d = (group_7d['event_type'] == 'input').sum()
            error_7d = (group_7d['event_type'] == 'error').sum()

            result_rows.append({
                'user_id': user_id,
                'apply_cnt_7d': apply_cnt_7d,
                'apply_cnt_30d': apply_cnt_30d,
                'night_ops_ratio_30d': round(night_ops_ratio, 4),
                'page_view_cnt_7d': page_view_7d,
                'input_cnt_7d': input_7d,
                'error_event_cnt_7d': error_7d,
            })

        return pd.DataFrame(result_rows)

    # ── 还款表现特征 ─────────────────────────────────

    def _build_repayment_features(
        self, repay_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        还款表现特征。

          overdue_cnt_hist    历史逾期次数
          avg_dpd             平均逾期天数
          current_overdue     当前是否逾期
          total_due_amount    总待还金额
          on_time_rate        按时还款率

        PRODUCTION SQL:
          SELECT user_id,
            SUM(CASE WHEN status='OVERDUE' THEN 1 ELSE 0 END) AS overdue_cnt_hist,
            AVG(dpd) AS avg_dpd,
            SUM(due_amount - paid_amount) AS total_outstanding,
            ...
          FROM dwd.dwd_repayment
          GROUP BY user_id
        """
        if repay_df.empty:
            return pd.DataFrame(columns=['user_id'])

        # 简化: 直接聚合状态
        agg = repay_df.groupby('user_id').agg(
            overdue_cnt_hist=('status', lambda x: (x == 'OVERDUE').sum()),
            total_due_amount=('due_amount', 'sum'),
            total_paid_amount=('paid_amount', 'sum'),
            repayment_cnt=('repayment_id', 'count'),
        ).reset_index()

        agg['on_time_rate'] = np.where(
            agg['repayment_cnt'] > 0,
            1 - agg['overdue_cnt_hist'] / agg['repayment_cnt'],
            1.0
        )

        return agg

    def summary(self) -> str:
        return """
╔══════════════════════════════════════════════════╗
║  DWS 层 — 汇总数据层 ★ 核心                      ║
╠══════════════════════════════════════════════════╣
║  原则: 按主题聚合，构建分析宽表                    ║
║  粒度: 用户 × 日期（每人每天一行）                 ║
╠══════════════════════════════════════════════════╣
║  ┌─────────────────────────────────────────────┐ ║
║  │ 1. 基础画像特征 (profile)                    │ ║
║  │    age, income, education, occupation, city  │ ║
║  │    → 来自 dwd_application 聚合               │ ║
║  │                                              │ ║
║  │ 2. 行为衍生特征 (behavior)                   │ ║
║  │    apply_cnt_7d/30d, night_ops_ratio_30d    │ ║
║  │    page_view_cnt, input_cnt, error_cnt       │ ║
║  │    → 来自 dwd_user_behavior 滑动窗口聚合      │ ║
║  │                                              │ ║
║  │ 3. 还款表现特征 (repayment)                  │ ║
║  │    overdue_cnt_hist, avg_dpd, on_time_rate  │ ║
║  │    → 来自 dwd_repayment 聚合                 │ ║
║  │                                              │ ║
║  │ 4. 征信衍生特征 (credit) — 模拟              │ ║
║  │    credit_score, debt_ratio, query_cnt       │ ║
║  │    → 来自征信 API 结果                       │ ║
║  │                                              │ ║
║  │ 5. 设备指纹特征 (device) — 模拟              │ ║
║  │    device_risk_score, rooted_flag            │ ║
║  │    → 来自设备 SDK 上报                       │ ║
║  └─────────────────────────────────────────────┘ ║
║                                                   ║
║  用户风险特征宽表 = profile + behavior            ║
║                     + repayment + credit + device  ║
║                                                   ║
║  下游 ADS 层直接取此表构建训练样本                 ║
╚══════════════════════════════════════════════════╝
"""
