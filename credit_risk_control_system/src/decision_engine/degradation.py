"""
降级策略 — 外部服务超时/不可用时的兜底逻辑

PRODUCTION 背景:
在线推理需要并行调用多个外部服务（特征存储、征信API、多头借贷等）。
任一服务超时不应阻塞整条链路。降级策略定义了每种特征缺失时的默认行为。

设计原则:
1. 每个外部调用有独立超时时间
2. 超时后返回降级值，不抛异常
3. 降级值偏保守（宁可误拒，不可漏过）
4. 降级事件完整记录到决策日志
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class DegradationConfig:
    """降级配置"""
    # 各数据源超时时间（秒）
    feature_fetch_timeout: float = 0.050    # 50ms
    credit_report_timeout: float = 0.200    # 200ms
    multi_head_timeout: float = 0.150       # 150ms
    device_fingerprint_timeout: float = 0.030  # 30ms

    # 缓存有效期
    feature_cache_ttl_seconds: int = 3600      # 1小时
    credit_report_cache_ttl_hours: int = 24    # 24小时


class DegradationPolicy:
    """
    降级策略管理器。

    PRODUCTION NOTE:
    降级默认值的选择非常重要。金融风控中默认值应偏向保守:
    - 多头借贷次数缺失 → 假设为高分位值（宁可保守）
    - 征信分缺失 → 假设为中位数（不能随意拒绝）
    - 设备风险分缺失 → 假设为高分（宁可多审）

    特征降级值需要定期 review（结合业务数据分析降级率与逾期率关系）。
    """

    # ★ PRODUCTION: 降级默认值需基于历史数据分位数定
    # 原则: 对风险判断关键的特征用保守默认值，非关键的用中位数
    FEATURE_DEFAULTS: dict[str, Any] = {
        # 行为特征: 缺失时假设"正常"
        "apply_cnt_7d": 0,
        "apply_cnt_30d": 0,
        "apply_cnt_90d": 0,
        "night_ops_ratio_30d": 0.3,      # 中位数假设
        "avg_session_duration_7d": 60.0,
        "device_change_cnt_30d": 0,

        # 征信衍生: 缺失时用中位数（不能武断拒）
        "credit_score_raw": 600,          # 中等信用分
        "credit_score_normalized": 0.5,
        "debt_to_income_ratio": 0.4,      # ★ 保守: 假设中等负债
        "overdue_cnt_hist": 0,
        "query_cnt_3m": 2,

        # 多头借贷: ★ 关键风险特征，缺失时保守估计
        "multi_head_cnt_7d": 3,           # ★ 保守: 假设有一定多头
        "multi_head_cnt_30d": 5,          # ★ 保守

        # 设备指纹: ★ 反欺诈关键特征
        "device_risk_score": 0.5,         # ★ 保守: 中等风险
        "device_rooted_flag": 0,
        "device_linked_users": 0,
        "sim_change_cnt_30d": 0,

        # 反欺诈
        "fraud_score": 0.3,
    }

    # ★ PRODUCTION: 如果使用缓存的旧特征值，需要标记
    # 缓存值的 TTL 过期后不再使用
    CACHE_TTL_OVERRIDES: dict[str, int] = {
        "multi_head_cnt_7d": 1800,        # 30min（多头数据变化快）
        "credit_score_raw": 86400,        # 24h（征信变化慢）
    }

    @classmethod
    def get_default(cls, feature_name: str) -> Any:
        """
        获取特征的降级默认值。

        Args:
            feature_name: 特征名称

        Returns:
            默认值（从 FEATURE_DEFAULTS 查找，无匹配则返回 0）
        """
        return cls.FEATURE_DEFAULTS.get(feature_name, 0)

    @classmethod
    def get_all_defaults(cls, feature_names: list[str]) -> dict[str, Any]:
        """批量获取降级默认值"""
        return {f: cls.get_default(f) for f in feature_names}

    @classmethod
    def is_degraded_value(cls, feature_name: str, value: Any) -> bool:
        """检查特征值是否为降级默认值（用于日志标记）"""
        return value == cls.get_default(feature_name)
