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
        智能匹配：先试标准名，再试别名。查不到返回 None。

        这是最常用的入口——无论用户说标准名还是口语名，都能找到指标。
        """
        return (
            self.get_indicator_by_name(keyword)
            or self.get_indicator_by_alias(keyword)
        )

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
