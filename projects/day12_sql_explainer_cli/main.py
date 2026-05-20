"""Day 12 - SQL 解释助手 CLI。

这个脚本是第一个完整项目雏形：输入 SQL，输出表、字段、风险等级、建议和缺失上下文。
当前版本先用规则实现，是为了把安全边界和结构化输出做稳定；后续再接 LLM 负责更自然的解释。
"""

import argparse
import json
import re
from dataclasses import asdict, dataclass


EXAMPLE_SQL = """
select city, count(distinct user_id) as active_users
from user_events
where dt between '2026-05-01' and '2026-05-07'
  and event_name = 'app_open'
group by city
order by active_users desc
limit 100
"""


@dataclass
class Risk:
    """单条 SQL 风险。

    level 用于程序判断严重程度，message 给用户说明问题，suggestion 告诉用户下一步怎么改。
    """

    level: str
    message: str
    suggestion: str


@dataclass
class SQLExplanation:
    """SQL 解释助手的结构化输出。

    这个结构让 CLI、API、前端或后续 LLM 都能稳定消费结果，
    不需要从一段自然语言里重新猜风险等级和建议。
    """

    summary: str
    tables: list[str]
    fields: list[str]
    risk_level: str
    can_publish: bool
    risks: list[Risk]
    suggestions: list[str]
    missing_context: list[str]


def normalize_sql(sql: str) -> str:
    """把 SQL 压成更稳定的一行文本。

    用户输入的 SQL 可能有换行、多空格和缩进。
    先归一化，后面的正则提取表名、字段和风险规则会更稳定。
    """
    return " ".join(sql.strip().split())


def extract_tables(sql: str) -> list[str]:
    """从 SQL 中提取 from 和 join 后面的表名。

    表名是后续做权限校验、表结构检索和指标口径补充的入口。
    当前用正则处理简单 SQL，复杂 SQL 后续应替换成 SQL parser。
    """
    normalized = normalize_sql(sql)
    matches = re.findall(
        r"\bfrom\s+([a-zA-Z_][\w.]*)|\bjoin\s+([a-zA-Z_][\w.]*)",
        normalized,
        flags=re.IGNORECASE,
    )
    tables: list[str] = []
    for from_table, join_table in matches:
        table = from_table or join_table
        if table and table not in tables:
            tables.append(table)
    return tables


def extract_fields(sql: str) -> list[str]:
    """提取 select 和 from 之间的字段表达式。

    字段列表能帮助用户理解 SQL 查了什么，也为后续字段级权限和敏感字段检查打基础。
    """
    normalized = normalize_sql(sql)
    match = re.search(r"\bselect\s+(.*?)\s+\bfrom\b", normalized, flags=re.IGNORECASE)
    if not match:
        return []
    return [field.strip() for field in match.group(1).split(",") if field.strip()]


def analyze_risks(sql: str) -> tuple[list[Risk], list[str]]:
    """用规则分析常见数仓 SQL 风险。

    这里的规则覆盖 select *、缺少 where、缺少 dt、聚合和排序等问题。
    这些风险适合由程序确定性检查，不应该完全交给 LLM 自由判断。
    """
    normalized = normalize_sql(sql).lower()
    risks: list[Risk] = []
    missing_context: list[str] = []

    has_where = bool(re.search(r"\bwhere\b", normalized))
    has_dt = bool(re.search(r"\bdt\b", normalized))

    # select * 会读取不必要字段，也可能把敏感字段带出来，所以风险级别较高。
    if "select *" in normalized:
        risks.append(Risk("high", "使用 select * 会读取不必要字段。", "只选择业务需要的字段。"))

    # 没有 where 条件时，大表很容易被全表扫描，线上成本和延迟都会失控。
    if not has_where:
        risks.append(Risk("high", "缺少 where 条件，可能触发全表扫描。", "增加时间范围、分区或业务过滤条件。"))

    # dt 通常是数仓分区字段，缺少分区过滤是数据开发里最常见的性能问题之一。
    if not has_dt:
        risks.append(Risk("medium", "未发现 dt 分区条件。", "数仓大表优先补充分区过滤，例如 dt。"))

    # group by 会触发聚合，分组字段基数过高时可能导致计算资源明显增加。
    if "group by" in normalized:
        risks.append(Risk("medium", "group by 可能产生较大的聚合开销。", "确认分组字段基数，必要时先过滤再聚合。"))

    # order by 在大数据场景里可能触发全局排序，成本通常比普通过滤更高。
    if "order by" in normalized:
        risks.append(Risk("medium", "order by 可能带来全局排序成本。", "确认是否必须全局排序，或限制排序数据量。"))

    # limit 只限制返回行数，不一定限制扫描量；没有 where 时仍可能先扫很多数据。
    if " limit " in f" {normalized} " and not has_where:
        risks.append(Risk("low", "limit 不代表扫描成本一定低。", "先过滤再 limit，避免无意义扫描。"))

    # 指标名需要业务口径支撑，否则 SQL 即使能跑，也可能不符合业务定义。
    if "active_users" in normalized:
        missing_context.append("active_users 活跃用户业务口径")

    return risks, missing_context


def decide_risk_level(risks: list[Risk], missing_context: list[str]) -> str:
    """根据风险列表和缺失上下文决定总风险等级。

    总等级用于后续流程判断，比如是否允许上线、是否需要人工复核。
    缺少业务口径时即使没有 high 规则，也至少要标为 medium。
    """
    if any(risk.level == "high" for risk in risks):
        return "high"
    if any(risk.level == "medium" for risk in risks) or missing_context:
        return "medium"
    return "low"


def explain_sql(sql: str) -> SQLExplanation:
    """生成 SQL 的完整解释结果。

    这个函数把表字段提取、风险分析、等级判断和建议生成串起来。
    它是 CLI 当前最核心的业务入口，后续 API 化或接 LLM 时也可以复用。
    """
    tables = extract_tables(sql)
    fields = extract_fields(sql)
    risks, missing_context = analyze_risks(sql)
    risk_level = decide_risk_level(risks, missing_context)
    suggestions = [risk.suggestion for risk in risks]

    if missing_context:
        suggestions.append("补充缺失的业务口径或表结构后再判断是否上线。")

    if not suggestions:
        suggestions = ["当前未发现明显风险，建议结合表结构、数据量和执行计划继续确认。"]

    return SQLExplanation(
        summary="这段 SQL 用于查询数据表，并可能包含过滤、聚合、排序或限制返回条数。",
        tables=tables,
        fields=fields,
        risk_level=risk_level,
        can_publish=risk_level == "low" and not missing_context,
        risks=risks,
        suggestions=suggestions,
        missing_context=missing_context,
    )


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    用户可以传自己的 SQL，也可以用内置 example 快速验证项目是否能跑通。
    """
    parser = argparse.ArgumentParser(description="Explain SQL and identify common data warehouse risks.")
    parser.add_argument("--sql", help="SQL text to explain.")
    parser.add_argument("--example", action="store_true", help="Run with the built-in example SQL.")
    return parser.parse_args()


def main() -> None:
    """CLI 入口：读取 SQL、生成解释、打印 JSON。

    输出 JSON 是为了让结果不仅能给人看，也能被后续程序继续处理。
    """
    args = parse_args()
    sql = EXAMPLE_SQL if args.example else args.sql

    if not sql:
        raise SystemExit("Please provide --sql or use --example.")

    explanation = explain_sql(sql)
    print(json.dumps(asdict(explanation), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
