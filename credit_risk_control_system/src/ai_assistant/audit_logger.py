"""
审计日志 —— 把每一次问答完整记录下来

小白类比：这一步是"装行车记录仪"。
每一次用户问答，系统都把完整过程记下来：谁问的、问的什么、生成的 SQL 是什么、
查出了什么结果、花了多久。出了问题时，能像回放录像一样追溯。

为什么审计日志这么重要？
  1. 合规：金融场景要求"每一次数据访问都可追溯"
  2. 排查问题：用户说"你给的数据不对"，你能翻日志看当时到底查了什么
  3. 监控：分析日志能发现"哪个指标被问得最多""哪类问题最容易出错"

为什么用 Kafka（异步消息队列），而不是直接写数据库？
  关键：日志不能拖慢主流程。
  如果每次问答都要等"日志写进数据库"才返回，用户体验会变差。
  正确做法是"异步"——把日志丢进 Kafka 就立刻返回，由消费者慢慢去落库。
  这就是"解耦"：主流程不被日志拖累。

关于脱敏（重要）：
  日志里不能存明文敏感信息（用户手机号、身份证号）。
  真实生产会在写日志前做脱敏。这里留了个钩子。
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuditEvent:
    """一次问答的完整审计记录"""
    trace_id: str           # 全链路追踪 ID（贯穿整条链路）
    user_id: str            # 提问用户
    query: str              # 用户原话
    intent: str             # 识别出的意图
    rewritten: dict         # 改写后的结构化查询
    sql: str                # 最终执行的 SQL
    result: Any             # 查询结果（脱敏后）
    latency_ms: float       # 总耗时
    timestamp: float        # 时间戳

    def to_dict(self) -> dict:
        """转成字典，方便序列化成 JSON 发到 Kafka。"""
        return {
            "trace_id": self.trace_id,
            "user_id": self._mask_user(self.user_id),  # 脱敏：用户ID打码
            "query": self.query,
            "intent": self.intent,
            "rewritten": self.rewritten,
            "sql": self.sql,
            "result": self.result,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def _mask_user(user_id: str) -> str:
        """用户 ID 脱敏：只保留前 3 位，其余打码。"""
        if len(user_id) <= 3:
            return user_id
        return user_id[:3] + "*" * (len(user_id) - 3)


class AuditLogger:
    """
    审计日志器。

    职责：把问答过程异步写入日志（生产用 Kafka，学习版用内存 list 模拟）。
    """

    def __init__(self):
        # 学习版：用内存 list 存日志，方便观察。真实生产：换成 KafkaProducer
        self._logs: list[dict] = []

    def log(self, event: AuditEvent) -> None:
        """
        记录一次问答事件。

        生产级：这里是异步的（发 Kafka 消息），不阻塞主流程。
        学习版：同步加到 list 里，方便你直接查看。
        """
        self._logs.append(event.to_dict())

        # 真实生产：这段代码会变成异步发 Kafka
        # producer.send("ai_qa.audit", json.dumps(event.to_dict()))
        # 注意：这里用 json.dumps 是安全的，因为 to_dict 已经做了脱敏

    def get_all(self) -> list[dict]:
        """查看所有日志（学习版辅助方法，方便调试）。"""
        return self._logs
