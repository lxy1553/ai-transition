"""
ADS 层 (Application Data Service) — 应用数据层

职责: 直接服务上层应用，不做通用性保留。

ADS 层的核心产出:
  ┌─────────────────────────────────────────────────────┐
  │ ads_training_samples     — 模型训练样本集            │
  │ ads_model_monitor        — 模型监控指标日报          │
  │ ads_approval_rate_daily  — 审批通过率日报 (BI)       │
  │ ads_delinquency_daily    — 逾期率日报 (BI)           │
  │ ads_portfolio_analysis   — 资产组合分析 (风控报表)   │
  │ ads_feature_psi_daily    — 特征PSI监控日报           │
  └─────────────────────────────────────────────────────┘

PRODUCTION: Spark SQL 生成各 ADS 表，写入 ClickHouse/Iceberg。
BI 工具 (Grafana/Superset) 直接查询本层数据。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field


class ADSLayer:
    """
    ADS 层 — 面向应用的数据集市。

    各表设计原则: 宽表、预聚合、即查即用。
    不做复杂 JOIN，BI 工具/模型训练直接读取。
    """

    def __init__(self, storage_path: str = "./data/warehouse/ads"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    # ── 1. 模型训练样本 ──────────────────────────────

    def build_training_samples(
        self,
        dws_wide_table: pd.DataFrame,
        label_df: pd.DataFrame,
        performance_window_days: int = 30,
    ) -> pd.DataFrame:
        """
        ads_training_samples — 模型训练样本集。

        输入: DWS 宽表 (用户×日期的特征) + 标签表 (T+30逾期)
        输出: 带标签的训练样本

        这是 PIT Join 的最后一站:
        - DWS 宽表的特征快照时间是 dt
        - label 是该用户在 dt + 30 天后的逾期标签
        - 拼接时严格 dt_特征 < dt_标签

        PRODUCTION:
          INSERT OVERWRITE TABLE ads.training_samples
          SELECT
            w.*,
            l.label,
            l.performance_date
          FROM dws.user_risk_feature_wide w
          LEFT JOIN ads.loan_labels l
            ON w.user_id = l.user_id
            AND w.dt = DATE_SUB(l.label_date, ${performance_window_days})
        """
        samples = dws_wide_table.merge(
            label_df, on='user_id', how='inner'
        )

        # 移除不需要的列
        drop_cols = [c for c in ['dt_y', 'performance_date']
                    if c in samples.columns]
        samples = samples.drop(columns=drop_cols)

        print(f"[ADS] 训练样本: {len(samples)} 条, "
              f"坏样本率: {samples['label'].mean():.2%}")

        return samples

    # ── 2. 模型监控日报 ──────────────────────────────

    def build_model_monitor_daily(
        self,
        predictions: pd.DataFrame,    # {user_id, dt, score, default_prob, decision}
        dws_wide_table: pd.DataFrame,
        dt: str,
    ) -> pd.DataFrame:
        """
        ads_model_monitor — 模型监控指标日报。

        每日一条记录，包含:
          total_applications    总申请数
          approval_rate         通过率
          avg_score             平均评分
          score_std             评分标准差
          reject_rate           拒绝率
          manual_review_rate    人工审核率
          avg_credit_limit      平均授信额度

        PRODUCTION: 此表直接对接 Grafana 模型监控大盘。
        """
        n_total = len(predictions)
        if n_total == 0:
            return pd.DataFrame()

        approved = predictions[predictions['decision'] == 'APPROVE']
        rejected = predictions[predictions['decision'] == 'REJECT']
        manual = predictions[predictions['decision'] == 'MANUAL_REVIEW']

        monitor = pd.DataFrame([{
            'dt': dt,
            'total_applications': n_total,
            'approval_rate': round(len(approved) / n_total, 4),
            'reject_rate': round(len(rejected) / n_total, 4),
            'manual_review_rate': round(len(manual) / n_total, 4),
            'avg_score': round(predictions['score'].mean(), 2),
            'score_std': round(predictions['score'].std(), 2),
            'score_p10': round(predictions['score'].quantile(0.10), 2),
            'score_p50': round(predictions['score'].quantile(0.50), 2),
            'score_p90': round(predictions['score'].quantile(0.90), 2),
            'avg_credit_limit': round(
                predictions[predictions['credit_limit'] > 0]['credit_limit'].mean(), 2
            ),
            'avg_latency_ms': round(predictions.get('latency_ms', pd.Series([0])).mean(), 2),
        }])

        return monitor

    # ── 3. 逾期率日报 ────────────────────────────────

    def build_delinquency_daily(
        self,
        labels: pd.DataFrame,       # {user_id, label_date, label(DPD30+)}
        by_channel: bool = False,
    ) -> pd.DataFrame:
        """
        ads_delinquency_daily — 逾期率日报。

        支持:
        - 按日期: 每日逾期率趋势
        - 按渠道: 各渠道逾期率对比
        - 按模型版本: A/B 测试效果对比
        """
        labels['label_date'] = pd.to_datetime(labels.get('label_date', datetime.now()))

        daily = labels.groupby(
            labels['label_date'].dt.strftime('%Y-%m-%d')
        ).agg(
            total_loans=('user_id', 'count'),
            bad_loans=('label', 'sum'),
        ).reset_index()

        daily['delinquency_rate'] = round(
            daily['bad_loans'] / daily['total_loans'], 4
        )

        return daily

    # ── 4. 资产组合分析 ──────────────────────────────

    def build_portfolio_analysis(
        self,
        decisions: pd.DataFrame,     # {user_id, decision, score, credit_limit}
        dws_wide_table: pd.DataFrame,
    ) -> dict:
        """
        ads_portfolio_analysis — 资产组合分析。

        风控报表核心指标:
          - 分数段分布 (A+/A/B+/B/C/D)
          - 额度利用率
          - 各渠道资产质量
          - 地域集中度
        """
        merged = decisions.merge(dws_wide_table, on='user_id', how='left')

        def score_bucket(s):
            if s >= 750: return 'A+'
            if s >= 700: return 'A'
            if s >= 650: return 'B+'
            if s >= 600: return 'B'
            if s >= 500: return 'C'
            return 'D'

        merged['bucket'] = merged['score'].apply(score_bucket)

        return {
            'total_portfolio': int(len(merged)),
            'total_credit_exposure': round(float(merged['credit_limit'].sum()), 2),
            'avg_credit_limit': round(float(merged['credit_limit'].mean()), 2),
            'score_distribution': {k: int(v) for k, v in merged['bucket'].value_counts().to_dict().items()},
            'avg_score_by_bucket': {k: round(float(v), 1) for k, v in merged.groupby('bucket')['score'].mean().to_dict().items()},
        }

    # ── 5. 特征 PSI 监控 ─────────────────────────────

    def build_feature_psi_daily(
        self,
        current_dws: pd.DataFrame,
        baseline_stats: dict,
        dt: str,
    ) -> pd.DataFrame:
        """
        ads_feature_psi_daily — 特征 PSI 监控日报。

        这是监控体系的核心——每日计算各特征 PSI。

        输出: {dt, feature_name, psi, level, baseline_mean, current_mean}
        """
        from src.monitoring.psi_monitor import FeaturePSIMonitor

        monitor = FeaturePSIMonitor(baseline_distribution=baseline_stats)
        report = monitor.run_daily_check(current_dws, dt)

        rows = []
        for feature, psi in report.psi_details.items():
            rows.append({
                'dt': dt,
                'feature': feature,
                'psi': psi,
                'level': 'CRITICAL' if psi > 0.25 else ('WARNING' if psi > 0.10 else 'OK'),
            })

        return pd.DataFrame(rows)

    def summary(self) -> str:
        return """
