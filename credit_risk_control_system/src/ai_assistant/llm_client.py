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

    关键改进：Mock 不再硬编码"逾期率""通过率"这几个词，
    而是接收一个指标目录（catalog），查目录里的别名表来判断。
    这样 Mock 能识别配置里定义的所有同义词（坏账率、不良率、违约率...），
    评测测的才是"系统的真实映射能力"，而不是"Mock 硬编码了几个词"。

    生产级替换：真实项目里，把这个类换成 OpenAILLM / ClaudeLLM / DeepSeekLLM，
    它们实现同样的 chat / chat_json 接口，只是内部真的发 HTTP 请求。
    真实 LLM 理解同义词靠"语义"，Mock 靠"查别名表"，效果上等价——都是把口语词映射到标准指标。
    """

    def __init__(self, catalog=None):
        """
        Args:
            catalog: 指标目录（SchemaCatalog）。Mock 靠它识别同义词。
                     不传也能跑（退化成只认几个硬编码词），但评测会失真。
        """
        self.catalog = catalog

    def _find_indicator(self, query: str):
        """
        用指标目录查 query 里提到了哪个指标（模拟 LLM 理解同义词）。

        小白理解：真实 LLM 看到"坏账率"能理解它是"逾期率"。
        Mock 做不到语义理解，但可以查别名表——如果"坏账率"在某个指标的
        aliases 里，就等价于"理解"了这个同义词。
        """
        if self.catalog is None:
            return None
        for ind in self.catalog._data.get("indicators", []):
            # 检查 query 里是否含指标的标准名
            if ind["name"] in query:
                return ind
            for alias in ind.get("aliases", []):
                # 双向包含：别名是 query 的子串，或 query 是别名的子串
                # 例："坏账率" in query → 匹配；query="额度"，"额度" in "平均额度" → 匹配
                if alias in query or query in alias:
                    return ind
        return None

    def _has_query_action(self, query: str) -> bool:
        """
        检查用户是否有"查询动作"信号（这是解耦的关键）。

        小白理解：意图识别要回答"用户想不想查数据"，看的是"动作"，
        不是"查的指标存不存在"。用户说"查一个不存在的指标"，动作"查"是明确的，
        意图就应该是"指标查询"，至于指标不存在，那是后面"指标解析"要处理的。

        为什么动作词要选得精准？
          - "多少""是多少""查""查询""有没有" → 精准，闲聊里几乎不出现
          - "怎么样""看看""帮我" → 太宽泛，会误判"今天天气怎么样""帮我写首诗"
        """
        query_actions = ["是多少", "多少", "查询", "查", "有没有"]
        return any(action in query for action in query_actions)

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
            # 判断顺序很重要：
            #  1. 先判"血缘追溯"（因为"数据来源是什么"里既有"来源"又有"是什么"）
            #  2. 再判"口径解释"（"什么是坏账率"/"坏账率是什么"）
            #  3. 最后判"指标查询"（动作信号 OR 指标信号）
            if "怎么算" in query or "来源" in query or "血缘" in query or "计算逻辑" in query or "计算方式" in query:
                return {"intent": "血缘追溯", "confidence": 0.90}
            # 注意：同时匹配"什么是"和"是什么"两种语序（"什么是坏账率" vs "坏账率是什么"）
            if "什么意思" in query or "是什么" in query or "什么是" in query or "定义" in query:
                return {"intent": "口径解释", "confidence": 0.90}
            # ★ 解耦关键：意图判断 = 动作信号（想查数） OR 指标信号（陈述式查询）
            #   动作信号：用户说"查""多少"，就是查询意图，不管指标存不存在
            #   指标信号：用户说"最近30天的逾期率"，没有动作词但有指标名，也是查询
            #   两者满足其一就是"指标查询"，指标是否存在交给下游"指标解析"处理
            if self._has_query_action(query) or self._find_indicator(query) is not None:
                return {"intent": "指标查询", "confidence": 0.92}
            return {"intent": "闲聊", "confidence": 0.60}

        # ── Query 改写：抽取指标关键词 ──
        if "indicator_keyword" in prompt or "提取" in prompt:
            # 用指标目录找 query 提到的指标，返回标准名
            indicator = self._find_indicator(query)
            keyword = indicator["name"] if indicator else ""
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


# ── 真实 LLM 实现 ─────────────────────────────────────────
# 下面是真实调用 DeepSeek 大模型的实现。
# 本质就一件事：发 HTTP 请求，把返回的 JSON 里的文字抽出来。

import os
import json


class DeepSeekLLM(LLMClient):
    """
    真实调用 DeepSeek 大模型。

    小白类比：这才是"真的大脑"。MockLLM 是背答案的机器人，
    这个是真把问题发到 DeepSeek 服务器，让真的大模型理解并回答。

    使用前提：
      1. 去 platform.deepseek.com 注册，拿一个 API Key
      2. 设置环境变量：export DEEPSEEK_API_KEY=sk-xxxx
      3. 装了 requests：pip install requests

    为什么选 DeepSeek？
      - 便宜（价格是 GPT 的几十分之一），学习/开发成本低
      - API 兼容 OpenAI 格式，换 GPT/Claude 只需改个 base_url 和模型名
    """

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.base_url = base_url

    def chat(self, prompt: str, **kwargs) -> str:
        """发一段话，拿回模型的文本回答。"""
        content = self._call(prompt, json_mode=False)
        return content

    def chat_json(self, prompt: str, **kwargs) -> dict[str, Any]:
        """
        发一段话，拿回结构化的 JSON 回答。

        关键：这里开了 JSON mode（response_format=json_object），
        让模型保证返回合法 JSON，下游才能安全地 json.loads。
        """
        content = self._call(prompt, json_mode=True)
        # 模型可能返回带 ```json 包裹的内容，剥掉再解析
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            content = content.replace("json\n", "", 1)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 解析失败兜底：返回一个空结构，让上层走降级逻辑
            return {"result": "parse_error"}

    def _call(self, prompt: str, json_mode: bool) -> str:
        """
        真正发 HTTP 请求的核心方法。

        小白理解：把 prompt 打包成 JSON，POST 到 DeepSeek 服务器，
        服务器返回一段 JSON，里面 choices[0].message.content 就是回答。
        """
        import requests  # 延迟导入：只有真用 DeepSeek 时才需要 requests

        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,   # 低温 = 输出更稳定、更少随机，适合意图识别这种任务
        }
        # JSON mode：让模型保证返回合法 JSON
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,   # 30 秒超时，防止一直挂着
        )
        resp.raise_for_status()  # 非 200 抛异常（比如 API Key 错、欠费）
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def create_llm(catalog=None) -> LLMClient:
    """
    LLM 工厂函数 —— 根据环境变量决定用真的还是假的。

    小白理解：这是一个"自动开关"。
      设置了 DEEPSEEK_API_KEY → 用真 DeepSeek
      没设置 → 用 MockLLM（方便本地开发、不花钱）

    这样你的代码不用改，靠环境变量就能在"真实"和"模拟"之间切换。

    Args:
        catalog: 指标目录。传给 MockLLM 让它能识别同义词（查别名表）。
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if api_key:
        return DeepSeekLLM(api_key)
    # 没 Key 就降级用 Mock（本地开发、跑 demo、跑单测都够用）
    return MockLLM(catalog)
