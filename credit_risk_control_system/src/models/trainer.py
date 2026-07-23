"""
模型训练器 — XGBoost/LightGBM 训练 + MLflow 管理

PRODUCTION 训练流程:
1. Feast PIT Join 构建样本（防时间泄漏）
2. WOE/IV 特征筛选（去除无预测力特征）
3. 时间切分（OOT验证: Out-of-Time）
4. XGBoost 训练（带早停和类别权重）
5. 模型评估（KS/AUC/Gini/PSI/Lift）
6. MLflow 注册 → Staging 阶段
7. 人工审批 → Promotion to Production

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §5.5
"""

import os
import json
import pickle
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split

from src.models.evaluator import ModelEvaluator, EvalReport
from src.models.woe_iv import WOECalculator



class ModelWrapper:
    """
    模型包装器 — 给推理引擎使用的统一接口。

    封装了 XGBoost/评分卡模型，提供 predict_proba 和 explain 方法。
    推理引擎不关心底层是 XGBoost 还是 LightGBM。
    """

    def __init__(self, name: str, version: str,
                 booster, feature_names: list[str],
                 shap_explainer=None):
        self.name = name
        self.version = version
        self.booster = booster
        self.feature_names = feature_names
        self._shap = shap_explainer

    def predict_proba(self, feature_vector: np.ndarray) -> float:
        """返回违约概率 [0, 1]"""
        dmatrix = xgb.DMatrix(
            feature_vector.reshape(1, -1),
            feature_names=self.feature_names,
        )
        prob = float(self.booster.predict(dmatrix)[0])
        return prob

    def explain(self, feature_vector: np.ndarray,
                top_n: int = 10) -> dict[str, float]:
        """
        返回 Top-N 特征的 SHAP 贡献值。

        生产环境: shap.TreeExplainer 已预先初始化并缓存。
        """
        if self._shap is None:
            return {}

        shap_vals = self._shap.shap_values(
            xgb.DMatrix(feature_vector.reshape(1, -1),
                       feature_names=self.feature_names)
        )[0]

        contributions = dict(sorted(
            zip(self.feature_names, map(float, shap_vals)),
            key=lambda x: abs(x[1]), reverse=True
        )[:top_n])

        return contributions


