#!/usr/bin/env python3
"""
监控演示 — 特征PSI监控 + 模型熔断演示

用法:
    python scripts/run_monitoring.py                    # PSI 每日检测演示
    python scripts/run_monitoring.py --circuit-breaker   # 熔断器演示
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from src.monitoring.psi_monitor import FeaturePSIMonitor
from src.monitoring.circuit_breaker import ModelCircuitBreaker, BreakerState


def demo_psi_monitor():
    """演示 PSI 漂移检测"""
    print("\n" + "=" * 60)
    print("  特征 PSI 漂移监控演示")
    print("=" * 60)

    # 模拟训练集特征分布（基准）
    np.random.seed(42)
    train_df = pd.DataFrame({
        'apply_cnt_7d': np.random.poisson(2, 1000),
        'night_ops_ratio_30d': np.random.beta(2, 5, 1000),
        'debt_to_income_ratio': np.random.beta(3, 5, 1000),
        'device_risk_score': np.random.beta(2, 6, 1000),
    })

    monitor = FeaturePSIMonitor()
    monitor.build_baseline_from_df(train_df, train_df.columns.tolist())
    print("\n基准分布（训练集）:")
    for feat, stats in monitor.baseline.items():
        print(f"  {feat}: mean={stats['mean']:.3f}, std={stats['std']:.3f}, "
              f"null_rate={stats['null_rate']:.1%}")

    # 模拟"特征漂移"后的生产数据
    print("\n" + "-" * 40)
    print("场景1: 无漂移（正常）")
    prod_df_normal = pd.DataFrame({
        'apply_cnt_7d': np.random.poisson(2, 1000),     # 同分布
        'night_ops_ratio_30d': np.random.beta(2, 5, 1000),
        'debt_to_income_ratio': np.random.beta(3, 5, 1000),
        'device_risk_score': np.random.beta(2, 6, 1000),
    })
    report = monitor.run_daily_check(prod_df_normal)
    print(f"  PSI 超标: {report.features_above_warning}")
    for feat, psi in report.psi_details.items():
        print(f"    {feat}: PSI={psi:.4f}")

    print("\n" + "-" * 40)
    print("场景2: 显著漂移（多头借贷激增）")
    prod_df_drift = pd.DataFrame({
        'apply_cnt_7d': np.random.poisson(8, 1000),     # ★ 从 2 变为 8
        'night_ops_ratio_30d': np.random.beta(5, 2, 1000),  # ★ 分布反转
        'debt_to_income_ratio': np.random.beta(7, 3, 1000),  # ★ 整体升高
        'device_risk_score': np.random.beta(2, 6, 1000),
    })
    report = monitor.run_daily_check(prod_df_drift)
    print(f"  PSI 超出 0.10: {report.features_above_warning}")
    print(f"  PSI 超出 0.25: {report.features_above_critical}")
    for feat, psi in report.psi_details.items():
        level = "🔴" if psi > 0.25 else ("🟡" if psi > 0.1 else "🟢")
        print(f"    {level} {feat}: PSI={psi:.4f}")

    if report.alerts:
        print("\n  ⚠ 告警:")
        for alert in report.alerts:
            print(f"    [{alert.level}] {alert.message}")


def demo_circuit_breaker():
    """演示模型熔断"""
    print("\n" + "=" * 60)
    print("  模型熔断器演示")
    print("=" * 60)

    def on_break():
        print("  🔴 熔断触发！切换到备用模型/纯规则模式")

    def on_recover():
        print("  🟢 熔断恢复！切回主模型")

    breaker = ModelCircuitBreaker(
        delinquency_spike_threshold=0.30,
        on_break=on_break,
        on_recover=on_recover,
    )

    print(f"\n初始状态: {breaker.state.value}")

    # 场景1: 正常
    print("\n[场景1] 指标正常...")
    state = breaker.check(
        delinquency_change_ratio=0.05,  # 逾期率微涨5%
        psi_critical_count=0,
        error_rate=0.01,
    )
    print(f"  状态: {state.value}")

    # 场景2: 逾期率突增 40%
    print("\n[场景2] 逾期率突增 40%...")
    state = breaker.check(
        delinquency_change_ratio=0.40,  # ★ 突增40%
        psi_critical_count=2,
        error_rate=0.03,
    )
    print(f"  状态: {state.value}")

    # 场景3: 再次检查，仍在熔断
    print("\n[场景3] 继续检查...")
    state = breaker.check(
        delinquency_change_ratio=0.35,
        psi_critical_count=1,
        error_rate=0.02,
    )
    print(f"  状态: {state.value}")

    # 场景4: 模拟冷却期后试探
    print("\n[场景4] 模拟冷却期后的试探...")
    breaker.last_state_change = (
        breaker.last_state_change - breaker.recovery_seconds - 1
    )
    state = breaker.check(
        delinquency_change_ratio=0.10,
        psi_critical_count=0,
        error_rate=0.01,
    )
    print(f"  状态: {state.value}")

    # 场景5: 再次检查，指标正常 → 恢复
    print("\n[场景5] 指标持续正常 → 恢复...")
    state = breaker.check(
        delinquency_change_ratio=0.05,
        psi_critical_count=0,
        error_rate=0.01,
    )
    print(f"  状态: {state.value}")

    # 打印历史
    print("\n熔断历史:")
    for event in breaker.get_history():
        print(f"  {event['timestamp']} | {event['from']} → {event['to']}: "
              f"{event['reason']}")


def main():
    parser = argparse.ArgumentParser(description='风控监控演示')
    parser.add_argument('--circuit-breaker', action='store_true',
                        help='运行熔断器演示')
    args = parser.parse_args()

    if args.circuit_breaker:
        demo_circuit_breaker()
    else:
        demo_psi_monitor()


if __name__ == '__main__':
    main()