╔══════════════════════════════════════════════════╗
║  ADS 层 — 应用数据层                             ║
╠══════════════════════════════════════════════════╣
║  原则: 直接服务上层应用，预聚合、即查即用         ║
╠══════════════════════════════════════════════════╣
║  ┌─────────────────────────────────────────────┐ ║
║  │ ads_training_samples                        │ ║
║  │  → 模型训练 (XGBoost/评分卡)                 │ ║
║  │  → 特征: DWS宽表 + 标签 T+30                 │ ║
║  │                                              │ ║
║  │ ads_model_monitor                           │ ║
║  │  → Grafana 模型监控大盘                      │ ║
║  │  → 指标: 通过率/评分分布/额度/延迟            │ ║
║  │                                              │ ║
║  │ ads_delinquency_daily                       │ ║
║  │  → 风控报表 / 监管报送                       │ ║
║  │  → 指标: 逾期率(DPD30+)/Vintage分析           │ ║
║  │                                              │ ║
║  │ ads_portfolio_analysis                      │ ║
║  │  → 资产组合分析 / 风险仪表盘                  │ ║
║  │  → 指标: 分数段分布/地域集中度/渠道质量       │ ║
║  │                                              │ ║
║  │ ads_feature_psi_daily                       │ ║
║  │  → 特征漂移监控 / 模型重训触发                │ ║
║  │  → 指标: PSI / 空值率变化                     │ ║
║  └─────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════╝
"""
