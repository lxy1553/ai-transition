"""
WOE/IV 计算器 — 评分卡建模的标准特征筛选方法

WOE (Weight of Evidence):
  衡量特征分箱对好坏样本的区分能力。
  WOE_i = ln(Distribution_Good_i / Distribution_Bad_i)
  正值表示该分箱中好样本更多，负值表示坏样本更多。

IV (Information Value):
  WOE 的加权和，衡量特征整体的预测能力。
  IV = Σ (Distr_Good_i - Distr_Bad_i) * WOE_i

IV 解读标准:
  < 0.02 : 无预测能力 → 剔除
  0.02 - 0.10 : 弱预测能力
  0.10 - 0.30 : 中等预测能力
  0.30 - 0.50 : 强预测能力
  > 0.50 : 可疑（需检查是否过拟合或时间泄漏）

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §5.5
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WOEBin:
    """单个分箱的 WOE 统计"""
    bin_label: str
    good: int
    bad: int
    total: int
    good_rate: float
    bad_rate: float
    woe: float
    iv_contribution: float


@dataclass
class WOEResult:
    """单个特征的 WOE/IV 完整结果"""
    feature: str
    total_iv: float
    iv_level: str           # weak / medium / strong / suspicious
    bins: list[WOEBin] = field(default_factory=list)


class WOECalculator:
    """
    WOE/IV 计算器。

    使用方式:
        calc = WOECalculator(bins=10, method='quantile')
        results = calc.calculate(df, feature_cols, target='label')
        # 筛选 IV >= 0.02 的特征
        selected = [r.feature for r in results if r.total_iv >= 0.02]
    """

    def __init__(self, bins: int = 10, method: str = 'quantile'):
        """
        Args:
            bins: 分箱数量
            method: 分箱方法 — 'quantile' 等频 / 'uniform' 等宽
        """
        self.bins = bins
        self.method = method

    def calculate(
        self, df: pd.DataFrame, feature_cols: list[str],
        target: str = 'label'
    ) -> list[WOEResult]:
        """批量计算多个特征的 WOE/IV"""
        results = []
        for col in feature_cols:
            if col == target:
                continue
            try:
                result = self._calculate_single(df, col, target)
                results.append(result)
            except Exception as e:
                # 特征无法计算 WOE（如全为 null）
                results.append(WOEResult(
                    feature=col, total_iv=0.0, iv_level='weak'
                ))
        return results

    def _calculate_single(
        self, df: pd.DataFrame, feature: str, target: str
    ) -> WOEResult:
        """计算单个特征的 WOE/IV"""
        total_good = (df[target] == 0).sum()
        total_bad = (df[target] == 1).sum()

        if total_good == 0 or total_bad == 0:
            return WOEResult(feature=feature, total_iv=0.0, iv_level='weak')

        # 分箱
        binned = self._bin_feature(df[feature], df[target], target)

        bins = []
        total_iv = 0.0

        for bin_label in sorted(binned['bin'].unique()):
            mask = binned['bin'] == bin_label
            good = (binned[mask][target] == 0).sum()
            bad = (binned[mask][target] == 1).sum()
            n = good + bad

            dist_good = good / total_good if total_good > 0 else 1e-6
            dist_bad = bad / total_bad if total_bad > 0 else 1e-6

            # WOE 平滑处理
            dist_good = max(dist_good, 1e-6)
            dist_bad = max(dist_bad, 1e-6)

            woe = np.log(dist_good / dist_bad)
            iv = (dist_good - dist_bad) * woe

            bins.append(WOEBin(
                bin_label=str(bin_label),
                good=good, bad=bad, total=n,
                good_rate=round(dist_good, 4),
                bad_rate=round(dist_bad, 4),
                woe=round(woe, 4),
                iv_contribution=round(iv, 4),
            ))
            total_iv += iv

        # IV 分级
        iv_level = self._classify_iv(total_iv)

        return WOEResult(
            feature=feature,
            total_iv=round(total_iv, 4),
            iv_level=iv_level,
            bins=bins,
        )

    def _bin_feature(
        self, feature: pd.Series, target: pd.Series, target_col: str = 'target'
    ) -> pd.DataFrame:
        """分箱处理"""
        df = pd.DataFrame({'feature': feature, target_col: target})

        if feature.dtype in ('object', 'category'):
            df['bin'] = feature.astype(str)
        else:
            try:
                if self.method == 'quantile':
                    df['bin'] = pd.qcut(
                        feature, q=self.bins, duplicates='drop',
                        labels=False
                    )
                else:
                    df['bin'] = pd.cut(
                        feature, bins=self.bins, labels=False
                    )
            except ValueError:
                # 无法分箱（如常量特征）
                df['bin'] = 0

        return df.dropna()

    def _classify_iv(self, iv: float) -> str:
        """IV 值分级"""
        if iv < 0.02:
            return 'weak'
        elif iv < 0.10:
            return 'medium'
        elif iv < 0.30:
            return 'strong'
        else:
            return 'suspicious'

    def summary_dataframe(self, results: list[WOEResult]) -> pd.DataFrame:
        """将 WOE/IV 结果导出为 DataFrame"""
        return pd.DataFrame([
            {
                'feature': r.feature,
                'total_iv': r.total_iv,
                'iv_level': r.iv_level,
                'n_bins': len(r.bins),
                'top_bin_woe': max((b.woe for b in r.bins), default=0),
            }
            for r in sorted(results, key=lambda r: r.total_iv, reverse=True)
        ])
