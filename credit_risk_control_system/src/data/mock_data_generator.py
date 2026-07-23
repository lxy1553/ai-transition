"""
模拟数据生成器 — 用于本地开发和测试

生成三类模拟数据:
1. 用户申请记录（带标签）
2. 行为埋点流
3. 还款表现数据

PRODUCTION: 这些数据来自真实业务系统（MySQL Binlog + 客户端埋点）。
"""

import hashlib
import random
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd


class MockDataGenerator:
    """模拟数据生成器"""

    def __init__(self, seed: int = 42, n_users: int = 1000):
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        self.n_users = n_users

    def generate_applications(
        self, start_date: str = "2026-01-01",
        end_date: str = "2026-06-30",
        bad_rate: float = 0.12,
    ) -> pd.DataFrame:
        """
        生成模拟申请记录（带标签）。

        Returns:
            DataFrame with columns:
            user_id, application_id, application_time, product_type,
            apply_amount, device_id, label(DPD30+)
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        n_days = (end - start).days

        records = []
        for i in range(self.n_users):
            user_id = f"user_{i:06d}"

            # 每个用户可能有多次申请
            n_apps = self.rng.randint(1, 3)
            for j in range(n_apps):
                app_day = self.rng.randint(0, n_days)
                app_time = start + timedelta(
                    days=app_day,
                    hours=self.rng.randint(8, 22),
                    minutes=self.rng.randint(0, 59),
                )

                is_bad = 1 if self.rng.random() < bad_rate else 0

                records.append({
                    'user_id': user_id,
                    'application_id': f"app_{i:06d}_{j}",
                    'application_time': app_time,
                    'product_type': self.rng.choice(
                        ['cash_loan', 'installment', 'revolving']
                    ),
                    'apply_amount': round(
                        self.rng.choice([1000, 3000, 5000, 10000, 20000, 50000]),
                        2
                    ),
                    'device_id': f"device_{int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16) % 10000:04d}",
                    'label': is_bad,
                })

        return pd.DataFrame(records)

    def generate_behavior_events(
        self, n_events: int = 50000
    ) -> pd.DataFrame:
        """生成模拟行为埋点流"""
        events = []
        event_types = ['page_view', 'click', 'input', 'submit', 'decision_result']
        weights = [0.4, 0.25, 0.2, 0.1, 0.05]

        for _ in range(n_events):
            user_idx = self.rng.randint(0, self.n_users - 1)
            ts = datetime(2026, 1, 1) + timedelta(
                days=self.rng.randint(0, 180),
                hours=self.rng.randint(0, 23),
                minutes=self.rng.randint(0, 59),
                seconds=self.rng.randint(0, 59),
            )

            events.append({
                'user_id': f"user_{user_idx:06d}",
                'event_type': self.rng.choices(event_types, weights=weights)[0],
                'event_time': ts,
                'device_id': f"device_{user_idx % 10000:04d}",
                'session_id': f"session_{self.rng.randint(0, 20000)}",
            })

        return pd.DataFrame(events)

    def generate_repayment_records(self) -> pd.DataFrame:
        """生成模拟还款表现数据"""
        apps = self.generate_applications()
        records = []

        for _, app in apps.iterrows():
            if app['label'] == 1:
                # 坏样本: DPD 从 0 逐渐上升
                max_dpd = self.rng.choice([30, 45, 60, 90])
                for day in range(0, 90, 30):
                    records.append({
                        'application_id': app['application_id'],
                        'obs_date': app['application_time'] + timedelta(days=day),
                        'days_past_due': min(max_dpd, day),
                        'outstanding_balance': round(
                            app['apply_amount'] * (1 - day / 120), 2
                        ) if day <= 60 else app['apply_amount'],
                    })
            else:
                # 好样本: 正常还款
                for day in range(0, 90, 30):
                    records.append({
                        'application_id': app['application_id'],
                        'obs_date': app['application_time'] + timedelta(days=day),
                        'days_past_due': 0,
                        'outstanding_balance': round(
                            app['apply_amount'] * max(0, (90 - day) / 90), 2
                        ),
                    })

        return pd.DataFrame(records)
