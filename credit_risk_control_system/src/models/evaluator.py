"""
模型评估器 — KS/AUC/Gini/PSI/Lift 全维度评估

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §5.5
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from sklearn.metrics import roc_auc_score


@dataclass
class EvalReport:
    """模型评估报告"""
    # 区分度指标
    auc_train: float = 0.0
    auc_test: float = 0.0
    ks_train: float = 0.0
    ks_test: float = 0.0
    gini_test: float = 0.0

    # 稳定性指标
    psi_train_test: float = 0.0

    # 过拟合度
    overfit_gap: float = 0.0   # AUC_train - AUC_test

    # Lift 分析
    lift_table: list[dict] = field(default_factory=list)

    # 判断
    passed: bool = False
    failures: list[str] = field(default_factory=list)


class ModelEvaluator:
    """
    模型评估器 — 金融风控标准评估方法。

    上线标准:
    - AUC >= 0.65
    - KS >= 0.25
    - PSI < 0.25
    - Overfit Gap < 0.05
    """

    MIN_AUC = 0.65
    MIN_KS = 0.25
    MAX_PSI = 0.25
    MAX_OVERFIT_GAP = 0.05

    def evaluate(
        self,
        y_train: np.ndarray, y_train_pred: np.ndarray,
        y_test: np.ndarray, y_test_pred: np.ndarray,
        n_lift_bins: int = 10,
    ) -> EvalReport:
        """全维度评估"""
        report = EvalReport()
        failures = []

        # AUC
        report.auc_train = roc_auc_score(y_train, y_train_pred)
        report.auc_test = roc_auc_score(y_test, y_test_pred)
        if report.auc_test < self.MIN_AUC:
            failures.append(
                f"AUC={report.auc_test:.4f} < {self.MIN_AUC}"
            )

        # KS
        report.ks_train = self._calculate_ks(y_train, y_train_pred)
        report.ks_test = self._calculate_ks(y_test, y_test_pred)
        if report.ks_test < self.MIN_KS:
            failures.append(
                f"KS={report.ks_test:.4f} < {self.MIN_KS}"
            )

        # Gini = 2*AUC - 1
        report.gini_test = 2 * report.auc_test - 1

        # PSI
        report.psi_train_test = self._calculate_psi(
            y_train_pred, y_test_pred, bins=n_lift_bins
        )
        if report.psi_train_test > self.MAX_PSI:
            failures.append(
                f"PSI={report.psi_train_test:.4f} > {self.MAX_PSI}"
            )

        # Overfit Gap
        report.overfit_gap = report.auc_train - report.auc_test
        if report.overfit_gap > self.MAX_OVERFIT_GAP:
            failures.append(
                f"Overfit={report.overfit_gap:.4f} > {self.MAX_OVERFIT_GAP}"
            )

        # Lift
        report.lift_table = self._calculate_lift(y_test, y_test_pred, n_lift_bins)

        report.passed = len(failures) == 0
        report.failures = failures

        return report

    def _calculate_ks(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> float:
        """
        KS = max(|TPR - FPR|)

        按预测分从高到低排序，计算每个截断点的 TPR(召回坏样本) 和
        FPR(误杀好样本)，取最大差值。
        """
        sorted_idx = np.argsort(y_pred)[::-1]
        y_sorted = y_true[sorted_idx]

        n_pos = np.sum(y_true == 1).item()
        n_neg = np.sum(y_true == 0).item()

        if n_pos == 0 or n_neg == 0:
            return 0.0

        tpr = np.cumsum(y_sorted == 1) / n_pos
        fpr = np.cumsum(y_sorted == 0) / n_neg

        return float(np.max(np.abs(tpr - fpr)))

    def _calculate_psi(
        self, expected: np.ndarray, actual: np.ndarray,
        bins: int = 10
    ) -> float:
        """
        PSI = Σ (Actual% - Expected%) * ln(Actual% / Expected%)

        衡量两个分布的差异程度。
        PSI > 0.25 → 模型可能失效，需要重训。
        """
        expected_pct, _ = np.histogram(expected, bins=bins)
        actual_pct, _ = np.histogram(actual, bins=bins)

        expected_pct = expected_pct.astype(float) / len(expected)
        actual_pct = actual_pct.astype(float) / len(actual)

        expected_pct = np.clip(expected_pct, 1e-6, None)
        actual_pct = np.clip(actual_pct, 1e-6, None)

        return float(np.sum(
            (actual_pct - expected_pct) *
            np.log(actual_pct / expected_pct)
        ))

    def _calculate_lift(
        self, y_true: np.ndarray, y_pred: np.ndarray, bins: int = 10
    ) -> list[dict]:
        """
        Lift 分析 — 每个分数分箱的坏账率。

        Lift = 分箱坏账率 / 整体坏账率
        Lift > 1: 该分箱风险高于平均
        Lift < 1: 该分箱风险低于平均
        """
        df = pd.DataFrame({'score': y_pred, 'label': y_true})
        df['bin'] = pd.qcut(
            df['score'], q=bins, labels=False, duplicates='drop'
        )
        overall_bad_rate = float(y_true.mean())

        result = []
        for b in sorted(df['bin'].unique()):
            bin_df = df[df['bin'] == b]
            bad_rate = float(bin_df['label'].mean())
            lift = bad_rate / overall_bad_rate if overall_bad_rate > 0 else 0
            result.append({
                'bin': int(b),
                'count': len(bin_df),
                'score_min': round(float(bin_df['score'].min()), 4),
                'score_max': round(float(bin_df['score'].max()), 4),
                'bad_rate': round(bad_rate, 4),
                'lift': round(lift, 4),
            })
        return result
