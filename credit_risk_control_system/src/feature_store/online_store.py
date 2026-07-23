"""
在线特征存储 — 低延迟特征查询（<5ms）

PRODUCTION: Redis Cluster（3主3从，Sentinel高可用）
  架构: feature:{user_id}:{feature_name} → value
  示例: feature:user_12345:apply_cnt_7d → "3"
  TTL: 根据特征类型设置（行为7天、征信30天、基础画像无过期）

DEV: fakeredis（内存模拟，零依赖启动）或直接使用本地Redis
  切换方式: 环境变量 FEATURE_STORE_TYPE=redis|memory

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §5.4
"""

import os
import time
from dataclasses import dataclass
from typing import Any, Optional, Union

import numpy as np

from src.decision_engine.degradation import DegradationPolicy


# ═══════════════════════════════════════════════════════════
# 存储后端抽象
# ═══════════════════════════════════════════════════════════

class OnlineStoreBackend:
    """在线存储后端抽象基类"""

    def get(self, key: str) -> Optional[str]:
        raise NotImplementedError

    def mget(self, keys: list[str]) -> list[Optional[str]]:
        raise NotImplementedError

    def set(self, key: str, value: str, ttl: int = 604800) -> None:
        raise NotImplementedError

    def mset(self, kv_pairs: dict[str, str], ttl: int = 604800) -> None:
        raise NotImplementedError


class RedisBackend(OnlineStoreBackend):
    """
    ★ PRODUCTION: 真实 Redis 后端。

    需要: pip install redis
    启动: docker run -p 6379:6379 redis:7-alpine
    """

    def __init__(self, host="localhost", port=6379, db=0, cluster_mode=False):
        try:
            import redis
            if cluster_mode:
                # Redis Cluster 模式
                self.client = redis.RedisCluster(
                    host=host, port=port, decode_responses=True
                )
            else:
                self.client = redis.Redis(
                    host=host, port=port, db=db, decode_responses=True
                )
            self.client.ping()
            print(f"[OnlineStore] Redis 已连接 {host}:{port}")
        except ImportError:
            raise ImportError(
                "需要安装 redis-py: pip install redis\n"
                "或切换为 memory 模式: FEATURE_STORE_TYPE=memory"
            )
        except Exception as e:
            raise ConnectionError(
                f"Redis 连接失败 {host}:{port}: {e}\n"
                "确保 Redis 已启动: docker run -p 6379:6379 redis:7-alpine\n"
                "或切换为 memory 模式: FEATURE_STORE_TYPE=memory"
            )

    def get(self, key: str) -> Optional[str]:
        return self.client.get(key)

    def mget(self, keys: list[str]) -> list[Optional[str]]:
        if not keys:
            return []
        return self.client.mget(keys)

    def set(self, key: str, value: str, ttl: int = 604800) -> None:
        self.client.setex(key, ttl, value)

    def mset(self, kv_pairs: dict[str, str], ttl: int = 604800) -> None:
        pipe = self.client.pipeline()
        for key, value in kv_pairs.items():
            pipe.setex(key, ttl, value)
        pipe.execute()


class MemoryBackend(OnlineStoreBackend):
    """
    ★ DEV: 内存字典后端（无外部依赖，适合本地开发和单元测试）。

    注意: 重启后数据丢失，仅用于开发环境。
    """

    def __init__(self):
        self._store: dict[str, tuple[str, float]] = {}  # key → (value, expire_at)
        print("[OnlineStore] DEV模式: 使用内存存储")

    def get(self, key: str) -> Optional[str]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expire_at = entry
        if time.time() > expire_at:
            del self._store[key]
            return None
        return value

    def mget(self, keys: list[str]) -> list[Optional[str]]:
        return [self.get(k) for k in keys]

    def set(self, key: str, value: str, ttl: int = 604800) -> None:
        self._store[key] = (value, time.time() + ttl)

    def mset(self, kv_pairs: dict[str, str], ttl: int = 604800) -> None:
        expire_at = time.time() + ttl
        for key, value in kv_pairs.items():
            self._store[key] = (value, expire_at)


# ═══════════════════════════════════════════════════════════
# 在线特征服务
# ═══════════════════════════════════════════════════════════

