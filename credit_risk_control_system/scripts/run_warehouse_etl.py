#!/usr/bin/env python3
"""
数据仓库 ETL 全流程演示 — ODS → DWD → DWS → ADS

用法: python scripts/run_warehouse_etl.py

这是数仓四层分层的可运行演示:
  ODS: 原始数据（含脏数据、明文敏感信息）
  DWD: 清洗 + 脱敏 + 质量标记
  DWS: 按用户聚合，构建风险特征宽表
  ADS: 生成训练样本、监控日报、BI数据

PRODUCTION:
  ODS→DWD: Spark SQL T+1 凌晨执行
  DWD→DWS: Spark SQL T+1 凌晨执行
  DWS→ADS: Spark SQL T+1 凌晨执行
  实时链路: Flink SQL 每5分钟增量更新
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from src.data.warehouse.ods_layer import ODSLayer
from src.data.warehouse.dwd_layer import DWDLayer
from src.data.warehouse.dws_layer import DWSLayer
from src.data.warehouse.ads_layer import ADSLayer


def main():
    dt = "2026-07-01"
    print(f"\n{'='*70}")
    print(f"  信贷风控数据仓库 ETL 全流程演示")
    print(f"  日期: {dt}")
    print(f"  链路: ODS → DWD → DWS → ADS")
    print(f"{'='*70}")

    # ══════════════════════════════════════════════════
    # Layer 1: ODS — 原始数据层
    # ══════════════════════════════════════════════════
    ods = ODSLayer()
    print(ods.summary())

    print("\n[Step 1/4] ODS 层 — 加载原始数据...")
    ods_app = ods.load_application(dt, n_records=500)
    ods_behavior = ods.load_behavior(dt, n_records=5000)
    ods_repay = ods.load_repayment(dt)

    print(f"  ods_application: {len(ods_app)} 条")
    print(f"  ods_user_behavior: {len(ods_behavior)} 条")
    print(f"  ods_repayment: {len(ods_repay)} 条")

    # 展示 ODS 的脏数据
    print(f"\n  ★ ODS 脏数据示例:")
    bad_amounts = ods_app[ods_app['apply_amount'].isna() | (ods_app['apply_amount'] <= 0)]
    print(f"    异常金额记录: {len(bad_amounts)}/{len(ods_app)}")
    print(f"    明文身份证示例: {ods_app['id_card'].iloc[0]}")  # 明文！
    print(f"    明文手机号示例: {ods_app['phone'].iloc[0]}")    # 明文！

    # ══════════════════════════════════════════════════
    # Layer 2: DWD — 明细数据层（清洗 + 脱敏）
    # ══════════════════════════════════════════════════
    dwd = DWDLayer()
    print(dwd.summary())

    print("\n[Step 2/4] DWD 层 — 清洗 + 脱敏...")
    dwd_app, dq_app = dwd.clean_application(ods_app)
    dwd_behavior, dq_behavior = dwd.clean_behavior(ods_behavior)
    dwd_repay, dq_repay = dwd.clean_repayment(ods_repay)

    print(f"  dwd_application: {len(dwd_app)} 条 (隔离 {dq_app.quarantined_rows} 条)")
    print(f"  dwd_user_behavior: {len(dwd_behavior)} 条 (隔离 {dq_behavior.quarantined_rows} 条)")
    print(f"  dwd_repayment: {len(dwd_repay)} 条 (隔离 {dq_repay.quarantined_rows} 条)")

    # 展示脱敏效果
    print(f"\n  ★ DWD 脱敏后:")
    print(f"    身份证: {ods_app['id_card'].iloc[0]} → {dwd_app['id_card'].iloc[0] if len(dwd_app) > 0 else 'N/A'}")
    print(f"    手机号: {ods_app['phone'].iloc[0]} → {dwd_app['phone'].iloc[0] if len(dwd_app) > 0 else 'N/A'}")

    # 数据质量报告
    print(f"\n  数据质量报告:")
    for col, rate in dq_app.null_rate_by_column.items():
        print(f"    {col:25s} 空值率: {rate:.2%}")

    # ══════════════════════════════════════════════════
    # Layer 3: DWS — 汇总数据层（用户风险特征宽表）
    # ══════════════════════════════════════════════════
    dws = DWSLayer()
    print(dws.summary())

    print("\n[Step 3/4] DWS 层 — 构建用户风险特征宽表...")
    wide_table = dws.build_wide_table(dwd_app, dwd_behavior, dwd_repay, dt)

    # 展示宽表结构
    print(f"\n  ★ DWS 宽表列 ({len(wide_table.columns)} 列):")
    for i, col in enumerate(wide_table.columns):
        if i > 0 and i % 4 == 0:
            print()
        print(f"    {col:30s}", end="")
    print()

    # 展示特征示例
    if len(wide_table) > 0:
        numeric_cols = wide_table.select_dtypes(include=[np.number]).columns[:8]
        print(f"\n  特征示例 (前3个用户):")
        print(wide_table[['user_id'] + list(numeric_cols)].head(3).to_string(index=False))

    # ══════════════════════════════════════════════════
    # Layer 4: ADS — 应用数据层
    # ══════════════════════════════════════════════════
    ads = ADSLayer()
    print(ads.summary())

    print("\n[Step 4/4] ADS 层 — 生成应用数据集...")

    # 4a. 构建训练样本（模拟 label）
    np.random.seed(42)
    label_df = pd.DataFrame({
        'user_id': wide_table['user_id'].unique(),
        'label': np.random.choice([0, 1], len(wide_table['user_id'].unique()),
                                   p=[0.88, 0.12]),
    })
    training_samples = ads.build_training_samples(wide_table, label_df)
    print(f"  ads_training_samples: {len(training_samples)} 条, "
          f"坏样本率={training_samples['label'].mean():.2%}")

    # 4b. 模型监控日报
    mock_predictions = pd.DataFrame({
        'user_id': wide_table['user_id'].unique()[:200],
        'score': np.random.normal(620, 80, 200).clip(300, 900),
        'decision': np.random.choice(
            ['APPROVE', 'REJECT', 'MANUAL_REVIEW'], 200,
            p=[0.65, 0.25, 0.10]
        ),
        'credit_limit': np.random.choice([3000, 5000, 10000, 30000], 200),
    })
    monitor = ads.build_model_monitor_daily(mock_predictions, wide_table, dt)
    if len(monitor) > 0:
        print(f"\n  ads_model_monitor ({dt}):")
        for col in monitor.columns:
            print(f"    {col}: {monitor[col].iloc[0]}")

    # 4c. 资产组合分析
    portfolio = ads.build_portfolio_analysis(mock_predictions, wide_table)
    print(f"\n  ads_portfolio_analysis:")
    print(f"    总资产: {portfolio['total_portfolio']} 笔")
    print(f"    总敞口: ¥{portfolio['total_credit_exposure']:,.0f}")
    print(f"    评分分布: {portfolio['score_distribution']}")

    # ══════════════════════════════════════════════════
    # 总结
    # ══════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  ETL 全流程完成！")
    print(f"{'='*70}")
    print(f"""
    数据流转总结:

    ODS ({len(ods_app)} 条申请)
     │  含脏数据、明文PII、未校验
     │
     ▼
    DWD ({len(dwd_app)} 条清洗后)
     │  脱敏完成、质量标记、隔离 {dq_app.quarantined_rows} 条
     │
     ▼
    DWS ({len(wide_table)} 用户 × {len(wide_table.columns)} 特征)
     │  5大特征类: 基础画像 + 行为 + 还款 + 征信 + 设备
     │
     ▼
    ADS
     ├── 训练样本: {len(training_samples)} 条
     ├── 模型监控: 1 条日报
     └── 资产分析: 组合报告
    """)

    print("✅ 四层数据仓库 ETL 流程演示完成")
    print("   生产环境: ODS→DWD→DWS→ADS 由 Spark SQL 每日 T+1 执行\n")


if __name__ == '__main__':
    main()
