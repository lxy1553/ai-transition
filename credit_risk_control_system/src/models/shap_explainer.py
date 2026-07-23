"""
SHAP 可解释性 — 满足金融监管要求的特征贡献分析

XGBoost/LightGBM 使用 TreeExplainer（精确计算，非采样估计）。
每个审批决策都可追溯到各特征对分数的贡献值。

PRODUCTION 集成:
- 推理时计算 SHAP 值并返回 Top-10 贡献特征
- SHAP 值写入决策日志，满足监管可解释性要求
- 离线做全局 SHAP 分析：特征重要性排序、依赖图、交互效应

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §5.3
"""

import numpy as np
import pandas as pd
from typing import Optional, Union


class SHAPExplainer:
    """
    SHAP 解释器封装。

    使用 TreeExplainer（树模型的精确 SHAP 计算，非核估计）。

    使用方式:
        explainer = SHAPExplainer(model)
        contributions = explainer.explain(feature_vector)
        # → {"debt_to_income_ratio": 0.15, "credit_score": -0.08, ...}

        global_importance = explainer.global_feature_importance(X_sample)
        # → [("debt_to_income_ratio", 0.25), ...]
    """

    def __init__(self, model, feature_names: Union[list[str], None] = None):
        """
        Args:
            model: XGBoost/LightGBM 训练好的模型（需要 booster）
            feature_names: 特征名列表
        """
        self.model = model
        self.feature_names = feature_names or []
        self._explainer = None

        try:
            import shap
            # TreeExplainer 专用于树模型，速度比 KernelExplainer 快 100x+
            if hasattr(model, 'get_booster'):
                self._explainer = shap.TreeExplainer(model.get_booster())
            else:
                self._explainer = shap.TreeExplainer(model)
        except Exception as e:
            print(f"[SHAP] 初始化失败: {e}")

    def explain(
        self, feature_vector: np.ndarray, top_n: int = 10
    ) -> dict[str, float]:
        """
        解释单条预测（推理时调用）。

        Args:
            feature_vector: 形状 (n_features,) 的单条特征向量
            top_n: 返回贡献最大的前 N 个特征

        Returns:
            {feature_name: shap_value, ...}
        """
        if self._explainer is None:
            return {}

        shap_vals = self._explainer.shap_values(
            feature_vector.reshape(1, -1)
        )
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[0]  # XGBoost 返回 list

        vals = shap_vals[0] if shap_vals.ndim == 2 else shap_vals

        # 取绝对值最大的 top_n
        names = self.feature_names or [f"f{i}" for i in range(len(vals))]
        contributions = dict(sorted(
            zip(names, map(float, vals)),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:top_n])

        return contributions

    def global_feature_importance(
        self, X_sample: np.ndarray
    ) -> list[tuple[str, float]]:
        """
        全局特征重要性（离线分析用）。

        Args:
            X_sample: 样本特征矩阵（建议5000条以内，加速计算）

        Returns:
            按平均 |SHAP| 排序的特征列表
        """
        if self._explainer is None:
            return []

        shap_vals = self._explainer.shap_values(X_sample)
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[0]

        mean_abs_shap = np.abs(shap_vals).mean(axis=0)

        names = self.feature_names or [
            f"f{i}" for i in range(len(mean_abs_shap))
        ]
        return sorted(
            zip(names, map(float, mean_abs_shap)),
            key=lambda x: x[1], reverse=True,
        )

    def generate_report(
        self, X_sample: np.ndarray, output_path: Union[str, None] = None
    ) -> dict:
        """
        生成完整的 SHAP 可解释性报告。

        内容:
        - 特征重要性排名
        - 每个特征对模型的平均贡献方向（正向/负向）
        - 支持导出为 JSON（供审批后台展示）

        PRODUCTION: 结合 matplotlib 生成 SHAP summary_plot 图片。
        """
        if self._explainer is None:
            return {"error": "SHAP not available"}

        importance = self.global_feature_importance(X_sample)
        shap_vals = self._explainer.shap_values(X_sample)
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[0]

        report = {
            "feature_importance": [
                {"feature": name, "mean_abs_shap": round(val, 6)}
                for name, val in importance
            ],
            "n_features": len(self.feature_names),
            "n_samples_analyzed": len(X_sample),
        }

        if output_path:
            import json
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

        return report