class OnlineFeatureStore:
    """
    在线特征服务 — 为推理引擎提供低延迟特征查询。

    使用方式:
        store = OnlineFeatureStore(feature_names=["apply_cnt_7d", ...])
        features = await store.get_online_features("user_12345")
        # → {"apply_cnt_7d": 3, "night_ops_ratio_30d": 0.2, ...}

    缓存策略:
    1. 本地进程内存缓存（L1，Python dict + TTL）
    2. Redis（L2，网络调用但仍是亚毫秒级）
    3. 降级默认值（L3，超时或不可用时）

    PRODUCTION 扩展:
    - gRPC 替代 Redis 直连（统一特征服务接口）
    - 增加本地 Caffeine/Guava Cache 等价物（cachetools）
    - 特征批量预取（根据 user_id 批量拉取最近活跃特征）
    """

    # Redis Key 模板
    KEY_TEMPLATE = "feature:{user_id}:{feature_name}"

    def __init__(
        self,
        feature_names: list[str],
        backend: Union[OnlineStoreBackend, None] = None,
        cache_size: int = 10000,
        cache_ttl: int = 300,  # 本地缓存5分钟
    ):
        self.FEATURE_NAMES = feature_names

        # 选择后端
        if backend:
            self.backend = backend
        else:
            store_type = os.environ.get('FEATURE_STORE_TYPE', 'memory')
            if store_type == 'redis':
                self.backend = RedisBackend(
                    host=os.environ.get('REDIS_HOST', 'localhost'),
                    port=int(os.environ.get('REDIS_PORT', '6379')),
                )
            else:
                self.backend = MemoryBackend()

        # L1 本地缓存
        try:
            from cachetools import TTLCache
            self._local_cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)
        except ImportError:
            self._local_cache = {}  # 降级为普通dict（无TTL）

    async def get_online_features(self, user_id: str) -> 'FeatureSnapshot':
        """
        获取用户的最新在线特征值。

        PRODUCTION: 此方法通常为 async（虽然 Redis 是同步调用，
        但配合 asyncio.to_thread 或 aioredis 可异步化）。

        Args:
            user_id: 用户唯一标识

        Returns:
            FeatureSnapshot 包含特征字典 + 元信息
        """
        from src.decision_engine.inference_pipeline import FeatureSnapshot

        t_start = time.perf_counter()
        features = {}
        missing = []
        degraded = []

        # 构建 Redis keys
        keys = [
            self.KEY_TEMPLATE.format(user_id=user_id, feature_name=fn)
            for fn in self.FEATURE_NAMES
        ]

        # 批量查询 Redis（一次网络往返）
        raw_values = self.backend.mget(keys)

        for fn, raw_val in zip(self.FEATURE_NAMES, raw_values):
            if raw_val is None:
                # 检查 L1 缓存
                cache_key = f"{user_id}:{fn}"
                cached = self._local_cache.get(cache_key)
                if cached is not None:
                    features[fn] = cached
                    degraded.append(fn)
                else:
                    # L3 降级：使用默认值
                    features[fn] = DegradationPolicy.get_default(fn)
                    missing.append(fn)
            else:
                features[fn] = self._deserialize(fn, raw_val)

        latency_ms = (time.perf_counter() - t_start) * 1000

        return FeatureSnapshot(
            user_id=user_id,
            features=features,
            feature_version="online_v1",
            missing_features=missing,
            degraded_features=degraded,
            fetch_latency_ms=latency_ms,
        )

    def get_cached_features(self, user_id: str) -> Union[dict[str, Any], None]:
        """从 L1 缓存获取特征（超时降级时使用）"""
        cached = {}
        for fn in self.FEATURE_NAMES:
            val = self._local_cache.get(f"{user_id}:{fn}")
            if val is not None:
                cached[fn] = val

        return cached if cached else None

    def set_features(self, user_id: str, features: dict[str, Any]) -> None:
        """
        写入特征（由 Flink/Spark 离线任务调用）。

        PRODUCTION: 此方法由离线特征工程任务调用，更新 Redis。
        """
        kv_pairs = {}
        for fn, value in features.items():
            key = self.KEY_TEMPLATE.format(user_id=user_id, feature_name=fn)
            kv_pairs[key] = str(value)

            # 同时更新 L1 缓存
            self._local_cache[f"{user_id}:{fn}"] = value

        self.backend.mset(kv_pairs)

    def _deserialize(self, feature_name: str, raw: str) -> Any:
        """将 Redis 返回的字符串转为正确的 Python 类型"""
        # 简单类型推断（生产环境应根据 FeatureRegistry 的类型信息）
        try:
            if '.' in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            if raw.lower() in ('true', 'false'):
                return raw.lower() == 'true'
            return raw
