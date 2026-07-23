#!/usr/bin/env python3
"""
模型训练脚本 — 端到端训练流程演示

用法:
    python scripts/train_model.py                               # 使用模拟数据训练
    python scripts/train_model.py --from-warehouse               # 从数据仓库 ADS 层加载
    python scripts/train_model.py --from-warehouse --model lightgbm

流程:
    1. 加载数据（模拟生成 / 数据仓库 ADS 层）
    2. WOE/IV 特征筛选
    3. 时间切分（OOT 验证）
    4. XGBoost / LightGBM 训练
    5. 模型评估 + 保存
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from src.data.mock_data_generator import MockDataGenerator
from src.feature_store.offline_store import OfflineFeatureStore
from src.models.woe_iv import WOECalculator
from src.models.trainer import ModelTrainer


def load_from_warehouse(warehouse_path: str = "data/warehouse") -> pd.DataFrame:
    """从数据仓库 ADS 层加载训练样本"""
    base = Path(warehouse_path) / "ads"
    if not base.exists():
        raise FileNotFoundError(f"ADS 数据目录不存在: {base.resolve()}\n"
                                f"请先运行: python scripts/generate_data_pipeline.py")

    samples = []
    for dt_dir in sorted(base.iterdir()):
        f = dt_dir / "training_samples.parquet"
        if f.exists():
            df = pd.read_parquet(f)
            print(f"  加载 {dt_dir.name}: {len(df)} 条, 坏样本率 {df['label'].mean():.2%}")
            samples.append(df)

    if not samples:
        raise FileNotFoundError(f"未找到 training_samples.parquet 文件")

    all_df = pd.concat(samples, ignore_index=True)
    print(f"  合并总计: {len(all_df)} 条, 坏样本率 {all_df['label'].mean():.2%}")
    return all_df


def load_from_mock(n_samples: int = 5000) -> pd.DataFrame:
    """使用模拟数据生成器"""
    print(f"  生成 {n_samples} 条模拟数据...")
    gen = MockDataGenerator(seed=42, n_users=n_samples)
    apps = gen.generate_applications()

    store = OfflineFeatureStore("./data/offline_features")
    all_features = []
    for dt in apps['application_time'].dt.strftime('%Y-%m-%d').unique():
        day_apps = apps[apps['application_time'].dt.strftime('%Y-%m-%d') == dt]
        features = store.generate_mock_features(
            user_ids=day_apps['user_id'].tolist(), dt=dt
        )
        all_features.append(features)
    features_df = pd.concat(all_features, ignore_index=True)

    from src.data.sample_builder import TrainingSampleBuilder
    builder = TrainingSampleBuilder()
    samples = builder.build(apps, features_df)
    return samples


def main():
    parser = argparse.ArgumentParser(description='信贷风控模型训练')
    parser.add_argument('--from-warehouse', action='store_true',
                        help='从数据仓库 ADS 层加载训练数据')
    parser.add_argument('--warehouse-path', default='data/warehouse',
                        help='数据仓库路径（配合 --from-warehouse 使用）')
    parser.add_argument('--model', default='xgboost',
                        choices=['xgboost', 'lightgbm'],
                        help='模型类型')
    parser.add_argument('--n-samples', type=int, default=5000,
                        help='模拟数据样本数（非 warehouse 模式）')
    parser.add_argument('--mlflow-uri', default=None,
                        help='MLflow Tracking URI')
    args = parser.parse_args()

    # ── Step 1: 准备数据 ──
    print("\n[1/5] 准备数据...")
    if args.from_warehouse:
        print(f"  数据来源: 数据仓库 ADS 层 ({args.warehouse_path})")
        samples = load_from_warehouse(args.warehouse_path)
    else:
        print("  数据来源: 模拟数据生成器")
        samples = load_from_mock(args.n_samples)

    print(f"  样本数: {len(samples)}, 坏样本率: {samples['label'].mean():.2%}")

    # ── Step 2: WOE/IV 特征筛选 ──
    print("\n[2/5] WOE/IV 特征筛选...")

    exclude_cols = {'user_id', 'application_id', 'application_time',
                    'product_type', 'device_id', 'label', 'dt', 'label_date'}
    feature_cols = [
        c for c in samples.columns
        if c not in exclude_cols
        and samples[c].dtype in ('int64', 'float64', 'int32', 'float32')
    ]
    print(f"  候选特征: {len(feature_cols)} 个")

    woe_calc = WOECalculator(bins=10, method='quantile')
    iv_results = woe_calc.calculate(samples, feature_cols)
    iv_df = woe_calc.summary_dataframe(iv_results)

    # 按 IV 降序选择特征
    sorted_results = sorted(iv_results, key=lambda r: r.total_iv, reverse=True)
    selected = [
        r.feature for r in sorted_results
        if r.total_iv >= 0.005 and r.iv_level != 'suspicious'
    ]
    if len(selected) < 8:
        selected = [r.feature for r in sorted_results[:8]]
        print(f"  ⚠ IV 高阈值下特征不足，降级使用 Top-{len(selected)} 特征")

    print(f"  IV 筛选: {len(feature_cols)} → {len(selected)} 个特征")
    print(iv_df.head(15).to_string(index=False))

    # ── Step 3: 数据切分 ──
    print("\n[3/5] 数据切分（OOT 验证）...")
    X = samples[selected].fillna(0).values.astype(np.float32)
    y = samples['label'].values

    # 按时间切分: 前70%训练，后30% OOT
    split_idx = int(len(X) * 0.7)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"  训练集: {len(X_train)}, 测试集(OOT): {len(X_test)}")
    print(f"  训练集坏样本率: {y_train.mean():.2%}")
    print(f"  测试集坏样本率: {y_test.mean():.2%}")

    # ── Step 4: 训练模型 ──
    print(f"\n[4/5] 训练 {args.model.upper()} 模型...")
    trainer = ModelTrainer(
        experiment_name="credit_risk_a_card",
        tracking_uri=args.mlflow_uri,
        artifact_path="./data/models",
    )

    model_wrapper, eval_report = trainer.train_xgboost(
        X_train=X_train, y_train=y_train,
        X_test=X_test, y_test=y_test,
        feature_names=selected,
    )

    # ── Step 5: 结果 ──
    print("\n[5/5] 训练完成!")
    print(f"\n{'='*60}")
    print(f"  数据来源: {'数据仓库 ADS' if args.from_warehouse else '模拟生成'}")
    print(f"  特征数量: {len(selected)}")
    print(f"  特征名称: {', '.join(selected[:8])}{'...' if len(selected) > 8 else ''}")
    print(f"  模型文件: ./data/models/")
    print(f"{'='*60}")

    if eval_report.passed:
        print("\n✅ 模型满足上线标准，可发布到 Staging")
    else:
        print("\n❌ 模型未满足上线标准，需优化:")
        for f in eval_report.failures:
            print(f"  - {f}")
        if args.from_warehouse and len(samples) < 5000:
            print("\n  💡 提示: 当前训练数据仅 {} 条，建议生成更多数据".format(len(samples)))
        print("  💡 提示: mock 数据 label 为随机生成，真实数据会显著改善模型效果")


if __name__ == '__main__':
    main()
