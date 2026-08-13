"""
RAG 检索层 —— 从知识库里把"相关内容"捞出来

小白类比：这一步就像查资料前先翻目录、查索引。
用户问"逾期率"，系统不能空手回答，得先去找"逾期率的定义是什么、
存在哪张表、怎么算的"这些背景资料，找到了才好往下走。

为什么不能只用一种检索方式？
  - 向量检索（语义相似）：擅长"意思相近"，比如"坏账"能匹配到"逾期"
  - 关键词检索（精确匹配）：擅长"名字一模一样"，比如精确命中"delinquency_rate"
  - 规则字典检索：直接查指标目录，100% 准确，但只能查配置里有的
三种方式各有长短，所以要多路召回再融合——这就是 RRF 要做的事。

生产级三个关键点（面试常考）：
  1. 多路召回（recall）：宁可多捞，不能漏。三种方式各自 top-K
  2. RRF 融合：把多路结果合并排序，不用调权重，简单有效
  3. 权限过滤：检索完必须按用户权限过滤，金融场景是生死线
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievedDoc:
    """检索到的一篇"文档"（这里指一条指标定义或表结构）"""
    doc_id: str
    content: str          # 内容
    score: float          # 相关度分数
    source: str           # 来自哪一路检索：vector / keyword / rule
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorRetriever:
    """
    向量检索 —— 按"语义相似度"找相关内容。

    小白理解：把每个指标定义都变成一个向量（一串数字），
    用户的问题也变成向量，算两个向量的余弦相似度，越接近越相关。

    生产级：这里用真实的 Embedding 模型（如 BGE）做向量化，
    存进向量数据库（Milvus/Chroma）。学习版用关键词模拟相似度。
    """

    def __init__(self, catalog):
        self.catalog = catalog

    def search(self, query: str, top_k: int = 3) -> list[RetrievedDoc]:
        """
        按语义相似度检索。学习版用"关键词重叠"模拟向量相似度。
        """
        docs = []
        for ind in self.catalog._data.get("indicators", []):
            # 模拟语义相似度：query 和指标描述/别名重叠越多，分数越高
            text = ind["description"] + " ".join(ind.get("aliases", []))
            overlap = len(set(query) & set(text))
            if overlap > 0:
                docs.append(RetrievedDoc(
                    doc_id=ind["name"],
                    content=f"{ind['description']}（计算方式：{ind['formula']}）",
                    score=float(overlap),
                    source="vector",
                    metadata={"indicator": ind["name"]},
                ))
        # 按分数排序，取 top_k
        docs.sort(key=lambda d: d.score, reverse=True)
        return docs[:top_k]


class KeywordRetriever:
    """
    关键词检索 —— 按"精确匹配"找相关内容。

    小白理解：就是像 Ctrl+F 一样，精确查找指标名是否出现。
    生产级用 BM25 算法（比简单匹配更聪明，考虑词频和文档长度）。
    """

    def __init__(self, catalog):
        self.catalog = catalog

    def search(self, query: str, top_k: int = 3) -> list[RetrievedDoc]:
        """精确匹配指标名或别名。"""
        docs = []
        for ind in self.catalog._data.get("indicators", []):
            # 精确匹配：query 里包含指标的标准名或别名
            if ind["name"] in query or any(a in query for a in ind.get("aliases", [])):
                docs.append(RetrievedDoc(
                    doc_id=ind["name"],
                    content=f"指标 {ind['name']}，位于表 {ind['table']}",
                    score=1.0,  # 精确匹配给满分
                    source="keyword",
                    metadata={"indicator": ind["name"]},
                ))
        return docs[:top_k]


class RuleRetriever:
    """
    规则字典检索 —— 直接查指标目录（100% 准确）。

    小白理解：这是最"死板"但也最可靠的一路——不猜，直接翻字典。
    适用于已经确定指标名，要拿它的表结构和口径的场景。
    """

    def __init__(self, catalog):
        self.catalog = catalog

    def search(self, indicator_name: str) -> list[RetrievedDoc]:
        """按标准指标名精确查字典。"""
        ind = self.catalog.get_indicator_by_name(indicator_name)
        if ind is None:
            return []
        return [RetrievedDoc(
            doc_id=ind["name"],
            content=self.catalog.get_schema_prompt(ind["table"]),
            score=1.0,
            source="rule",
            metadata={"indicator": ind["name"], "table": ind["table"]},
        )]


def rrf_fusion(result_lists: list[list[RetrievedDoc]], k: int = 60) -> list[RetrievedDoc]:
    """
    RRF 融合（Reciprocal Rank Fusion）—— 把多路检索结果合并排序。

    小白理解：三种检索方式各给出一份排名，怎么合并？
    RRF 的做法：每个文档的得分 = 它在每路排名里的"倒数"之和。
    排名越靠前（第1名 > 第2名），贡献越大。不用手动调权重，简单又有效。

    公式：score(doc) = Σ 1/(k + rank_i)
      rank_i 是 doc 在第 i 路检索里的名次，k 是平滑常数（通常 60）
    """
    score_map: dict[str, float] = {}
    doc_map: dict[str, RetrievedDoc] = {}

    for result_list in result_lists:
        for rank, doc in enumerate(result_list, start=1):
            score_map[doc.doc_id] = score_map.get(doc.doc_id, 0.0) + 1.0 / (k + rank)
            # 保留第一次出现的 doc 对象（或取分数更高的那个）
            if doc.doc_id not in doc_map:
                doc_map[doc.doc_id] = doc

    # 按融合分数排序
    merged = [doc_map[did] for did in score_map]
    merged.sort(key=lambda d: score_map[d.doc_id], reverse=True)
    return merged


class Reranker:
    """
    精排 —— 用一个"更贵、更准"的模型，把融合后的 top-N 再精排一遍。

    小白理解：召回阶段是"广撒网"（快但粗），精排阶段是"精选"（慢但准）。
    生产级用专门的 rerank 模型（如 BGE-Reranker、Cohere Rerank）。
    学习版直接用文档本身的分数，不真的重排。
    """

    def rerank(self, query: str, docs: list[RetrievedDoc], top_k: int = 5) -> list[RetrievedDoc]:
        """精排（学习版：直接按现有分数取 top_k）。"""
        # 真实生产：这里会调用 rerank 模型重新打分，比如把 top20 精排到 top5
        return docs[:top_k]


class PermissionFilter:
    """
    权限过滤 —— 按用户角色过滤检索结果。

    小白理解：不是所有员工都能看所有数据。
    普通运营可能不能看"逾期率"这种敏感指标，风控专员才能看。
    这一步必须在返回结果前做，否则就是数据泄露事故。

    金融场景这是"生死线"，漏了就是生产事故。
    """

    # 角色等级：数字越大权限越高
    ROLE_LEVEL = {"guest": 0, "analyst": 1, "risk": 2, "admin": 3}

    def __init__(self, catalog):
        self.catalog = catalog

    def check(self, indicator_name: str, user_role: str) -> bool:
        """
        判断某用户是否有权查看某指标。

        逻辑：拿指标要求的角色等级，和用户的角色等级比，
        用户等级 >= 指标要求等级，才放行。
        """
        ind = self.catalog.get_indicator_by_name(indicator_name)
        if ind is None:
            return True  # 未知指标不拦截（由下游处理）
        required = ind.get("required_role", "all")
        if required == "all":
            return True
        return self.ROLE_LEVEL.get(user_role, 0) >= self.ROLE_LEVEL.get(required, 0)
