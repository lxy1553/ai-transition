"""Feature Store - 特征平台

核心能力:
1. Feature Registry: 特征定义与元数据管理
2. Online Store: 在线特征服务（低延迟 Redis 查询）
3. Offline Store: 离线特征存储（Iceberg/Parquet）
4. Point-in-Time Join: 防止时间泄漏的样本构建

PRODUCTION 选型:
- 本模块自研简化版（学习用途）
- 生产环境推荐 Feast (feast.dev) 作为特征平台
- 关键能力：离线/在线一致性、PIT Join、特征血缘
"""

from src.feature_store.registry import FeatureRegistry
from src.feature_store.online_store import OnlineFeatureStore
from src.feature_store.offline_store import OfflineFeatureStore
from src.feature_store.pit_join import PointInTimeJoin

__all__ = [
    "FeatureRegistry",
    "OnlineFeatureStore",
    "OfflineFeatureStore",
    "PointInTimeJoin",
]
