"""
查询执行器 —— 真正去数仓里跑 SQL，并做质量检查

小白类比：这一步就是"真去仓库取货"。
前面都是准备工作（理解需求、找资料、写 SQL），到这里才真正执行查询。

为什么执行要包这么多层防护？
  一条 SQL 看起来无害，但执行时可能：
    - 跑太久（超时）—— 数亿行数据没加索引，一查就是几十分钟
    - 返回太多行 —— 内存直接爆掉
    - 查出来的数据是脏的 —— 数据质量差，算出来的数不可信
  所以执行器要管三件事：超时控制、行数限制、数据质量检查。

数据质量检查（之前 grilling 重点补的）：
  数仓 DWD 层有 dq_score（数据质量分）和 dq_quarantined（是否隔离）。
  如果某天数据质量差、大量样本被隔离，查出来的逾期率会失真偏低。
  所以执行前要先看质量状态，不达标要如实告知用户，而不是报个假数。
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class QueryResult:
    """查询执行结果"""
    success: bool                 # 是否成功
    data: list[dict] = None       # 查询结果（行列表）
    error: str = ""               # 错误信息（失败时）
    quality_issue: str = ""       # 数据质量提示（有质量问题时）
    maturity_issue: str = ""      # 账龄成熟度提示（样本未成熟时）


class QueryExecutor:
    """
    查询执行器。

    职责：执行 SQL + 超时控制 + 行数限制 + 数据质量/成熟度检查。
    """

    def __init__(self, max_rows: int = 1000, timeout_seconds: int = 10):
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds

    def execute(self, sql: str) -> QueryResult:
        """
        执行 SQL 并返回结果（学习版用模拟数据，不真连数据库）。

        真实生产：这里会调用数据库驱动（如 pyhive、clickhouse-driver），
        并包一层超时控制（线程 + join timeout）。
        """
        # ── 模拟执行：返回一份"上个月逾期率 3.2%"的假结果 ──
        # 学习版故意返回写死的数据，方便你理解下游怎么消费这个结果
        data = [
            {"month": "2026-05", "rate": 0.028},
            {"month": "2026-06", "rate": 0.032},
        ]

        # ── 数据质量检查（模拟）──
        # 真实生产：这里会查 DWD 层的 dq_quarantined 状态，
        # 看这批数据里有多少是被标记为"质量差、已隔离"的
        quality_issue = self._check_data_quality(data)

        # ── 账龄成熟度检查（模拟）──
        # 逾期率要 T+30 天才成熟，最近一个月的样本可能还没成熟
        maturity_issue = self._check_maturity("2026-06")

        return QueryResult(
            success=True,
            data=data,
            quality_issue=quality_issue,
            maturity_issue=maturity_issue,
        )

    def _check_data_quality(self, data: list[dict]) -> str:
        """
        检查数据质量（学习版返回空，真实版查 dq 状态）。

        小白理解：如果查出来的数据是"脏"的（大量缺失、隔离），
        这里要返回一个提示，让上层告诉用户"数据可能有质量问题"。
        """
        # 真实生产：检查 data 对应的那几天 dq_score 是否低于阈值
        # 这里简化返回空字符串 = 没有质量问题
        return ""

    def _check_maturity(self, latest_month: str) -> str:
        """
        检查账龄成熟度（重要！）。

        小白理解：逾期是"放款 30 天后"才暴露的。
        如果查的是最近一个月的逾期率，那批贷款还没满 30 天观察期，
        逾期还没完全暴露，算出来的逾期率会"偏低"（假象）。

        这就是之前 grilling 里说的"环比上升可能是账龄成熟度造成的假象"。
        """
        # 真实生产：判断 latest_month 距离今天是否 > 30 天
        # 这里简化：假设 2026-06 的数据还没成熟，返回提示
        return (
            f"注意：{latest_month} 的部分样本账龄未满 30 天观察期，"
            f"逾期率可能偏低，建议用成熟样本（放款 30 天以上）重新对比。"
        )

    def execute_with_retry(self, sql: str, max_retries: int = 3) -> QueryResult:
        """
        带重试的执行（真实生产用，这里留个骨架）。

        小白理解：执行失败时自动重试，最多试 N 次。防止偶发故障。
        """
        for attempt in range(max_retries):
            result = self.execute(sql)
            if result.success:
                return result
            # 真实生产：这里会判断错误类型，只有"可重试"的错误才重试
            # （比如网络抖动），"不可重试"的（比如表不存在）直接返回
        return result
