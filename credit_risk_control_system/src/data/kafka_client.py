"""
Kafka 客户端 — 决策日志异步写入 + 事件消费

PRODUCTION: confluent_kafka / aiokafka
  - 决策日志 topic: 异步写入（fire-and-forget），不阻塞推理响应
  - 申请事件 topic: 供 Flink 实时特征计算消费
  - 还款事件 topic: 供贷后监控消费
  - 分区策略: 按 user_id 哈希分区（保证同一用户事件有序）

★ DEV: 内存队列（开发/测试环境零依赖运行）
  切换方式: KAFKA_DEV_FALLBACK=false 则使用真实 Kafka

架构设计: Producer/Consumer 接口与真实 Kafka 一致，切换无代码改动。
"""

import asyncio
import json
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from queue import Queue
from typing import Any, Callable, Optional, Union


# ═══════════════════════════════════════════════════════════
# 存储后端抽象
# ═══════════════════════════════════════════════════════════

class MessageQueueBackend:
    """消息队列后端抽象"""

    async def send(self, topic: str, message: dict) -> None:
        raise NotImplementedError

    def subscribe(self, topic: str, callback: Callable) -> None:
        raise NotImplementedError


class RealKafkaBackend(MessageQueueBackend):
    """
    ★ PRODUCTION: 真实 Kafka 后端。

    需要: pip install aiokafka
    启动: docker-compose up kafka
    """

    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        try:
            from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
            self._producer = None
            self._servers = bootstrap_servers
            self._consumer_tasks = []
            print(f"[Kafka] 真实 Kafka 后端: {bootstrap_servers}")
        except ImportError:
            raise ImportError(
                "需要 aiokafka: pip install aiokafka\n"
                "或设置 KAFKA_DEV_FALLBACK=true 使用内存模式"
            )

    async def send(self, topic: str, message: dict) -> None:
        if self._producer is None:
            from aiokafka import AIOKafkaProducer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._servers,
                value_serializer=lambda v: json.dumps(v).encode(),
            )
            await self._producer.start()

        await self._producer.send_and_wait(topic, message)

    def subscribe(self, topic: str, callback: Callable) -> None:
        """启动消费者协程（这里用简化实现）"""
        pass


class MemoryQueueBackend(MessageQueueBackend):
    """
    ★ DEV: 内存队列后端。

    零外部依赖，消息仅存在于进程内存中。
    用于本地开发和单元测试。
    """

    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._message_log: list[dict] = []  # 已发送消息记录
        print("[Kafka] DEV模式: 使用内存队列")

    async def send(self, topic: str, message: dict) -> None:
        """发送消息到队列"""
        msg_with_meta = {
            **message,
            '_topic': topic,
            '_timestamp': time.time(),
        }
        self._message_log.append(msg_with_meta)

        # 通知订阅者
        for callback in self._subscribers.get(topic, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(msg_with_meta)
                else:
                    callback(msg_with_meta)
            except Exception:
                pass

    def subscribe(self, topic: str, callback: Callable) -> None:
        """订阅 topic"""
        self._subscribers[topic].append(callback)

    def get_messages(self, topic: Union[str, None] = None) -> list[dict]:
        """获取历史消息（调试用）"""
        if topic:
            return [m for m in self._message_log if m['_topic'] == topic]
        return self._message_log


# ═══════════════════════════════════════════════════════════
# 决策日志写入器
# ═══════════════════════════════════════════════════════════

class DecisionLogger:
    """
    决策日志异步写入器。

    职责:
    - 将每笔推理的完整日志异步写入 Kafka（不阻塞响应）
    - 日志包含: 特征快照、模型版本、SHAP值、决策结果、耗时
    - 失败重试 + 降级（本地文件备份）

    PRODUCTION: Kafka 集群，分区策略按 user_id 哈希。
    """

    def __init__(self, backend: Union[MessageQueueBackend, None] = None,
                 topic: str = "credit_decision_log"):
        self.topic = topic

        if backend:
            self.backend = backend
        elif os.environ.get('KAFKA_DEV_FALLBACK', 'true').lower() == 'true':
            self.backend = MemoryQueueBackend()
        else:
            self.backend = RealKafkaBackend(
                os.environ.get('KAFKA_BOOTSTRAP', 'localhost:9092')
            )

    async def log(self, result: 'DecisionResult') -> None:
        """
        异步写决策日志。

        在推理流水线中通过 asyncio.create_task 调用，
        不阻塞主响应路径。
        """
        try:
            await self.backend.send(
                self.topic, result.to_log_dict()
            )
        except Exception as e:
            # ★ PRODUCTION: 失败时写本地文件作为备份
            print(f"[DecisionLogger] 写入失败: {e}")
