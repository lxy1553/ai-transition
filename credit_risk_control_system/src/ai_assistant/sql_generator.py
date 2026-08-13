"""
NL2SQL 生成器 —— 把自然语言翻译成 SQL

小白类比：这一步是把"上个月逾期率是多少"翻译成数据库能执行的 SQL。
就像翻译官，把人话翻译成数据库的"语言"（SQL）。

为什么必须注入 Schema（表结构）？
  LLM 不会"看"你的数据库，它不知道你的表叫什么、有哪些字段。
  如果你不告诉它，它会自己瞎编字段名——生成出 `SELECT xx FROM yyy`，
  但你的库里根本没有这些字段，一执行就报错。
  所以生成 SQL 前，必须先拿到准确的表结构，塞进 prompt 里约束它。

生产级的"生成→校验→修正"循环（重要）：
  不是一次生成就完事。真实流程是：
    LLM 生成 SQL → 校验器检查 → 失败就带着错误信息重新生成 → 最多重试 N 次
  这样能大幅降低"生成出非法 SQL"的概率。
"""

from src.ai_assistant.llm_client import LLMClient
from src.ai_assistant.schema_catalog import SchemaCatalog


class SQLGenerator:
    """
    NL2SQL 生成器。

    职责：给定指标 + 表结构 + 时间范围，生成一条正确的查询 SQL。
    """

    def __init__(self, llm: LLMClient, catalog: SchemaCatalog):
        self.llm = llm
        self.catalog = catalog

    def generate(self, indicator: dict, time_range: dict) -> str:
        """
        生成查询某指标的 SQL。

        小白理解：输入"查逾期率、上个月"，输出一条 SELECT 语句。
        """
        table_name = indicator["table"]
        schema_prompt = self.catalog.get_schema_prompt(table_name)

        # 构建 prompt：把表结构、指标口径、时间范围都告诉 LLM
        prompt = f"""
你是 SQL 生成专家。请根据以下信息生成一条只读的 SELECT 查询。

【表结构】
{schema_prompt}

【要查询的指标】
指标名：{indicator["name"]}
计算方式：{indicator["formula"]}
分子字段：{indicator["columns"].get("numerator")}
分母字段：{indicator["columns"].get("denominator")}

【时间范围】
{time_range}

【硬性要求】（违反任何一条都算错误）
1. 只允许 SELECT 查询，禁止 INSERT/UPDATE/DELETE/DROP
2. 必须带时间过滤条件（WHERE 子句里要有时间字段）
3. 必须按月份 GROUP BY（方便看趋势）

请只返回 SQL 语句，不要解释。
"""
        # 学习版：MockLLM 不会真的生成 SQL，这里手动构造一条正确的 SQL 作为演示
        # 真实生产：这里会真的调用 LLM，拿到它生成的 SQL 字符串
        sql = self._build_sql_by_indicator(indicator, time_range)

        return sql

    def _build_sql_by_indicator(self, indicator: dict, time_range: dict) -> str:
        """
        手动构造 SQL（学习版专用，替代真实 LLM 生成）。

        小白理解：真实系统里这一步是 LLM 干的，但 LLM 输出的 SQL 你没法在
        学习时不联网看到结果，所以这里用"规则模板"手动写死一条，
        让你能看清 SQL 长什么样、字段是怎么对应上的。

        这也体现了生产里的另一个思路：简单指标用"规则模板"生成 SQL
        （快、可控、不会出错），复杂指标才交给 LLM。
        """
        table = indicator["table"]
        num = indicator["columns"]["numerator"]
        den = indicator["columns"]["denominator"]
        time_field = indicator.get("time_field", "dt")

        # 逾期率这种有分子分母的指标：算比值
        if den:
            return (
                f"SELECT DATE_FORMAT({time_field}, '%Y-%m') AS month, "
                f"ROUND(SUM({num}) / SUM({den}), 4) AS rate "
                f"FROM {table} "
                f"WHERE {time_field} >= '2026-06-01' "  # 上个月的起始日期（示例写死）
                f"GROUP BY DATE_FORMAT({time_field}, '%Y-%m') "
                f"ORDER BY month;"
            )
        # 已经预计算好的指标（如 approval_rate）：直接查
        else:
            return (
                f"SELECT {time_field} AS month, {num} AS value "
                f"FROM {table} "
                f"WHERE {time_field} >= '2026-06-01' "
                f"ORDER BY {time_field};"
            )
