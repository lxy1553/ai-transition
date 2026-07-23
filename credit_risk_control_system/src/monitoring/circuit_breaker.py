"""
模型熔断器 — 逾期率突增时自动切换至备用模型

状态机: CLOSED → OPEN → HALF_OPEN → CLOSED

PRODUCTION 监控源:
- Prometheus 查询实时逾期率指标
- 或从 ClickHouse 查询早期逾期信号（T+15）
- 延迟敏感: 每 5 分钟检查一次

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §5.6
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional


class BreakerState(str, Enum):
    CLOSED = "CLOSED"            # 正常（主模型）
    OPEN = "OPEN"                # 熔断（备用模型/规则）
    HALF_OPEN = "HALF_OPEN"     # 半开（试探性恢复）


@dataclass
class BreakerEvent:
    timestamp: float
    from_state: BreakerState
    to_state: BreakerState
    reason: str


class ModelCircuitBreaker:
    """
    模型熔断器。

    触发条件（任一满足）:
    1. 实时逾期率突增 > 30%（vs 24小时均值）
    2. PSI > 0.25 的特征数 >= 3个
    3. 推理错误率 > 5%

    恢复条件:
    - HALF_OPEN 状态下，10%流量试跑主模型
    - 连续10分钟指标正常 → CLOSED（恢复）
    - 指标仍异常 → OPEN（继续熔断）

    PRODUCTION:
    - 熔断动作: 更新 MLflow Model Registry → promote 备用模型
      或切换为纯规则引擎模式（拒绝率上升但风险可控）
    - 通知: 钉钉 P0 告警 + 值班电话
    """

    def __init__(
        self,
        delinquency_spike_threshold: float = 0.30,
        max_psi_features: int = 3,
        error_rate_threshold: float = 0.05,
        recovery_seconds: float = 600,
        on_break: Optional[Callable] = None,
        on_recover: Optional[Callable] = None,
    ):
        self.delinquency_spike_threshold = delinquency_spike_threshold
        self.max_psi_features = max_psi_features
        self.error_rate_threshold = error_rate_threshold
        self.recovery_seconds = recovery_seconds

        self.state = BreakerState.CLOSED
        self.events: list[BreakerEvent] = []
        self.last_state_change = time.time()

        # 回调函数（由外部注入熔断动作）
        self.on_break = on_break          # 熔断时调用
        self.on_recover = on_recover      # 恢复时调用

    def check(
        self,
        delinquency_change_ratio: float = 0.0,
        psi_critical_count: int = 0,
        error_rate: float = 0.0,
    ) -> BreakerState:
        """
        检查是否需要触发熔断。

        Args:
            delinquency_change_ratio: 逾期率变化比例
            psi_critical_count: PSI > 0.25 的特征数
            error_rate: 推理错误率

        Returns:
            当前状态
        """
        if self.state == BreakerState.CLOSED:
            should_break = (
                delinquency_change_ratio > self.delinquency_spike_threshold
                or psi_critical_count >= self.max_psi_features
                or error_rate > self.error_rate_threshold
            )

            if should_break:
                self._transition(BreakerState.OPEN, (
                    f"逾期率变化={delinquency_change_ratio:.2%}, "
                    f"PSI超标={psi_critical_count}, "
                    f"错误率={error_rate:.2%}"
                ))
                if self.on_break:
                    self.on_break()

        elif self.state == BreakerState.OPEN:
            # 冷却期后进入 HALF_OPEN
            if time.time() - self.last_state_change > self.recovery_seconds:
                self._transition(
                    BreakerState.HALF_OPEN, "冷却期结束，试探性恢复"
                )

        elif self.state == BreakerState.HALF_OPEN:
            # 试探期：指标正常 → 恢复
            all_normal = (
                delinquency_change_ratio <= self.delinquency_spike_threshold / 2
                and psi_critical_count == 0
                and error_rate <= self.error_rate_threshold / 2
            )
            if all_normal:
                self._transition(BreakerState.CLOSED, "指标恢复正常")
                if self.on_recover:
                    self.on_recover()
            elif delinquency_change_ratio > self.delinquency_spike_threshold:
                # 指标仍异常 → 继续熔断
                self._transition(BreakerState.OPEN, "试探期指标仍异常，继续熔断")

        return self.state

    def _transition(self, to_state: BreakerState, reason: str) -> None:
        """状态转换"""
        event = BreakerEvent(
            timestamp=time.time(),
            from_state=self.state,
            to_state=to_state,
            reason=reason,
        )
        self.events.append(event)
        self.state = to_state
        self.last_state_change = time.time()

        print(f"[CircuitBreaker] {event.from_state.value} → "
              f"{event.to_state.value}: {reason}")

    def get_history(self) -> list[dict]:
        """获取熔断历史"""
        return [
            {
                'timestamp': datetime.fromtimestamp(e.timestamp).isoformat(),
                'from': e.from_state.value,
                'to': e.to_state.value,
                'reason': e.reason,
            }
            for e in self.events
        ]
