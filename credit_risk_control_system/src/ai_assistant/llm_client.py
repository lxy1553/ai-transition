"""
LLM 客户端抽象层 —— 整个问答系统的"大脑"

小白类比：这个文件相当于一个"万能插头"。
你的问答系统需要调用大模型（ChatGPT、Claude、DeepSeek...），
但如果每个模块都直接写死调用某一家，那换模型时就得改遍所有代码。

所以这里定义了一个统一接口 LLMClient，所有模块只认这个接口。
想换模型？只需要在这里改一处，其它模块完全无感。

为什么学习时用 MockLLM（假的 LLM）？
  真实调用大模型要 API Key、要花钱、要联网。
  MockLLM 假装是个大模型，根据你 prompt 里的关键词返回预设好的答案，
  这样整条链路能"跑通"，你能看清数据是怎么流的，而不用真的调 API。

生产级思考：这个抽象还有三个好处——
  1. 方便测试：单测时用 MockLLM，不用依赖外部 API
  2. 方便降级：真实 LLM 挂了，可以切到备用模型（fallback）
  3. 方便成本控制：不同任务用不同档次的模型（贵的做精排，便宜的做粗筛）
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    """大模型客户端的统一接口。所有 AI 模块都依赖这个接口，而不是依赖某一家具体的模型。"""

    @abstractmethod
    def chat(self, prompt: str, **kwargs) -> str:
        """
        问模型一句话，得到一个文本回答。

        用于：意图识别、结果解释这类"要自然语言输出"的场景。
        """
        raise NotImplementedError

    @abstractmethod
    def chat_json(self, prompt: str, **kwargs) -> dict[str, Any]:
        """
        问模型一句话，得到一个"结构化的 JSON 回答"。

        为什么需要这个？因为下游代码要"机器能读"的结果，而不是一段话。
        比如意图识别，我希望模型返回 {"intent": "指标查询"} 而不是"我觉得这是查指标"。

        生产级：现在主流模型都支持 JSON mode / function calling，
        但这里抽象成一个独立方法，方便切换实现。
        """
        raise NotImplementedError


class MockLLM(LLMClient):
    """
    假的 LLM —— 不真的调用模型，而是根据 prompt 里的关键词返回预设答案。

    小白类比：这就像一个"背答案的机器人"，你问它什么，它从一个小抄本里找答案。
    目的是让整条链路能跑通，方便你理解数据流，而不是真的去理解你的问题。

    生产级替换：真实项目里，把这个类换成 OpenAILLM / ClaudeLLM / DeepSeekLLM，
    它们实现同样的 chat / chat_json 接口，只是内部真的发 HTTP 请求。
    """

    def chat(self, prompt: str, **kwargs) -> str:
        """
        返回一段模拟的自然语言回答。
        根据 prompt 里的关键词，决定"回答"什么内容。
        """
        # 这里用关键词做最简单的模拟，让链路能走通
        # 注意：结果解释器的 prompt 里用的是英文指标名 delinquency_rate，
        # 所以这里同时匹配中文"逾期率"和英文名，才能正确触发
        if "逾期率" in prompt or "delinquency_rate" in prompt:
            # 区分"查数值"和"问定义"两种场景
            if "查询结果" in prompt or "多少" in prompt:
                # 模拟：LLM 把查询结果翻译成人话
                return "上月逾期率为 3.2%，较上月上升 0.4 个百分点。"
            return "逾期率是信贷风险的核心指标，指逾期笔数占总放贷笔数的比例。"
        # 兜底：没命中关键词就返回通用回答
        return "根据数据查询结果，未能找到明确答案，请补充更多信息。"

    def chat_json(self, prompt: str, **kwargs) -> dict[str, Any]:
        """
        返回一段模拟的结构化 JSON 回答。

        注意：这里的关键词判断是"为了演示故意简化的"。
        真实 LLM 会真的理解你的 prompt，这里只是假装理解。

        关键：这里判断的是「用户问题」本身，而不是整个 prompt。
        因为 prompt 模板里本身就写了"逾期率""通过率"这些示例词，
        如果检查整个 prompt，就会把示例词误当成用户说的话。
        """
        # 从 prompt 里提取真正的用户问题（"用户问题："后面的那一句）
        query = self._extract_query(prompt)

        # ── 意图识别 ──
        if "意图" in prompt or "属于哪类" in prompt:
            # 判断顺序很重要：先判"解释意图"，再判"查询意图"
            # 因为"逾期率是什么意思"里既有"逾期率"又有"意思"，
            # 应该判成"口径解释"而不是"指标查询"
            if "什么意思" in query or "是什么" in query or "定义" in query:
                return {"intent": "口径解释", "confidence": 0.90}
            if "怎么算" in query or "来源" in query or "血缘" in query:
                return {"intent": "血缘追溯", "confidence": 0.90}
            if "逾期率" in query or "通过率" in query or "额度" in query:
                return {"intent": "指标查询", "confidence": 0.92}
            return {"intent": "闲聊", "confidence": 0.60}

        # ── Query 改写：抽取指标关键词 ──
        if "indicator_keyword" in prompt or "提取" in prompt:
            # 把口语指标词映射成标准关键词（注意用 query 判断，不是 prompt）
            if "坏账率" in query or "不良率" in query or "逾期率" in query:
                keyword = "逾期率"
            elif "通过率" in query:
                keyword = "通过率"
            elif "额度" in query:
                keyword = "额度"
            else:
                keyword = ""
            return {
                "indicator_keyword": keyword,
                "time": "上个月" if ("上个月" in query or "上月" in query) else "",
            }

        # ── 槽位抽取 ──
        if "槽位" in prompt or "抽取" in prompt:
            return {
                "metric": "delinquency_rate",
                "time": "last_month",
                "dimensions": [],
            }

        # ── 兜底 ──
        return {"result": "unknown"}

    def _extract_query(self, prompt: str) -> str:
        """
        从 prompt 里提取「用户问题」那一句。

        小白理解：prompt 是一大段给 LLM 的指令，其中夹杂着用户真正说的话。
        这个方法把"用户问题："后面的内容抽出来，避免把指令里的示例词误判。
        """
        import re
        # 找 "用户问题：xxx" 这种模式
        m = re.search(r"用户问题[：:]\s*(.+)", prompt)
        if m:
            return m.group(1).strip()
        # 兜底：没找到就返回整个 prompt
        return prompt


# ── 生产级真实实现示例（骨架）──────────────────────────────
# 下面是真实调用某家大模型时的样子。学习时不需要跑通，但你可以看到：
# 真实的 LLMClient 实现长什么样——本质就是发 HTTP 请求，把结果 parse 成结构。
#
# class DeepSeekLLM(LLMClient):
#     def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
#         self.api_key = api_key
#         self.base_url = base_url
#
#     def chat(self, prompt: str, **kwargs) -> str:
#         resp = requests.post(
#             f"{self.base_url}/v1/chat/completions",
#             headers={"Authorization": f"Bearer {self.api_key}"},
#             json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]},
#         )
#         return resp.json()["choices"][0]["message"]["content"]
