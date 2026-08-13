"""
结果解释器 —— 把查出来的数字，翻译成人能听懂的话

小白类比：这一步是"翻译成大白话"。
数据库查出来的是冷冰冰的数字 {"month":"2026-06","rate":0.032}，
用户要看懂的是"上个月逾期率 3.2%"，最好还能说一句"比上个月涨了"。

为什么不能直接把查询结果甩给用户？
  - 0.032 这种小数，用户不知道是 3.2% 还是 32%
  - 一堆行数据，用户不知道重点是什么
  - 有质量提示/成熟度提示时，要主动告诉用户，不能藏着
所以需要一个"翻译 + 提炼 + 附注意事项"的环节。

关键原则：宁可少说，不能乱说。
  LLM 解释数据时可能"编造业务原因"（比如硬说"逾期率上升是因为某政策"）。
  这比不解释还危险。所以解释要严格基于查询结果，不越界推断。
"""

from typing import Any, Optional

from src.ai_assistant.llm_client import LLMClient
from src.ai_assistant.query_executor import QueryResult


class ResultExplainer:
    """
    结果解释器。

    职责：把查询结果 + 注意事项，翻译成用户能懂的自然语言回答。
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def explain(self, indicator_name: str, result: QueryResult) -> str:
        """
        把查询结果翻译成自然语言回答。

        小白理解：输入指标名 + 查询结果，输出一段人能读懂的话。
        """
        # ── 第一步：把数据整理成文字，方便 LLM 理解 ──
        data_desc = self._format_data(result.data)

        # ── 第二步：让 LLM 生成解释 ──
        prompt = f"""
你是信贷数据分析助手。请用自然语言向用户解释以下查询结果。

【查询指标】{indicator_name}
【查询结果】{data_desc}

【注意事项】
- 有数据质量提示时，要如实告知用户
- 有账龄成熟度提示时，要提醒用户数据可能不完整

要求：
- 用百分比表示小数（0.032 = 3.2%）
- 严格基于查询结果，不要编造数据以外的业务原因
- 简洁，一两句话即可
"""
        explanation = self.llm.chat(prompt)

        # ── 第三步：把质量/成熟度提示附加到回答末尾 ──
        # 这些提示很重要，不能因为 LLM 没提到就丢掉
        warnings = []
        if result.quality_issue:
            warnings.append(result.quality_issue)
        if result.maturity_issue:
            warnings.append(result.maturity_issue)

        if warnings:
            explanation += "\n\n⚠️ " + "\n⚠️ ".join(warnings)

        return explanation

    def _format_data(self, data: Optional[list]) -> str:
        """把查询结果（行列表）格式化成一串文字。"""
        if not data:
            return "（无数据）"
        return "；".join(
            f"{row.get('month', '未知')} 为 {row.get('rate', row.get('value', '?'))}"
            for row in data
        )
