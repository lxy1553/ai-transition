"""
Query 改写 —— 把用户的大白话，翻译成机器能精确执行的查询

小白类比：用户说"上个月逾期率多少"，这句话对人很自然，
但机器没法直接拿去查数——"上个月"到底是哪几天？"逾期率"对应哪个字段？
Query 改写就是把模糊的口语，翻译成精确的结构化请求。

这一步是数据问答里最容易忽略、却最容易出错的地方：
  - "上个月" 到底是自然月（6月1日~6月30日）还是滚动30天（今天往前推30天）？
  - "逾期率" 是笔数口径还是金额口径？是 DPD30+ 还是 DPD60+？
  - "坏账率""不良率" 都是"逾期率"的同义词，得统一
不把这些讲清楚，查出来的数就会算错，用户还察觉不到。

真实生产的降级策略（重要）：
  改写失败或置信度低时，不是报错，而是"静默回退到原始 query"——
  用没改写的话继续往下走，至少不中断服务。宁可答案粗糙，不能系统崩。
"""

from dataclasses import dataclass
from typing import Any

from src.ai_assistant.llm_client import LLMClient
from src.ai_assistant.schema_catalog import SchemaCatalog


@dataclass
class RewrittenQuery:
    """改写后的结构化查询"""
    original: str                    # 用户原话（保留，用于审计和回退）
    indicators: list[str]            # 解析出的标准指标名（如 ["delinquency_rate"]）
    time_range: dict[str, Any]       # 时间范围（如 {type: natural_month, value: last_month}）
    basis: str                       # 口径：按笔数 by_count / 按金额 by_amount
    window: str                      # 观察窗口：DPD30+ / DPD60+
    resolved: bool                   # 是否成功改写出明确的指标


class QueryRewriter:
    """
    Query 改写器。

    职责：把口语问题翻译成结构化查询，同时用指标目录做"同义词归一化"和"口径绑定"。
    """

    def __init__(self, llm: LLMClient, catalog: SchemaCatalog):
        self.llm = llm
        self.catalog = catalog

    def rewrite(self, query: str) -> RewrittenQuery:
        """
        改写用户问题。

        分三步：
          1. 用 LLM 抽出指标名和意图
          2. 用指标目录把口语词映射到标准字段（同义词归一化）
          3. 用默认口径补齐没说明的参数（口径绑定）
        """
        # ── 第一步：LLM 粗提取 ──
        prompt = f"""
从用户问题中提取关键信息，返回 JSON：
- indicator_keyword: 用户提到的指标口语词（如"逾期率""坏账率"）
- time: 时间表达（如"上个月""最近30天"）

用户问题：{query}

只返回 JSON：{{"indicator_keyword": "...", "time": "..."}}
"""
        extracted = self.llm.chat_json(prompt)

        # ── 第二步：同义词归一化 ──
        # 把"坏账率""不良率"这类口语词，映射到标准字段名 delinquency_rate
        keyword = extracted.get("indicator_keyword", "")
        indicator = self.catalog.resolve_indicator(keyword)

        if indicator is None:
            # 没找到对应指标，返回"未解析"状态，让上层决定怎么处理
            return RewrittenQuery(
                original=query,
                indicators=[],
                time_range=self._parse_time(extracted.get("time", "")),
                basis=self.catalog.get_default_basis(),
                window="DPD30+",
                resolved=False,
            )

        # ── 第三步：口径绑定 ──
        # 用户没说口径，就用配置里的默认值（逾期率默认按笔数、DPD30+）
        time_range = self._parse_time(extracted.get("time", ""))

        # 未来时间校验：查"下个月"这种未来数据没意义，标记为未解析（上层反问）
        if time_range.get("type") == "future":
            return RewrittenQuery(
                original=query,
                indicators=[indicator["name"]],
                time_range=time_range,
                basis=self.catalog.get_default_basis(),
                window="DPD30+",
                resolved=False,
            )

        return RewrittenQuery(
            original=query,
            indicators=[indicator["name"]],
            time_range=time_range,
            basis=self.catalog.get_default_basis(),
            window="DPD30+",
            resolved=True,
        )

    def _parse_time(self, time_expr: str) -> dict[str, Any]:
        """
        把口语时间词转成结构化时间范围。

        小白理解：这是最常出错的地方。"上个月"有三种可能，
        这里统一转成结构化描述，真正的日期计算在生成 SQL 时再做。
        """
        if not time_expr:
            return {"type": "unspecified", "value": None}

        # 用规则做简单的时间归一化（生产里这块通常也要过 LLM 或专门的时间解析库）
        # 先判"未来时间"——查未来数据没有意义，应该反问（时间合理性校验）
        if "下个月" in time_expr or "明年" in time_expr or "下季度" in time_expr or "未来" in time_expr:
            return {"type": "future", "value": time_expr}
        if "上个月" in time_expr or "上月" in time_expr:
            return {"type": "natural_month", "value": "last_month"}
        if "最近30天" in time_expr or "近30天" in time_expr:
            return {"type": "rolling", "value": 30}
        if "本月" in time_expr or "这个月" in time_expr:
            return {"type": "natural_month", "value": "current_month"}
        # 兜底：没识别出来，返回原始表达
        return {"type": "raw", "value": time_expr}
