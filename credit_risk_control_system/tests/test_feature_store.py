"""特征平台测试"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import pytest

from src.feature_store import pit_join
from src.feature_store.registry import FeatureRegistry
from src.feature_store.online_store import OnlineFeatureStore, MemoryBackend
from src.feature_store.pit_join import PointInTimeJoin


class TestFeatureRegistry:
    """特征注册中心测试"""

    def test_load_from_yaml(self):
        registry = FeatureRegistry("config/features/feature_defs.yaml")
        assert registry.feature_count > 0

        feat = registry.get("age")
        assert feat is not None
        assert feat.type == "int"
        assert feat.category == "basic_profile"

    def test_get_by_category(self):
        registry = FeatureRegistry("config/features/feature_defs.yaml")
        behavior_features = registry.get_by_category("behavior")
        assert len(behavior_features) > 0
        assert all(f.category == "behavior" for f in behavior_features)

    def test_feature_names(self):
        registry = FeatureRegistry("config/features/feature_defs.yaml")
        names = registry.feature_names
        assert "age" in names
        assert "debt_to_income_ratio" in names


class TestOnlineFeatureStore:
    """在线特征存储测试"""

    def test_memory_backend(self):
        backend = MemoryBackend()
        backend.set("test:key", "42", ttl=3600)
        assert backend.get("test:key") == "42"

    def test_memory_backend_ttl(self):
        backend = MemoryBackend()
        backend.set("test:key", "value", ttl=0)  # 立即过期
        assert backend.get("test:key") is None

    def test_online_store_get_features(self):
        store = OnlineFeatureStore(
            feature_names=["apply_cnt_7d", "night_ops_ratio_30d"],
            backend=MemoryBackend(),
        )

        # 预填入特征值
        store.set_features("user_test", {
            "apply_cnt_7d": 3,
            "night_ops_ratio_30d": 0.25,
        })

        snapshot = store.get_online_features("user_test")

        # 同步方法
        import asyncio
        snapshot = asyncio.run(
            store.get_online_features("user_test")
        )

        assert snapshot.features["apply_cnt_7d"] == 3
        assert snapshot.features["night_ops_ratio_30d"] == 0.25

    def test_degradation_on_missing(self):
        store = OnlineFeatureStore(
            feature_names=["apply_cnt_7d", "unknown_feature"],
            backend=MemoryBackend(),
        )
        import asyncio
        snapshot = asyncio.run(
            store.get_online_features("user_new")
        )
        # 缺失特征应使用降级默认值
        assert len(snapshot.missing_features) == 2 or \
               len(snapshot.degraded_features) > 0


class TestPITJoin:
    """Point-in-Time Join 测试"""

    def test_basic_pit_join(self):
        entity_df, feature_df = pit_join.create_demo_pit_samples()
        pit = PointInTimeJoin({'user_behavior': feature_df})
        samples = pit.build_samples(entity_df)

        assert len(samples) == len(entity_df)
        # 应该有特征列
        assert 'user_behavior__apply_cnt_7d' in samples.columns
        # 非空率应该很高
        non_null_rate = samples['user_behavior__apply_cnt_7d'].notna().mean()
        assert non_null_rate > 0.5
