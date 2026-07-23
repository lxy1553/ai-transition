"""Models - 模型训练、评估与注册

核心能力:
1. WOE/IV 特征筛选（评分卡标准方法）
2. XGBoost/LightGBM 模型训练
3. 评分卡概率→分数映射
4. KS/AUC/Gini/PSI/Lift 模型评估
5. SHAP 模型可解释性
6. MLflow 模型版本管理
"""

from src.models.trainer import ModelTrainer, ModelWrapper
from src.models.evaluator import ModelEvaluator
from src.models.woe_iv import WOECalculator
from src.models.scorecard import ScorecardMapper
from src.models.shap_explainer import SHAPExplainer

__all__ = [
    "ModelTrainer",
    "ModelWrapper",
    "ModelEvaluator",
    "WOECalculator",
    "ScorecardMapper",
    "SHAPExplainer",
]
