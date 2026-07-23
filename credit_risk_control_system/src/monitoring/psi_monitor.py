"""
特征 PSI 漂移监控 — 每日检测特征分布变化

PSI (Population Stability Index) 是金融风控中最重要的模型监控指标。
PSI > 0.25 → 特征分布显著偏移，模型可能失效，需触发熔断或重训。

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §5.6
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class PSIAlert:
    feature: str
    psi: float
    level: str        # WARNING / CRITICAL
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PSIReport:
    check_date: str
    total_features: int
    features_above_warning: int    # PSI > 0.10
    features_above_critical: int   # PSI > 0.25
    alerts: list[PSIAlert]
    psi_details: dict[str, float]  # feature_name → psi


class FeaturePSIMonitor:
    """
    特征漂移监控器。

    每日运行流程:
    1. 加载基准分布（训练集的特征直方图）
    2. 获取当日特征分布
    3. 逐特征计算 PSI
    4. 超过阈值则告警

    PRODUCTION:
    - 基准分布存储在 MLflow 模型 artifact 中
    - 每日分布从 DWS 宽表 / ClickHouse 查询
    - 告警通过 Prometheus Alertmanager → 钉钉/邮件/PagerDuty
    """

    PSI_WARNING = 0.10
    PSI_CRITICAL = 0.25

    def __init__(
        self,
        baseline_distribution: Optional[dict] = None,
        baseline_path: Optional[str] = None,
    ):
        if baseline_distribution:
            self.baseline = baseline_distribution
        elif baseline_path:
            self.baseline = json.loads(Path(baseline_path).read_text())
        else:
            self.baseline = {}

    def run_daily_check(
        self, current_df: pd.DataFrame, check_date: Optional[str] = None
    ) -> PSIReport:
        """
        每日 PSI 检测。

        Args:
            current_df: 当日特征 DataFrame（需与 baseline 特征对齐）
            check_date: 检测日期

        Returns:
            PSI 报告
        """
        if check_date is None:
            check_date = datetime.now().strftime('%Y-%m-%d')

        alerts = []
        psi_details = {}

        for feature, baseline_stats in self.baseline.items():
            if feature not in current_df.columns:
                continue

            # 当日分布
            current_values = current_df[feature].dropna().values
            if len(current_values) == 0:
                continue

            current_hist, _ = np.histogram(
                current_values,
                bins=baseline_stats.get('n_bins', 10)
            )

            expected_hist = np.array(baseline_stats['histogram'])

            # 计算 PSI
            psi = self._calculate_psi(expected_hist, current_hist)
            psi_details[feature] = round(psi, 4)

            # 判断告警
            if psi > self.PSI_CRITICAL:
                alerts.append(PSIAlert(
                    feature=feature, psi=round(psi, 4),
                    level='CRITICAL',
                    message=f'[CRITICAL] {feature} PSI={psi:.4f} > 0.25, '
                            f'特征分布严重偏移，建议触发模型重训'
                ))
            elif psi > self.PSI_WARNING:
                alerts.append(PSIAlert(
                    feature=feature, psi=round(psi, 4),
                    level='WARNING',
                    message=f'[WARNING] {feature} PSI={psi:.4f} > 0.10, '
                            f'特征分布有偏移趋势'
                ))

        return PSIReport(
            check_date=check_date,
            total_features=len(psi_details),
            features_above_warning=sum(
                1 for p in psi_details.values() if p > self.PSI_WARNING
            ),
            features_above_critical=sum(
                1 for p in psi_details.values() if p > self.PSI_CRITICAL
            ),
            alerts=alerts,
            psi_details=psi_details,
        )

    def build_baseline_from_df(
        self, df: pd.DataFrame, feature_cols: list[str],
        n_bins: int = 10
    ) -> dict:
        """从训练集 DataFrame 构建基准分布"""
        baseline = {}
        for col in feature_cols:
            if col not in df.columns:
                continue
            values = df[col].dropna()
            hist, _ = np.histogram(values, bins=n_bins)
            baseline[col] = {
                'histogram': hist.tolist(),
                'n_bins': n_bins,
                'mean': float(values.mean()),
                'std': float(values.std()),
                'null_rate': float(df[col].isna().mean()),
            }
        self.baseline = baseline
        return baseline

    def save_baseline(self, path: str) -> None:
        """保存基准分布到文件"""
        Path(path).write_text(json.dumps(self.baseline, indent=2))

    @staticmethod
    def _calculate_psi(
        expected_hist: np.ndarray, actual_hist: np.ndarray
    ) -> float:
        """
        计算 PSI = Σ (A_i - E_i) * ln(A_i / E_i)
        """
        expected = np.array(expected_hist, dtype=float)
        actual = np.array(actual_hist, dtype=float)

        expected_pct = expected / (expected.sum() or 1)
        actual_pct = actual / (actual.sum() or 1)

        expected_pct = np.clip(expected_pct, 1e-6, None)
        actual_pct = np.clip(actual_pct, 1e-6, None)

        return float(np.sum(
            (actual_pct - expected_pct) *
            np.log(actual_pct / expected_pct)
        ))
