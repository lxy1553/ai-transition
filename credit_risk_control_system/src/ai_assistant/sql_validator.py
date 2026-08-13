"""
SQL 校验器 —— 执行前的最后一道安全门

小白类比：这一步就像机场安检。SQL 就是"行李"，执行就是"登机"。
安检要确保行李里没有违禁品（比如删库的 DROP 语句），才能放行。

为什么必须有这一步？
  LLM 生成的 SQL 是"不可信的"——它可能：
    - 生成出 DELETE/DROP 这种危险操作（把库删了）
    - 漏掉 WHERE 条件（导致全表扫描，数亿行直接卡死数据库）
    - 没限制行数（返回几百万行，内存爆掉）
  所以执行前必须用"死规则"逐条检查，不信任 LLM 的自觉。

关键区分：安全阻断 vs 系统错误
  这两者要分开，返回给用户的信息完全不同：
    - 安全阻断（SQL 有危险操作）→ 明确拒绝，告诉用户"不支持这个操作"
    - 系统错误（表不存在、语法错误）→ 提示"查询失败，请重试"
  用户能接受"查不到"，但会害怕"这系统居然能删我数据"。
"""

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """SQL 校验结果"""
    is_valid: bool                    # 是否通过校验
    violations: list[str] = field(default_factory=list)   # 违反的规则清单
    is_safety_block: bool = False     # 是否是"安全阻断"（危险操作），而非普通错误


class SQLValidator:
    """
    SQL 校验器。

    职责：用一系列"死规则"检查 SQL，确保它安全、可执行、不会拖垮数据库。
    """

    # 危险关键字：出现这些词直接判定为安全阻断
    DANGEROUS_KEYWORDS = [
        "DROP", "DELETE", "TRUNCATE", "ALTER", "INSERT",
        "UPDATE", "CREATE", "GRANT", "REVOKE",
    ]

    def __init__(self, max_join: int = 3, max_rows: int = 1000):
        self.max_join = max_join      # 最大 JOIN 数，防止复杂查询拖垮库
        self.max_rows = max_rows      # 最大返回行数

    def validate(self, sql: str) -> ValidationResult:
        """
        对 SQL 做完整校验，返回校验结果。

        小白理解：输入一条 SQL，输出"能不能执行 + 违反了哪些规则"。
        """
        violations = []
        is_safety_block = False

        # ── 检查 1：危险操作（最严重，安全阻断）──
        upper_sql = sql.upper()
        for kw in self.DANGEROUS_KEYWORDS:
            if kw in upper_sql:
                violations.append(f"禁止执行 {kw} 操作，只允许只读查询")
                is_safety_block = True

        # ── 检查 2：必须是 SELECT ──
        if not upper_sql.strip().startswith("SELECT"):
            violations.append("必须是 SELECT 查询")

        # ── 检查 3：必须有 WHERE 时间过滤（防止全表扫描）──
        if "WHERE" not in upper_sql:
            violations.append("缺少 WHERE 过滤条件，会全表扫描")

        # ── 检查 4：JOIN 数量限制 ──
        join_count = upper_sql.count("JOIN")
        if join_count > self.max_join:
            violations.append(f"JOIN 数量 {join_count} 超过限制 {self.max_join}")

        # ── 检查 5：行数限制（要么有 LIMIT，要么有 GROUP BY 聚合）──
        # 聚合查询（GROUP BY）返回的是汇总行，天然行数少；普通查询必须 LIMIT
        if "LIMIT" not in upper_sql and "GROUP BY" not in upper_sql:
            violations.append("缺少 LIMIT 或 GROUP BY，可能返回海量行")

        return ValidationResult(
            is_valid=(len(violations) == 0),
            violations=violations,
            is_safety_block=is_safety_block,
        )