class ModelTrainer:
    """
    模型训练器。

    使用方式:
        trainer = ModelTrainer(experiment_name="credit_a_card")
        X, y, feature_names = load_data(...)
        model = trainer.train_xgboost(
            X_train, y_train, X_test, y_test, feature_names
        )
    """

    def __init__(
        self,
        experiment_name: str = "credit_risk_a_card",
        tracking_uri: Optional[str] = None,
        artifact_path: str = "./data/models",
    ):
        """
        Args:
            experiment_name: MLflow 实验名称
            tracking_uri: MLflow 追踪服务器地址
                PRODUCTION: http://mlflow-server:5000
                DEV: file://./data/mlflow
            artifact_path: 模型本地保存路径（无 MLflow 时）
        """
        self.experiment_name = experiment_name
        self.artifact_path = Path(artifact_path)
        self.artifact_path.mkdir(parents=True, exist_ok=True)
        self.evaluator = ModelEvaluator()

        self._mlflow_available = False
        if tracking_uri:
            try:
                import mlflow
                mlflow.set_tracking_uri(tracking_uri)
                mlflow.set_experiment(experiment_name)
                self._mlflow_available = True
                self._mlflow = mlflow
                print(f"[ModelTrainer] MLflow 已连接: {tracking_uri}")
            except Exception:
                print("[ModelTrainer] MLflow 不可用，使用本地文件管理模型")

    def train_xgboost(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        feature_names: list[str],
        params: Optional[dict] = None,
        run_name: Optional[str] = None,
    ) -> tuple[ModelWrapper, EvalReport]:
        """
        训练 XGBoost 二分类模型。

        Args:
            X_train/y_train: 训练集
            X_test/y_test: 测试集（OOT验证集）
            feature_names: 特征名列表（用于 SHAP 解释）
            params: XGBoost 超参（None 则使用默认值）
            run_name: MLflow run 名称

        Returns:
            (模型包装器, 评估报告)
        """
        default_params = {
            'objective': 'binary:logistic',
            'eval_metric': 'auc',
            'max_depth': 5,
            'learning_rate': 0.05,
            'n_estimators': 500,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 10,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'random_state': 42,
            'early_stopping_rounds': 50,
        }

        # 样本不平衡: scale_pos_weight
        n_pos = (y_train == 1).sum()
        n_neg = (y_train == 0).sum()
        default_params['scale_pos_weight'] = n_neg / n_pos if n_pos > 0 else 1

        params = {**default_params, **(params or {})}
        run_name = run_name or f"xgb_{datetime.now():%Y%m%d_%H%M}"

        print(f"\n{'='*60}")
        print(f"[ModelTrainer] 开始训练 XGBoost")
        print(f"[ModelTrainer] 训练集: {len(X_train)} 样本, "
              f"坏样本率: {y_train.mean():.2%}")
        print(f"[ModelTrainer] 测试集: {len(X_test)} 样本, "
              f"坏样本率: {y_test.mean():.2%}")
        print(f"[ModelTrainer] 特征数: {len(feature_names)}")
        print(f"[ModelTrainer] Scale Pos Weight: {params['scale_pos_weight']:.2f}")
        print(f"{'='*60}")

        # 训练
        model = xgb.XGBClassifier(**{
            k: v for k, v in params.items()
            if k not in ('early_stopping_rounds',)
        })
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        # 预测
        y_train_pred = model.predict_proba(X_train)[:, 1]
        y_test_pred = model.predict_proba(X_test)[:, 1]

        # 评估
        report = self.evaluator.evaluate(
            y_train, y_train_pred, y_test, y_test_pred
        )

        # 初始化 SHAP 解释器（生产环境预加载，随模型一起返回）
        try:
            import shap
            shap_explainer = shap.TreeExplainer(model)
        except Exception:
            print("[ModelTrainer] SHAP 初始化失败（可忽略）")
            shap_explainer = None

        wrapper = ModelWrapper(
            name="credit_a_card_xgb",
            version=run_name,
            booster=model.get_booster(),
            feature_names=feature_names,
            shap_explainer=shap_explainer,
        )

        # ── 保存模型 ──
        self._save_model(wrapper, report, params, run_name)

        # ── 打印报告 ──
        self._print_report(report)

        return wrapper, report

    def _save_model(self, wrapper: ModelWrapper, report: EvalReport,
                    params: dict, run_name: str) -> None:
        """保存模型到 MLflow 或本地文件"""
        if self._mlflow_available:
            with self._mlflow.start_run(run_name=run_name):
                self._mlflow.log_params(params)
                self._mlflow.log_metrics({
                    'auc_test': report.auc_test,
                    'ks_test': report.ks_test,
                    'gini_test': report.gini_test,
                    'psi': report.psi_train_test,
                    'overfit_gap': report.overfit_gap,
                })
                self._mlflow.xgboost.log_model(
                    wrapper.booster, "model",
                    registered_model_name="credit_a_card_xgb",
                )
                print(f"[ModelTrainer] 模型已注册到 MLflow: {run_name}")
        else:
            # 本地保存
            model_path = self.artifact_path / f"{run_name}"
            model_path.mkdir(exist_ok=True)
            wrapper.booster.save_model(str(model_path / "model.json"))
            with open(model_path / "feature_names.json", 'w') as f:
                json.dump(wrapper.feature_names, f)
            with open(model_path / "eval_report.json", 'w') as f:
                json.dump({
                    'auc_test': report.auc_test,
                    'ks_test': report.ks_test,
                    'gini_test': report.gini_test,
                    'psi': report.psi_train_test,
                }, f, indent=2)
            print(f"[ModelTrainer] 模型已保存到: {model_path}")

    def _print_report(self, report: EvalReport):
        """格式化打印评估报告"""
        icon = "✅" if report.passed else "❌"
        print(f"\n{'='*60}")
        print(f"  模型评估报告  {icon} {'PASSED' if report.passed else 'FAILED'}")
        print(f"{'='*60}")
        print(f"  AUC (train):  {report.auc_train:.4f}")
        print(f"  AUC (test):   {report.auc_test:.4f}")
        print(f"  KS (test):    {report.ks_test:.4f}  (min: {ModelEvaluator.MIN_KS})")
        print(f"  Gini (test):  {report.gini_test:.4f}")
        print(f"  PSI:          {report.psi_train_test:.4f}  (max: {ModelEvaluator.MAX_PSI})")
        print(f"  Overfit Gap:  {report.overfit_gap:.4f}  (max: {ModelEvaluator.MAX_OVERFIT_GAP})")

        if report.failures:
            for f in report.failures:
                print(f"  ⚠ {f}")

        # Lift 表（只打印首尾）
        print(f"\n  Lift 分析（分箱坏账率）:")
        for row in report.lift_table:
            bar = "█" * max(1, int(row['lift'] * 10))
            print(f"    Bin {row['bin']:2d}: "
                  f"bad_rate={row['bad_rate']:.2%}  "
                  f"lift={row['lift']:.2f}  {bar}")
        print(f"{'='*60}\n")


# ═══════════════════════════════════════════════════════════
# 简化 Model Registry（无 MLflow 时用）
# ═══════════════════════════════════════════════════════════

class LocalModelRegistry:
    """本地模型注册中心（DEV fallback，生产用 MLflow Model Registry）"""

    def __init__(self, models_dir: str = "./data/models"):
        self.models_dir = Path(models_dir)
        self._active_models: dict[str, ModelWrapper] = {}

    def get_model(self, model_name: str, version: str = "production") -> ModelWrapper:
        """根据名称和版本加载模型"""
        cache_key = f"{model_name}:{version}"
        if cache_key in self._active_models:
            return self._active_models[cache_key]

        # 查找模型文件
        if version == "production":
            # 找最新的模型
            model_dirs = sorted(self.models_dir.glob("xgb_*"))
            if not model_dirs:
                raise FileNotFoundError(f"无可用模型: {self.models_dir}")
            model_path = model_dirs[-1]
        else:
            model_path = self.models_dir / version

        model_file = model_path / "model.json"
        feature_file = model_path / "feature_names.json"

        if not model_file.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_file}")

        booster = xgb.Booster()
        booster.load_model(str(model_file))

        with open(feature_file) as f:
            feature_names = json.load(f)

        wrapper = ModelWrapper(
            name=model_name,
            version=str(model_path.name),
            booster=booster,
            feature_names=feature_names,
        )

        self._active_models[cache_key] = wrapper
        return wrapper
