#!/usr/bin/env python3
"""
生成各层数据文件，展示完整数据流转

产出目录结构:
  data/warehouse/
  ├── ods/
  │   ├── dt=2026-07-01/
  │   │   ├── ods_application.parquet
  │   │   ├── ods_user_behavior.parquet
  │   │   └── ods_repayment.parquet
  ├── dwd/
  │   ├── dt=2026-07-01/
  │   │   ├── dwd_application.parquet
  │   │   ├── dwd_user_behavior.parquet
  │   │   ├── dwd_repayment.parquet
  │   │   └── dq_reports.json       ★ 数据质量报告
  ├── dws/
  │   ├── dt=2026-07-01/
  │   │   └── user_risk_feature_wide.parquet
  └── ads/
      ├── dt=2026-07-01/
      │   ├── training_samples.parquet
      │   ├── model_monitor_daily.csv
      │   └── portfolio_analysis.json

用法: python scripts/generate_data_pipeline.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from src.data.warehouse.ods_layer import ODSLayer, ODS_TABLES
from src.data.warehouse.dwd_layer import DWDLayer
from src.data.warehouse.dws_layer import DWSLayer
from src.data.warehouse.ads_layer import ADSLayer


def main():
    # 生成3天数据，模拟真实场景
    dates = ["2026-06-29", "2026-06-30", "2026-07-01"]
    base_path = Path("data/warehouse")

    ods = ODSLayer(str(base_path / "ods"))
    dwd = DWDLayer(str(base_path / "dwd"))
    dws = DWSLayer(str(base_path / "dws"))
    ads = ADSLayer(str(base_path / "ads"))

    all_monitor_dfs = []

    for dt in dates:
        print(f"\n{'='*70}")
        print(f"  📅 处理日期: {dt}")
        print(f"{'='*70}")

        # ─── Layer 1: ODS ───────────────────────────
        ods_dir = base_path / "ods" / f"dt={dt}"
        ods_dir.mkdir(parents=True, exist_ok=True)

        ods_app = ods.load_application(dt, n_records=500)
        ods_behavior = ods.load_behavior(dt, n_records=5000)
        ods_repay = ods.load_repayment(dt)

        ods_app.to_parquet(ods_dir / "ods_application.parquet", index=False)
        ods_behavior.to_parquet(ods_dir / "ods_user_behavior.parquet", index=False)
        ods_repay.to_parquet(ods_dir / "ods_repayment.parquet", index=False)

        print(f"  [ODS] → {ods_dir}")
        print(f"        申请 {len(ods_app)}条 | 行为 {len(ods_behavior)}条 | 还款 {len(ods_repay)}条")

        # ─── Layer 2: DWD ───────────────────────────
        dwd_dir = base_path / "dwd" / f"dt={dt}"
        dwd_dir.mkdir(parents=True, exist_ok=True)

        dwd_app, dq_app = dwd.clean_application(ods_app)
        dwd_behavior, dq_behavior = dwd.clean_behavior(ods_behavior)
        dwd_repay, dq_repay = dwd.clean_repayment(ods_repay)

        dwd_app.to_parquet(dwd_dir / "dwd_application.parquet", index=False)
        dwd_behavior.to_parquet(dwd_dir / "dwd_user_behavior.parquet", index=False)
        dwd_repay.to_parquet(dwd_dir / "dwd_repayment.parquet", index=False)

        # 保存数据质量报告
        dq_reports = {
            "application": {"total": dq_app.total_rows, "passed": dq_app.passed_rows,
                           "quarantined": dq_app.quarantined_rows,
                           "null_rates": dq_app.null_rate_by_column},
            "behavior": {"total": dq_behavior.total_rows, "passed": dq_behavior.passed_rows,
                        "quarantined": dq_behavior.quarantined_rows},
            "repayment": {"total": dq_repay.total_rows, "passed": dq_repay.passed_rows,
                         "quarantined": dq_repay.quarantined_rows},
        }
        with open(dwd_dir / "dq_reports.json", 'w') as f:
            json.dump(dq_reports, f, indent=2, ensure_ascii=False)

        print(f"  [DWD] → {dwd_dir}")
        print(f"        清洗后 {dwd_app['dq_score'].mean():.0f}分(均) | 隔离 {dq_app.quarantined_rows}条 | 脱敏完成 ✓")

        # ─── Layer 3: DWS ───────────────────────────
        dws_dir = base_path / "dws" / f"dt={dt}"
        dws_dir.mkdir(parents=True, exist_ok=True)

        wide_table = dws.build_wide_table(dwd_app, dwd_behavior, dwd_repay, dt)
        wide_table.to_parquet(dws_dir / "user_risk_feature_wide.parquet", index=False)

        print(f"  [DWS] → {dws_dir}")
        print(f"        宽表 {len(wide_table)}用户 × {len(wide_table.columns)}特征")

        # ─── Layer 4: ADS ───────────────────────────
        ads_dir = base_path / "ads" / f"dt={dt}"
        ads_dir.mkdir(parents=True, exist_ok=True)

        # 训练样本
        np.random.seed(hash(dt) % 2**32)
        users = wide_table['user_id'].unique()
        label_df = pd.DataFrame({
            'user_id': users,
            'label': np.random.choice([0, 1], len(users), p=[0.87, 0.13]),
            'label_date': dt,
        })
        training = ads.build_training_samples(wide_table, label_df)
        training.to_parquet(ads_dir / "training_samples.parquet", index=False)

        # 模型监控
        np.random.seed(hash(dt + "_pred") % 2**32)
        n_pred = len(users)
        predictions = pd.DataFrame({
            'user_id': users[:n_pred],
            'score': np.random.normal(615, 80, n_pred).clip(300, 900),
            'default_prob': np.random.beta(2, 8, n_pred),
            'decision': np.random.choice(['APPROVE', 'REJECT', 'MANUAL_REVIEW'], n_pred, p=[0.65, 0.25, 0.10]),
            'credit_limit': np.random.choice([3000, 5000, 10000, 20000, 50000], n_pred),
            'model_name': 'credit_a_card_xgb',
            'model_version': 'v3',
            'latency_ms': np.random.exponential(50, n_pred) + 30,
        })
        monitor = ads.build_model_monitor_daily(predictions, wide_table, dt)
        monitor.to_csv(ads_dir / "model_monitor_daily.csv", index=False)
        all_monitor_dfs.append(monitor)

        # 资产分析
        portfolio = ads.build_portfolio_analysis(predictions, wide_table)
        with open(ads_dir / "portfolio_analysis.json", 'w') as f:
            json.dump(portfolio, f, indent=2, ensure_ascii=False)

        print(f"  [ADS] → {ads_dir}")
        print(f"        训练样本 {len(training)}条 | 坏样本率 {training['label'].mean():.1%}")
        if len(monitor) > 0:
            print(f"        通过率 {monitor['approval_rate'].iloc[0]:.1%} | 平均分 {monitor['avg_score'].iloc[0]:.0f} | 平均延迟 {monitor['avg_latency_ms'].iloc[0]:.0f}ms")

    # ─── 最终汇总 ───────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  📊 数据仓库文件树")
    print(f"{'='*70}")
    _print_tree(base_path)

    print(f"\n{'='*70}")
    print(f"  📈 三日监控趋势")
    print(f"{'='*70}")
    if all_monitor_dfs:
        trend = pd.concat(all_monitor_dfs, ignore_index=True)
        print(trend[['dt', 'total_applications', 'approval_rate', 'avg_score', 'avg_latency_ms']].to_string(index=False))

    print(f"\n  ✅ 数据流转完成！")
    print(f"  产出: {base_path.resolve()}")
    print(f"  运行: python scripts/run_warehouse_etl.py 查看完整ETL日志")

    # ─── 写入表结构到数据目录 ─────────────────────────
    print(f"\n{'='*70}")
    print(f"  📋 写入表结构定义 (_TABLE_SCHEMA.json)")
    print(f"{'='*70}")
    from src.data.schema_registry import SchemaRegistry
    registry = SchemaRegistry()
    written = registry.write_layer_schemas(str(base_path))
    for key, path in written.items():
        print(f"  ✓ {key} → {path}")
    print(f"  共写入 {len(written)} 个 schema 文件\n")


def _print_tree(path, prefix=""):
    """打印目录树"""
    items = sorted(path.iterdir())
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└──" if is_last else "├──"
        if item.is_dir():
            print(f"  {prefix}{connector} {item.name}/")
            _print_tree(item, prefix + ("    " if is_last else "│   "))
        else:
            size = item.stat().st_size
            size_str = f"{size/1024:.1f}KB" if size > 1024 else f"{size}B"
            print(f"  {prefix}{connector} {item.name} ({size_str})")


if __name__ == '__main__':
    main()
