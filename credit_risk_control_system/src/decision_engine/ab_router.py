"""
A/B 测试流量路由器 — 冠军/挑战者模型在线分流

工作原理:
1. 基于 user_id 的 MD5 哈希将用户分入 10000 个桶 (0-9999)
2. 每个模型分配一定范围的桶（weight * 100）
3. 同一用户始终路由到同一模型（哈希一致性）
4. 比例可热更新（通过配置中心下发，或修改YAML后reload）

PRODUCTION 分层抽样:
对于需要按细分维度（城市、收入层）做分层A/B的场景，
在哈希前拼接 stratum 值: hash(f"{stratum}:{user_id}")
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

import yaml


@dataclass
class BucketConfig:
    """分桶配置"""
    name: str               # 桶名称: champion, challenger_v2
    model: str              # 模型注册名: credit_a_card_xgb
    version: str            # 模型版本: 3, staging, production
    weight: int             # 流量权重 (百分制，总和=100)
    bucket_range_start: int = 0   # 桶区间起始 [start, end)
    bucket_range_end: int = 0


class ABTrafficRouter:
    """
    冠军/挑战者 A/B 测试路由器。

    使用方式:
        router = ABTrafficRouter(config_path="config/settings.yaml")
        bucket = router.route("user_12345")
        # bucket = BucketConfig(name="champion", model="credit_a_card_xgb", ...)

    PRODUCTION 扩展:
    1. 与配置中心 (Nacos/Apollo) 集成，实现比例动态调整
    2. 支持更细分流策略（按城市分层、按时间段）
    3. A/B 效果统计自动汇总，联动 MLflow 自动 promote
    """

    TOTAL_BUCKETS = 10000  # 总分桶数

    def __init__(self, config_path: Union[str, Path, None] = None,
                 buckets: Union[list[dict], None] = None):
        """
        Args:
            config_path: 系统配置文件路径（从 settings.yaml 读取 ab_test 配置）
            buckets: 或直接传入分桶配置列表
        """
        self.buckets: list[BucketConfig] = []

        if config_path:
            self._load_from_config(config_path)
        elif buckets:
            self._load_from_list(buckets)
        else:
            # 默认: 全部走冠军模型
            self.buckets = [BucketConfig(
                name="default_champion",
                model="credit_a_card_xgb",
                version="production",
                weight=100,
                bucket_range_start=0,
                bucket_range_end=self.TOTAL_BUCKETS,
            )]

        self._validate_weights()

    def _load_from_config(self, config_path: Union[str, Path]) -> None:
        """从 YAML 配置文件加载"""
        config = yaml.safe_load(Path(config_path).read_text())
        ab_config = config.get('model', {}).get('ab_test', {})
        self._load_from_list(ab_config.get('buckets', []))

    def _load_from_list(self, buckets: list[dict]) -> None:
        """从分桶列表加载并计算区间"""
        cumulative = 0
        for b in buckets:
            weight = b.get('weight', 0)
            bucket_range = int(weight * self.TOTAL_BUCKETS / 100)
            self.buckets.append(BucketConfig(
                name=b['name'],
                model=b['model'],
                version=b['version'],
                weight=weight,
                bucket_range_start=cumulative,
                bucket_range_end=cumulative + bucket_range,
            ))
            cumulative += bucket_range

    def _validate_weights(self) -> None:
        """验证权重总和 <= 100"""
        total = sum(b.weight for b in self.buckets)
        if total > 100:
            raise ValueError(
                f"A/B 测试分桶权重总和 {total}% > 100%"
            )

    def route(self, user_id: str, stratum: Union[str, None] = None) -> BucketConfig:
        """
        根据 user_id 哈希确定路由目标。

        算法: MD5(user_id) → hex → int % 10000 → 查找所在区间

        Args:
            user_id: 用户唯一标识
            stratum: 分层键（可选，如城市编码）
                     用于分层抽样式 A/B 测试

        Returns:
            命中的分桶配置
        """
        # 分层抽样
        hash_input = f"{stratum}:{user_id}" if stratum else user_id

        # MD5 哈希 → 整数 → 取模
        hash_hex = hashlib.md5(hash_input.encode()).hexdigest()
        hash_val = int(hash_hex, 16) % self.TOTAL_BUCKETS

        # 查找所在区间
        for bucket in self.buckets:
            if bucket.bucket_range_start <= hash_val < bucket.bucket_range_end:
                return bucket

        # 兜底: 返回第一个桶（冠军模型）
        return self.buckets[0]

    def get_bucket_distribution(self) -> dict[str, dict]:
        """获取分桶分布（用于监控和验证）"""
        return {
            b.name: {
                "model": b.model,
                "version": b.version,
                "weight_pct": b.weight,
                "bucket_range": f"[{b.bucket_range_start}, {b.bucket_range_end})",
                "expected_traffic_pct": round(
                    (b.bucket_range_end - b.bucket_range_start)
                    / self.TOTAL_BUCKETS * 100, 1
                ),
            }
            for b in self.buckets
        }
