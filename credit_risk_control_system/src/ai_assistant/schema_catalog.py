"""
Schema 目录 —— 指标口径 + 表结构的知识库

小白类比：这个文件是系统的"字典"和"货架清单"。
它把 config/indicators.yaml 里写的那些指标定义、表结构，加载到内存里，
供两个关键模块查询：
  1. RAG 检索：用户问"逾期率是啥"，这里能查到它的定义和口径
  2. NL2SQL：用户问"查逾期率"，这里能查到它对应哪张表、哪两个字段

为什么单独做这一层？
  数仓的指标口径是"单一事实源"（Single Source of Truth）。
  如果 RAG 和 NL2SQL 各自维护一份指标定义，早晚会不一致，查出来的数就对不上。
  所以统一从这里读，保证口径一致。

生产级思考：
  真实项目里，这份数据来自元数据中心（比如 Amundsen、DataHub），
  这里用一个 YAML 文件模拟，思路是一样的——指标定义集中管理，各处引用。
"""

import yaml
from pathlib import Path
from typing import Any, Optional


class SchemaCatalog:
    """
    指标与表结构的集中目录。

    职责单一：只负责"查"，不负责"算"。所有关于"指标叫什么、在哪张表、
    口径是什么"的问题，都问它。
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        加载指标配置。

        Args:
            config_path: indicators.yaml 的路径。默认用项目里的 config 目录。
        """
        if config_path is None:
            # 默认路径：这个文件在 src/ai_assistant/ 下，往上两级就是项目根
            config_path = (
                Path(__file__).resolve().parent.parent.parent
                / "config" / "indicators.yaml"
            )
        self.config_path = Path(config_path)
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        """从 YAML 文件加载指标配置，解析成内存里的字典。"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # ── 指标查询 ──────────────────────────────────────────

    def get_indicator_by_name(self, name: str) -> Optional[dict]:
        """
        按标准名（如 "delinquency_rate"）查指标定义。
        """
        for ind in self._data.get("indicators", []):
            if ind["name"] == name:
                return ind
        return None

    def get_indicator_by_alias(self, alias: str) -> Optional[dict]:
        """
        按口语别名（如"逾期率""坏账率"）查指标定义。

        小白理解：用户说"坏账率"，系统要能认出它其实是"逾期率"。
        这就是 aliases 的作用——把各种口语叫法映射到标准字段。
        """
        for ind in self._data.get("indicators", []):
            if alias in ind.get("aliases", []):
                return ind
        return None

    def resolve_indicator(self, keyword: str) -> Optional[dict]:
        """
        智能匹配：精确匹配 → 包含匹配（兜底）。查不到返回 None。

        三级匹配（从准到松）：
          1. 标准名精确匹配（"delinquency_rate"）
          2. 别名精确匹配（"逾期率"）
          3. 包含匹配（"额度"能匹配到"平均额度"）

        为什么需要"包含匹配"兜底？
          用户经常用简称、口语化表达，比如问"额度"其实是想问"平均额度"。
          如果只做精确匹配，"额度"就匹配不上，系统会误判"没这个指标"。

        防误匹配（关键）：
          最小长度阈值——关键词至少 2 个字才做包含匹配。
          否则单字"率"会同时匹配到"逾期率"和"通过率"，全是误匹配。
        """
        if not keyword:
            return None

        # 第一级 + 第二级：精确匹配
        exact = self.get_indicator_by_name(keyword)
        if exact:
            return exact
        exact_alias = self.get_indicator_by_alias(keyword)
        if exact_alias:
            return exact_alias

        # 第三级：包含匹配（兜底，带最小长度阈值）
        if len(keyword) >= 2:
            fuzzy = self._fuzzy_match(keyword)
            if fuzzy:
                return fuzzy[0]   # 多个匹配取第一个（歧义情况见 resolve_ambiguous）

        return None

    def _fuzzy_match(self, keyword: str) -> list[dict]:
        """
        包含匹配：关键词是别名的子串，或别名是关键词的子串。

        小白理解：用户说"额度"，别名里有"平均额度"，"额度"是"平均额度"的一部分，
        就算匹配上了。反之，用户说"平均授信额度"，别名里有"平均额度"，
        "平均额度"是"平均授信额度"的一部分，也算匹配上。
        """
        matches = []
        for ind in self._data.get("indicators", []):
            for alias in ind.get("aliases", []):
                if keyword in alias or alias in keyword:
                    matches.append(ind)
                    break   # 一个指标只加一次，避免重复
        return matches

    def resolve_ambiguous(self, keyword: str) -> list[dict]:
        """
        返回所有匹配的指标（用于歧义检测）。

        小白理解：如果"额度"同时匹配到多个指标，说明有歧义，
        系统应该反问用户"您是指平均额度还是授信额度"，而不是随便选一个。

        这个方法返回所有匹配项，供上层判断是否需要反问。
        """
        if not keyword:
            return []
        # 精确匹配 + 包含匹配，全部收集
        matches = []
        seen = set()
        for ind in self._data.get("indicators", []):
            if ind["name"] == keyword or keyword in ind.get("aliases", []):
                if ind["name"] not in seen:
                    matches.append(ind)
                    seen.add(ind["name"])
        if not matches and len(keyword) >= 2:
            matches = self._fuzzy_match(keyword)
        return matches

    # ── 表结构查询 ──────────────────────────────────────

    def get_table_schema(self, table_name: str) -> Optional[dict]:
        """
        查某张表的字段清单（供 NL2SQL 使用）。

        返回的表结构里包含每个字段的名称、类型、说明，
        LLM 拿到这个才能生成"字段名不瞎编"的 SQL。
        """
        for t in self._data.get("tables", []):
            if t["name"] == table_name:
                return t
        return None

    def get_schema_prompt(self, table_name: str) -> str:
        """
        把表结构格式化成一段文字，方便塞进 NL2SQL 的 prompt 里。

        小白理解：LLM 不会"看"你的数据库，你得用文字把表结构"告诉"它。
        这个方法就是把表结构翻译成 LLM 能读的一段话。
        """
        table = self.get_table_schema(table_name)
        if table is None:
            return f"表 {table_name} 不存在，请检查指标配置。"

        cols_desc = []
        for col in table["columns"]:
            cols_desc.append(f"  - {col['name']} ({col['type']}): {col['desc']}")

        return (
            f"表 {table['name']}: {table['description']}\n"
            f"字段列表:\n" + "\n".join(cols_desc)
        )

    # ── 口径歧义 ─────────────────────────────────────────

    def get_ambiguities(self, indicator_name: str) -> list[dict]:
        """
        查某指标有哪些口径歧义。

        小白理解：有些指标能有好几种算法（比如逾期率按笔数还是按金额）。
        这个方法告诉系统"这个指标有哪些没说清就会算错的地方"。
        """
        ind = self.get_indicator_by_name(indicator_name)
        if ind is None:
            return []
        return ind.get("ambiguity", [])

    def get_default_basis(self) -> str:
        """查默认口径（用户没指明时用哪个）。"""
        return self._data.get("defaults", {}).get("delinquency_basis", "by_count")

    def get_lineage(self, indicator_name: str) -> str:
        """
        查某指标的血缘（来源和计算链路）。

        小白理解：用户问"逾期率是怎么算出来的"，就是查这个。
        返回一段描述这个指标从哪来、怎么算的话。

        血缘（Lineage）和口径（Definition）的区别：
        - 口径解释：这个指标"是什么"（定义、含义）
        - 血缘追溯：这个指标"从哪来、怎么算的"（来源链路）
        两者是不同的意图，回答内容也不同。
        """
        ind = self.get_indicator_by_name(indicator_name)
        if ind is None:
            return ""
        return ind.get("lineage", "")
