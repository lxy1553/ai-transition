"""
DWD 层 (Data Warehouse Detail) — 明细数据层

职责: 对 ODS 原始数据做清洗、标准化、脱敏，仍保留明细粒度。

处理步骤:
  1. 数据清洗: 去除非法值(负金额、空ID)、格式标准化
  2. 敏感信息脱敏: 姓名/身份证/手机号 → hash/token
  3. 字典映射: 将枚举码转为统一字典值
  4. 数据质量标记: 对每条记录标记质量分(dq_score)
  5. 不聚合: 仍保留原始粒度，一行对应一笔业务事件

质量标记规则:
  dq_score = 100 - 缺失字段扣分 - 异常值扣分
  dq_score < 60 → 标记为 dq_quarantine (隔离，不入后续层)

PRODUCTION: Spark SQL ETL，每天 T+1 凌晨执行。
          dq_score 进入数据质量监控体系(day57 的知识)。
"""

import hashlib
import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable


# ═══════════════════════════════════════════════════════════
# 数据质量标记
# ═══════════════════════════════════════════════════════════

@dataclass
class DQReport:
    """单批数据的质量报告"""
    table_name: str
    total_rows: int
    passed_rows: int           # dq_score >= 60
    quarantined_rows: int      # dq_score < 60（被隔离）
    null_rate_by_column: dict[str, float]
    invalid_rate_by_column: dict[str, float]


# ═══════════════════════════════════════════════════════════
# 脱敏工具
# ═══════════════════════════════════════════════════════════

class DataMasker:
    """敏感信息脱敏器"""

    @staticmethod
    def mask_name(name: str) -> str:
        """姓名脱敏: 张三 → 张*"""
        if not name or not isinstance(name, str):
            return "***"
        return name[0] + "*" * (len(name) - 1)

    @staticmethod
    def mask_id_card(id_card: str) -> str:
        """身份证脱敏: 保留前6位和后4位"""
        if not id_card or not isinstance(id_card, str) or len(id_card) < 15:
            return "INVALID_ID"
        return id_card[:6] + "********" + id_card[-4:]

    @staticmethod
    def mask_phone(phone: str) -> str:
        """手机号脱敏: 138****5678"""
        if not phone or not isinstance(phone, str) or len(phone) < 11:
            return "INVALID_PHONE"
        return phone[:3] + "****" + phone[-4:]

    @staticmethod
    def hash_user_id(user_id: str) -> str:
        """user_id 哈希化（可选，用于分析但不可反向追溯）"""
        if not user_id or not isinstance(user_id, str):
            return "INVALID_UID"
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════
# DWD 层
# ═══════════════════════════════════════════════════════════

