"""
意图识别 —— 听懂用户到底想干什么

小白类比：这一步就像客服接线员先问一句"您是想查数据、还是问概念？"，
把来电分流到不同的柜台。系统也必须先分清用户这句话属于哪类问题，
才能决定走哪条处理路径。

为什么不能跳过这一步？
  同样是"逾期率"三个字：
    - "上个月逾期率是多少？"    → 要查数（走 NL2SQL）
    - "逾期率是什么意思？"      → 要解释概念（走 RAG）
    - "逾期率是怎么算出来的？"   → 要查血缘（走血缘追溯）
  三句话处理方式完全不同，先分流才能做对。

真实生产的两级设计（重要）：
  这里为了学习简化成"一次 LLM 调用"。但真实金融系统是两级流水线：
    第一级：用轻量规则/小模型（几毫秒）快速判断，命中就返回
    第二级：小模型拿不准（置信度低）时，才升级到大模型
  为什么要两级？因为 LLM 慢（几百毫秒）且贵，能不用就不用。
"""

from dataclasses import dataclass
from typing import Any

from src.ai_assistant.llm_client import LLMClient


@dataclass
class IntentResult:
    """意图识别的结果"""
    intent: str          # 意图类型：指标查询 / 口径解释 / 血缘追溯 / 闲聊
    confidence: float    # 置信度 0~1，低于阈值就反问用户
    slots: dict[str, Any]  # 槽位：从话里抽出的结构化信息（指标名、时间、维度）


class IntentClassifier:
    """
    意图识别器。

    职责：把用户的一句话，分类成"要干什么"，并抽出关键槽位。
    """

    # 意图的枚举（写成类常量，避免到处写魔法字符串）
    INTENT_INDICATOR = "指标查询"   # 查具体数值
    INTENT_DEFINITION = "口径解释"  # 解释概念
    INTENT_LINEAGE = "血缘追溯"     # 查来源
    INTENT_CHAT = "闲聊"            # 跟数据无关的聊天
    INTENT_DANGEROUS = "危险操作"   # 想删库/改数据等破坏性操作

    # 置信度阈值：低于这个值，说明模型没把握，宁可反问也不要硬猜
    CONFIDENCE_THRESHOLD = 0.7

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def classify(self, query: str) -> IntentResult:
        """
        对用户问题做意图识别 + 槽位抽取。

        小白理解：喂进一句话，吐出一个"意图 + 槽位"的结构。
        比如输入"上个月逾期率是多少"，输出 intent=指标查询，slots={指标:逾期率, 时间:上月}
        """
        # ── 第一步：判断意图 ──
        # 把问题包装成一个 prompt，让 LLM 判断属于哪类
        prompt = f"""
你是信贷数据助手，请判断下面用户问题属于哪类意图：
1. 指标查询（用户想查某个具体数值，如"逾期率是多少""通过率"）
2. 口径解释（用户想问某个概念是什么意思、定义是什么）
3. 血缘追溯（用户想问某个指标是怎么算出来的、数据来源是什么）
4. 闲聊（跟数据查询无关）

用户问题：{query}

请只返回 JSON：{{"intent": "指标查询", "confidence": 0.9}}
"""
        result = self.llm.chat_json(prompt)
        intent = result.get("intent", self.INTENT_CHAT)
        confidence = result.get("confidence", 0.0)

        # ── 第二步：抽取槽位 ──
        # 只有"指标查询"才需要抽槽位；其它意图不需要
        slots = {}
        if intent == self.INTENT_INDICATOR:
            slots = self._extract_slots(query)

        return IntentResult(intent=intent, confidence=confidence, slots=slots)

    def _extract_slots(self, query: str) -> dict[str, Any]:
        """
        从"指标查询"类问题里抽出结构化槽位。

        小白理解：把一句话拆成机器能用的字段。
        "上个月逾期率" → {指标: 逾期率, 时间: 上个月}
        """
        slot_prompt = f"""
从用户问题中抽取以下槽位（抽取不到就填 null）：
- metric: 要查询的指标（如"逾期率""通过率"）
- time: 时间范围（如"上个月""最近30天"）
- dimensions: 需要拆分的维度（如"按渠道""按地区"）

用户问题：{query}

请只返回 JSON：{{"metric": "...", "time": "...", "dimensions": []}}
"""
        return self.llm.chat_json(slot_prompt)

    def is_confident(self, result: IntentResult) -> bool:
        """判断意图识别是否足够可信。不可信就反问用户，别硬猜。"""
        return result.confidence >= self.CONFIDENCE_THRESHOLD
