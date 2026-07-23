"""
ODS 层 (Operational Data Store) — 原始数据层

职责: 1:1 镜像业务系统数据，不做任何清洗和转换。

数据来源:
  ┌─────────────────────────────────────────────────────┐
  │ mysql_application     — 用户申请表 (MySQL Binlog)     │
  │ api_credit_report     — 征信报告原始返回 (HTTP日志)    │
  │ sdk_device_fingerprint— 设备指纹上报 (SDK JSON)       │
  │ sdk_user_behavior     — 用户行为埋点 (客户端上报)      │
  │ api_multi_head        — 多头借贷查询结果 (第三方API)   │
  │ mysql_repayment       — 还款计划表 (MySQL Binlog)      │
  └─────────────────────────────────────────────────────┘

PRODUCTION: 数据通过 Kafka Connect / Flink CDC 实时接入，
          存入 Iceberg ODS 层（按 dt 分区）。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass


# ═══════════════════════════════════════════════════════════
# ODS 层数据模型（镜像业务表结构）
# ═══════════════════════════════════════════════════════════

@dataclass
class ODSTable:
    """ODS 表元数据"""
    name: str               # 表名
    source_system: str      # 来源系统
    ingest_method: str      # 接入方式: binlog / api_log / sdk / file
    partition_key: str = "dt"   # 分区键
    description: str = ""


# 定义 ODS 层的所有表
ODS_TABLES = {
    "ods_application": ODSTable(
        name="ods_application",
        source_system="mysql_credit_core",
        ingest_method="binlog",
        description="用户贷款申请表（来自核心业务库 Binlog）",
    ),
    "ods_credit_report": ODSTable(
        name="ods_credit_report",
        source_system="api_credit_bureau",
        ingest_method="api_log",
        description="征信报告原始 JSON 返回",
    ),
    "ods_device_fingerprint": ODSTable(
        name="ods_device_fingerprint",
        source_system="sdk_device_fp",
        ingest_method="sdk",
        description="设备指纹 SDK 上报原始数据",
    ),
    "ods_user_behavior": ODSTable(
        name="ods_user_behavior",
        source_system="sdk_analytics",
        ingest_method="sdk",
        description="用户行为埋点流（点击、填表、提交等）",
    ),
    "ods_multi_head": ODSTable(
        name="ods_multi_head",
        source_system="api_third_party",
        ingest_method="api_log",
        description="多头借贷第三方查询结果",
    ),
    "ods_repayment": ODSTable(
        name="ods_repayment",
        source_system="mysql_credit_core",
        ingest_method="binlog",
        description="还款计划与还款记录表",
    ),
}


class ODSLayer:
    """
    ODS 层 — 原始数据接入与管理。

    关键约束: ODS 层不做任何数据清洗、过滤、转换。
    所有数据保持与源系统完全一致（包括脏数据）。

    PRODUCTION 实现:
      Flink CDC / Kafka Connect → Kafka → Iceberg ODS 表
    """

    def __init__(self, storage_path: str = "./data/warehouse/ods"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.tables = ODS_TABLES

    # ── 各表的模拟数据生成方法 ──

    def load_application(self, dt: str,
                         n_records: int = 1000) -> pd.DataFrame:
        """
        ods_application — 用户申请表（原始字段，含脏数据）。

        字段: user_id, application_id, apply_amount, product_type,
              user_name(明文★需在DWD层脱敏), id_card(明文★需脱敏),
              phone(明文★需脱敏), occupation, monthly_income, education,
              city, ip_address, device_id, channel, apply_time, dt
        """
        np.random.seed(hash(dt) % 2**32)

        # ★ 故意制造脏数据，体现 ODS 层"不处理"的原则
        raw = pd.DataFrame({
            'user_id': [f"user_{i:06d}" for i in range(n_records)],
            'application_id': [f"app_{i:06d}" for i in range(n_records)],
            'apply_amount': np.random.choice(
                [1000, 3000, 5000, 10000, 20000, 50000, -1000, 0, None],  # ★脏数据
                n_records, p=[0.15, 0.2, 0.2, 0.15, 0.1, 0.05, 0.03, 0.02, 0.1]
            ),
            'product_type': np.random.choice(
                ['cash_loan', 'installment', 'revolving', 'UNKNOWN_TYPE', None],  # ★脏数据
                n_records, p=[0.35, 0.3, 0.25, 0.05, 0.05]
            ),
            'user_name': [_fake_name(i) for i in range(n_records)],     # ★明文
            'id_card': [f"{np.random.randint(100000,999999)}19{np.random.randint(60,99):02d}{np.random.randint(1,13):02d}{np.random.randint(1,29):02d}{np.random.randint(1000,9999)}" for _ in range(n_records)],  # ★明文身份证
            'phone': [f"138{np.random.randint(10000000,99999999)}" for _ in range(n_records)],  # ★明文手机号
            'occupation': np.random.choice(
                ['employee', 'self_employed', 'freelancer', 'unemployed', '', None],
                n_records
            ),
            'monthly_income': np.random.choice(
                [3000, 5000, 8000, 12000, 20000, 35000, 0, None],
                n_records, p=[0.15, 0.2, 0.2, 0.15, 0.1, 0.05, 0.05, 0.1]
            ),
            'education': np.random.choice(
                ['high_school', 'bachelor', 'master', 'phd', '', None],
                n_records
            ),
            'city': np.random.choice(
                ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '', None],
                n_records
            ),
            'ip_address': [f"192.168.{np.random.randint(1,255)}.{np.random.randint(1,255)}" for _ in range(n_records)],
            'device_id': np.random.choice(
                [f"device_{i:04d}" for i in range(200)] + [None, '', 'INVALID_DEVICE'],
                n_records
            ),
            'channel': np.random.choice(
                ['app_android', 'app_ios', 'h5', 'partner_a', 'partner_b', 'UNKNOWN'],
                n_records
            ),
            'apply_time': [
                datetime.strptime(dt, '%Y-%m-%d')
                + timedelta(hours=np.random.randint(0, 24),
                           minutes=np.random.randint(0, 60))
                for _ in range(n_records)
            ],
            'dt': dt,
        })
        return raw

    def load_behavior(self, dt: str,
                      n_records: int = 10000) -> pd.DataFrame:
        """
        ods_user_behavior — 用户行为埋点流（原始上报）。

        字段: user_id, event_type, event_detail(JSON string),
              device_id, session_id, page_url, referrer,
              ip, user_agent, event_time, dt
        """
        np.random.seed(hash(dt) % 2**32)
        event_types = ['page_view', 'click', 'input', 'submit',
                       'app_install', 'app_uninstall', 'error']

        return pd.DataFrame({
            'user_id': np.random.choice(
                [f"user_{i:06d}" for i in range(500)] + ['', None, 'anonymous'],
                n_records
            ),
            'event_type': np.random.choice(
                event_types, n_records,
                p=[0.35, 0.25, 0.15, 0.1, 0.05, 0.03, 0.07]
            ),
            'event_detail': [_random_json() for _ in range(n_records)],
            'device_id': np.random.choice(
                [f"device_{i:04d}" for i in range(200)] + [None],
                n_records
            ),
            'session_id': np.random.choice(
                [f"sess_{i:06d}" for i in range(3000)] + [None],
                n_records
            ),
            'page_url': np.random.choice(
                ['/apply', '/products', '/mine', '/help', '/repay', ''],
                n_records
            ),
            'ip': [f"{np.random.randint(1,255)}.{np.random.randint(0,255)}.{np.random.randint(0,255)}.{np.random.randint(1,255)}" for _ in range(n_records)],
            'event_time': [
                datetime.strptime(dt, '%Y-%m-%d')
                + timedelta(hours=np.random.randint(0, 24),
                           minutes=np.random.randint(0, 60),
                           seconds=np.random.randint(0, 60))
                for _ in range(n_records)
            ],
            'dt': dt,
        })

    def load_repayment(self, dt: str) -> pd.DataFrame:
        """ods_repayment — 还款记录"""
        np.random.seed(hash(dt) % 2**32)
        n = 500
        return pd.DataFrame({
            'repayment_id': [f"repay_{i:06d}" for i in range(n)],
            'application_id': np.random.choice(
                [f"app_{i:06d}" for i in range(200)], n
            ),
            'user_id': np.random.choice(
                [f"user_{i:06d}" for i in range(200)], n
            ),
            'due_date': [datetime.strptime(dt, '%Y-%m-%d') + timedelta(days=np.random.randint(-30, 60)) for _ in range(n)],
            'paid_date': [datetime.strptime(dt, '%Y-%m-%d') + timedelta(days=np.random.randint(-30, 60)) if np.random.random() > 0.1 else None for _ in range(n)],
            'due_amount': np.random.choice([500, 1000, 2000, 5000, 0, None], n, p=[0.2, 0.3, 0.2, 0.15, 0.05, 0.1]),
            'paid_amount': np.random.choice([500, 1000, 2000, 5000, 0, None], n),
            'status': np.random.choice(['pending', 'paid', 'overdue', 'ERROR_STATUS'], n),
            'dt': dt,
        })

    def summary(self) -> str:
        """打印 ODS 层概要"""
        lines = ["\n╔══════════════════════════════════════════════╗",
                 "║  ODS 层 — 原始数据层                         ║",
                 "╠══════════════════════════════════════════════╣",
                 "║  原则: 1:1 镜像源系统，不做清洗               ║",
                 "║  特点: 含脏数据、明文敏感信息、无数据质量校验  ║",
                 "╠══════════════════════════════════════════════╣"]
        for t in self.tables.values():
            lines.append(f"║  {t.name:30s} ← {t.source_system:25s} ║")
        lines.append("╚══════════════════════════════════════════════╝")
        return "\n".join(lines)


def _fake_name(seed: int) -> str:
    surnames = ['张', '李', '王', '赵', '陈', '杨', '黄', '周', '吴', '徐']
    names = ['伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '洋', '勇']
    rng = np.random.RandomState(seed)
    return rng.choice(surnames) + rng.choice(names)


def _random_json() -> str:
    """模拟事件详情的 JSON 字符串"""
    import json
    return json.dumps({
        'x': np.random.randint(0, 375),
        'y': np.random.randint(0, 812),
        'duration_ms': np.random.randint(50, 30000),
    })