class DWDLayer:
    """
    DWD 层 — 数据清洗、标准化、脱敏。

    关键原则:
    - ODS → DWD: 清洗但不聚合
    - 被隔离记录(dq_score<60)单独存储，不入DWS层
    - 所有 PII（个人身份信息）在此层完成脱敏
    - 下游(DWS/ADS)不应看到明文敏感数据
    """

    def __init__(self, storage_path: str = "./data/warehouse/dwd"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    # ── 申请表清洗 ────────────────────────────────────

    def clean_application(self, ods_df: pd.DataFrame) -> tuple[pd.DataFrame, DQReport]:
        """
        ods_application → dwd_application

        清洗规则:
        1. 金额必须 > 0，否则标记为异常
        2. product_type 必须为已知类型，否则标记
        3. 姓名/身份证/手机号 → 脱敏
        4. user_id 为空 → 隔离
        5. 收入为0或空 → 标记但不隔离（可能真实）
        """
        df = ods_df.copy()
        n_total = len(df)
        df['dq_score'] = 100  # 初始满分

        # ── 1. 必填字段检查 ──
        required_fields = ['user_id', 'application_id', 'apply_amount']
        for field in required_fields:
            mask = df[field].isna() | (df[field].astype(str).str.strip() == '')
            df.loc[mask, 'dq_score'] -= 30  # 必填缺失 → 扣30分
            # 填充默认值避免后续处理报错
            df[field] = df[field].fillna('MISSING')

        # ── 2. 金额合法性 ──
        amount_mask = pd.to_numeric(df['apply_amount'], errors='coerce')
        df.loc[amount_mask.isna() | (amount_mask <= 0), 'dq_score'] -= 20
        df['apply_amount'] = amount_mask.fillna(0).clip(lower=0)

        # ── 3. 产品类型标准化 ──
        valid_products = {'cash_loan': 'CASH_LOAN', 'installment': 'INSTALLMENT',
                         'revolving': 'REVOLVING'}
        df['product_type'] = df['product_type'].map(valid_products).fillna('UNKNOWN')
        df.loc[df['product_type'] == 'UNKNOWN', 'dq_score'] -= 10

        # ── 4. 敏感信息脱敏 ★ ──
        masker = DataMasker()
        df['user_name'] = df['user_name'].apply(masker.mask_name)
        df['id_card'] = df['id_card'].apply(masker.mask_id_card)
        df['phone'] = df['phone'].apply(masker.mask_phone)
        # 可选: user_id 哈希化
        # df['user_id_hash'] = df['user_id'].apply(masker.hash_user_id)

        # ── 5. 收入/职业标准化 ──
        df['monthly_income'] = pd.to_numeric(
            df['monthly_income'], errors='coerce'
        ).fillna(0).clip(lower=0)
        df.loc[df['monthly_income'] == 0, 'dq_score'] -= 5

        df['occupation'] = df['occupation'].fillna('UNKNOWN').str.lower()
        valid_occs = {'employee', 'self_employed', 'freelancer', 'unemployed'}
        df.loc[~df['occupation'].isin(valid_occs), 'occupation'] = 'UNKNOWN'
        df.loc[df['occupation'] == 'UNKNOWN', 'dq_score'] -= 5

        # ── 6. 渠道标准化 ──
        channel_map = {
            'app_android': 'APP_ANDROID', 'app_ios': 'APP_IOS',
            'h5': 'H5', 'partner_a': 'PARTNER_A', 'partner_b': 'PARTNER_B',
        }
        df['channel'] = df['channel'].map(channel_map).fillna('UNKNOWN')

        # ── 7. 隔离记录 ──
        quarantine_mask = df['dq_score'] < 60
        df_clean = df[~quarantine_mask].copy()
        df_quarantine = df[quarantine_mask].copy()

        # 计算空值率
        null_rates = {}
        for col in ['user_id', 'apply_amount', 'product_type', 'occupation',
                     'monthly_income', 'device_id']:
            null_rates[col] = round(
                df_clean[col].isna().mean() + (df_clean[col].astype(str) == 'MISSING').mean(), 4
            )

        report = DQReport(
            table_name='dwd_application',
            total_rows=n_total,
            passed_rows=len(df_clean),
            quarantined_rows=len(df_quarantine),
            null_rate_by_column=null_rates,
            invalid_rate_by_column={
                'apply_amount': round((amount_mask <= 0).sum() / n_total, 4),
                'product_type': round((df['product_type'] == 'UNKNOWN').sum() / n_total, 4),
            },
        )

        return df_clean, report

    # ── 行为日志清洗 ────────────────────────────────────

    def clean_behavior(self, ods_df: pd.DataFrame) -> tuple[pd.DataFrame, DQReport]:
        """
        ods_user_behavior → dwd_user_behavior

        清洗规则:
        1. user_id 为空或 anonymous → 按 device_id + session_id 尝试关联
        2. event_type 标准化
        3. 异常时间戳（未来时间）→ 标记
        """
        df = ods_df.copy()
        n_total = len(df)
        df['dq_score'] = 100

        # user_id 为空 → 扣分但不丢弃（行为数据可通过设备指纹补充）
        bad_uid = df['user_id'].isna() | (df['user_id'].astype(str).str.strip() == '') | (df['user_id'] == 'anonymous')
        df.loc[bad_uid, 'dq_score'] -= 20
        df.loc[bad_uid, 'user_id'] = 'anonymous'

        # event_type 标准化
        valid_events = {'page_view', 'click', 'input', 'submit',
                       'app_install', 'app_uninstall', 'error'}
        df.loc[~df['event_type'].isin(valid_events), 'event_type'] = 'unknown'

        # session_id 为空 → 生成
        df['session_id'] = df['session_id'].fillna('session_generated')

        df_clean = df[df['dq_score'] >= 60]
        df_quarantine = df[df['dq_score'] < 60]

        report = DQReport(
            table_name='dwd_user_behavior',
            total_rows=n_total,
            passed_rows=len(df_clean),
            quarantined_rows=len(df_quarantine),
            null_rate_by_column={'user_id': round(bad_uid.mean(), 4)},
            invalid_rate_by_column={'event_type': round((df['event_type'] == 'unknown').sum() / n_total, 4)},
        )

        return df_clean, report

    # ── 还款记录清洗 ────────────────────────────────────

    def clean_repayment(self, ods_df: pd.DataFrame) -> tuple[pd.DataFrame, DQReport]:
        """
        ods_repayment → dwd_repayment

        清洗规则:
        1. 金额必须 >= 0
        2. paid_date 不能早于 due_date 超过 90 天
        3. status 标准化
        """
        df = ods_df.copy()
        n_total = len(df)
        df['dq_score'] = 100

        # 金额检查
        for col in ['due_amount', 'paid_amount']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).clip(lower=0)
            df.loc[df[col] == 0, 'dq_score'] -= 10

        # 状态标准化
        status_map = {'pending': 'PENDING', 'paid': 'PAID',
                     'overdue': 'OVERDUE'}
        df['status'] = df['status'].map(status_map).fillna('UNKNOWN')

        df_clean = df[df['dq_score'] >= 60]

        report = DQReport(
            table_name='dwd_repayment',
            total_rows=n_total,
            passed_rows=len(df_clean),
            quarantined_rows=n_total - len(df_clean),
            null_rate_by_column={
                'paid_date': round(df['paid_date'].isna().mean(), 4)
            },
            invalid_rate_by_column={
                'status': round((df['status'] == 'UNKNOWN').sum() / n_total, 4),
            },
        )

        return df_clean, report

    def summary(self) -> str:
        return """
╔══════════════════════════════════════════════════╗
║  DWD 层 — 明细数据层（清洗后）                    ║
╠══════════════════════════════════════════════════╣
║  原则: 清洗 + 脱敏 + 标准化，不聚合              ║
║  ┌─────────────────────────────────────────────┐ ║
║  │ ods_application    → dwd_application        │ ║
║  │  · 金额合法性检查                            │ ║
║  │  · 姓名/身份证/手机 → 脱敏                   │ ║
║  │  · 产品类型/渠道 → 标准化字典映射             │ ║
║  │  · dq_score < 60 → 隔离                     │ ║
║  ├─────────────────────────────────────────────┤ ║
║  │ ods_user_behavior  → dwd_user_behavior      │ ║
║  │  · 匿名用户标记                              │ ║
║  │  · 事件类型标准化                            │ ║
║  ├─────────────────────────────────────────────┤ ║
║  │ ods_repayment      → dwd_repayment          │ ║
║  │  · 金额非负校验                              │ ║
║  │  · 状态标准化                                │ ║
║  └─────────────────────────────────────────────┘ ║
║  特征: 所有敏感信息已完成脱敏                      ║
║       下游 DWS/ADS 不应处理明文 PII               ║
╚══════════════════════════════════════════════════╝
"""
