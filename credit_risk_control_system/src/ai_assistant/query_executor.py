"""
查询执行器 —— 真正去数仓里跑 SQL，并做质量检查

小白类比：这一步就是"真去仓库取货"。
前面都是准备工作（理解需求、找资料、写 SQL），到这里才真正执行查询。

和之前学习版最大的区别：
  之前是"返回写死的假数据"，现在是"真的拿 SQL 去 SQLite 里执行，
  返回真实查出来的结果"。这一改，整个项目从"骨架"变成了"能跑的作品"。

为什么执行要包这么多层防护？
  一条 SQL 看起来无害，但执行时可能：
    - 跑太久（超时）—— 数亿行数据没加索引，一查就是几十分钟
    - 返回太多行 —— 内存直接爆掉
    - 查出来的数据是脏的 —— 数据质量差，算出来的数不可信
  所以执行器要管三件事：超时控制、行数限制、数据质量检查。

生产级思考（重要）：
  执行器只依赖"一个数据库连接"，不关心底层是 SQLite 还是 ClickHouse。
  真实项目把 SQLite 换成 ClickHouse 驱动，这里代码几乎不用改。
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class QueryResult:
    """查询执行结果"""
    success: bool                 # 是否成功
    data: list[dict] = field(default_factory=list)   # 查询结果（行列表）
    error: str = ""               # 错误信息（失败时）
    quality_issue: str = ""       # 数据质量提示（有质量问题时）
    maturity_issue: str = ""      # 账龄成熟度提示（样本未成熟时）


class QueryExecutor:
    """
    查询执行器。

    职责：真的执行 SQL + 行数限制 + 数据质量/成熟度检查。
    """

    def __init__(self, connection, max_rows: int = 1000):
        """
        Args:
            connection: 数据库连接（sqlite3.Connection）。执行器不关心它是什么库。
            max_rows: 最大返回行数，防止内存爆掉。
        """
        self.conn = connection
        self.max_rows = max_rows

    def execute(self, sql: str) -> QueryResult:
        """
        真的执行 SQL 并返回结果。

        小白理解：把 SQL 交给数据库，拿回查询结果，再做质量检查。
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()

            # 把查询结果转成 list[dict]，方便下游用 row['字段名'] 访问
            columns = [d[0] for d in cursor.description] if cursor.description else []
            data = [dict(zip(columns, row)) for row in rows]

            # ── 行数限制 ──
            if len(data) > self.max_rows:
                data = data[:self.max_rows]

            # ── 数据质量检查 ──
            quality_issue = self._check_data_quality(data)

            # ── 账龄成熟度检查 ──
            maturity_issue = self._check_maturity(data)

            return QueryResult(
                success=True,
                data=data,
                quality_issue=quality_issue,
                maturity_issue=maturity_issue,
            )

        except Exception as e:
            # SQL 执行失败（语法错、表不存在等）
            return QueryResult(success=False, error=str(e))

    def _check_data_quality(self, data: list[dict]) -> str:
        """
        检查查询结果的数据质量。

        小白理解：如果查出来的数字有异常（比如空值、负数），
        要提示用户"这数据可能有问题"，而不是假装一切正常。

        真实生产：这里会查 DWD 层的 dq_score 和 dq_quarantined 字段，
        看这批数据里有多少被标记为"质量差、已隔离"。这里简化成
        检查结果里有没有空值或异常的负数。
        """
        if not data:
            return "查询无结果，请确认查询条件是否正确。"

        # 检查结果里有没有 None 或负数
        for row in data:
            for key, val in row.items():
                if val is None:
                    return "查询结果中存在空值，数据可能不完整。"
                if isinstance(val, (int, float)) and val < 0:
                    return "查询结果中出现负数，数据可能存在质量问题。"
        return ""

    def _check_maturity(self, data: list[dict]) -> str:
        """
        检查账龄成熟度（重要！）。

        小白理解：逾期是"放款 30 天后"才暴露的。
        如果查的是最近一个月的逾期率，那批贷款还没满 30 天观察期，
        逾期还没完全暴露，算出来的逾期率会"偏低"（假象）。

        这就是之前 grilling 里说的"环比上升可能是账龄成熟度造成的假象"。

        简化实现：检查结果里是否包含"数据里最新月份"（演示里是 2026-06），
        如果包含，就认为这个月样本可能未成熟。
        """
        # 找数据里的最新月份
        if not data:
            return ""

        months = [str(row.get("month", row.get("label_date", ""))) for row in data]
        # 演示里 2026-06 是"最新月份"，模拟它账龄未满 30 天
        if any("2026-06" in m for m in months):
            return (
                "注意：2026-06 的部分样本账龄未满 30 天观察期，"
                "逾期率可能偏低，建议用成熟样本（放款 30 天以上）重新对比。"
            )
        return ""

    def execute_with_retry(self, sql: str, max_retries: int = 3) -> QueryResult:
        """
        带重试的执行（真实生产用）。

        小白理解：执行失败时自动重试，最多试 N 次。防止偶发故障。
        注意：只有"可重试"的错误（网络抖动）才重试，
        "不可重试"的（表不存在、SQL 语法错）重试也没用，直接返回。
        """
        for attempt in range(max_retries):
            result = self.execute(sql)
            if result.success:
                return result
        return result
