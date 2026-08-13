"""
AI 数据问答编排器 —— 把整条链路串起来

小白类比：这个文件是"总指挥"。前面写的一堆模块（意图识别、改写、
检索、生成 SQL、校验、执行、解释、审计），每一个都只干一件事，
而这个文件负责把它们按正确的顺序串起来，像流水线一样。

为什么要有一个"总指挥"，而不是把逻辑全写在一个函数里？
  1. 每个模块职责单一，好理解、好测试、好替换
  2. 编排逻辑（先干什么后干什么）和具体实现（怎么干）分开
  3. 出问题时能快速定位是"哪一步"错了

整条链路（对应真实生产）：
  鉴权 → 意图识别 → Query改写 → RAG检索 → NL2SQL → SQL校验
  → 执行 → 质量检查 → 结果解释 → 审计

分支逻辑（重要）：
  - 意图是"指标查询" → 走完整链路（改写到执行）
  - 意图是"口径解释"/"血缘追溯" → 只走 RAG 检索，直接回答（不用查数）
  - 意图是"闲聊" → 直接让 LLM 回答
  - 置信度低 → 反问用户澄清，不硬猜
  - 权限不足 → 直接拒绝
"""

import time
import uuid
from dataclasses import dataclass

from src.ai_assistant.llm_client import LLMClient
from src.ai_assistant.schema_catalog import SchemaCatalog
from src.ai_assistant.intent_classifier import IntentClassifier
from src.ai_assistant.query_rewriter import QueryRewriter
from src.ai_assistant.retriever import (
    VectorRetriever, KeywordRetriever, RuleRetriever,
    rrf_fusion, Reranker, PermissionFilter,
)
from src.ai_assistant.sql_generator import SQLGenerator
from src.ai_assistant.sql_validator import SQLValidator
from src.ai_assistant.query_executor import QueryExecutor, QueryResult
from src.ai_assistant.result_explainer import ResultExplainer
from src.ai_assistant.audit_logger import AuditLogger, AuditEvent


@dataclass
class Answer:
    """最终返回给用户的答案"""
    trace_id: str
    answer: str           # 自然语言回答
    sql: str              # 执行的 SQL（供审计/展示）
    result: QueryResult   # 查询结果（供审计）


class QAPipeline:
    """
    AI 数据问答流水线。

    小白理解：你只需要调用 `ask("上个月逾期率是多少")`，
    它内部自动跑完整条链路，最后返回一段人能看懂的回答。
    """

    def __init__(self, llm: LLMClient, catalog: SchemaCatalog):
        """
        组装所有模块（依赖注入）。

        小白理解：这里像"开工厂前把所有机器装好"。
        每个模块在 init 时创建好，ask() 时直接用。
        """
        self.llm = llm
        self.catalog = catalog

        # 组装各模块（注意：每个模块都拿到它需要依赖的东西）
        self.intent_classifier = IntentClassifier(llm)
        self.query_rewriter = QueryRewriter(llm, catalog)
        self.retrievers = {
            "vector": VectorRetriever(catalog),
            "keyword": KeywordRetriever(catalog),
            "rule": RuleRetriever(catalog),
        }
        self.reranker = Reranker()
        self.permission = PermissionFilter(catalog)
        self.sql_generator = SQLGenerator(llm, catalog)
        self.sql_validator = SQLValidator()
        # 执行器连上真实数仓（SQLite）。真实生产把 SQLite 换成 ClickHouse 驱动即可
        from src.ai_assistant.mock_warehouse import MockWarehouse
        self.warehouse = MockWarehouse()
        self.executor = QueryExecutor(self.warehouse.get_connection())
        self.explainer = ResultExplainer(llm)
        self.audit = AuditLogger()

    def ask(self, query: str, user_id: str = "anonymous", user_role: str = "analyst") -> Answer:
        """
        主入口：用户问一句话，返回一个答案。

        小白理解：这就是你唯一需要调用的方法。整条链路都封装在里面了。
        """
        t_start = time.perf_counter()
        trace_id = uuid.uuid4().hex[:16]   # 生成全链路追踪 ID
        sql = ""
        result = QueryResult(success=False, data=[])

        # ── 步骤 1：意图识别 ──
        intent_result = self.intent_classifier.classify(query)

        # 置信度低 → 反问用户，不硬猜
        if not self.intent_classifier.is_confident(intent_result):
            answer = "抱歉，我不太确定您想问什么，能换个说法再说一遍吗？"
            self._log(trace_id, user_id, query, intent_result.intent, {}, "", result, t_start)
            return Answer(trace_id=trace_id, answer=answer, sql=sql, result=result)

        # ── 分支处理：根据意图走不同路径 ──
        if intent_result.intent == IntentClassifier.INTENT_INDICATOR:
            # 指标查询 → 走完整链路
            answer, sql, result = self._handle_indicator_query(
                query, user_role, trace_id
            )
        elif intent_result.intent == IntentClassifier.INTENT_DANGEROUS:
            # 危险操作 → 直接拒绝，不进入任何查询逻辑
            answer = "抱歉，系统只支持数据查询，不支持修改或删除操作。"
        elif intent_result.intent == IntentClassifier.INTENT_DEFINITION:
            # 口径解释 → 走 RAG 查定义
            answer = self._handle_definition_query(query)
        elif intent_result.intent == IntentClassifier.INTENT_LINEAGE:
            # 血缘追溯 → 查血缘（从哪来、怎么算）
            answer = self._handle_lineage_query(query)
        else:
            # 闲聊 → 直接让 LLM 回答
            answer = self.llm.chat(query)

        # ── 最后一步：写审计日志 ──
        self._log(trace_id, user_id, query, intent_result.intent, {}, sql, result, t_start)

        return Answer(trace_id=trace_id, answer=answer, sql=sql, result=result)

    # ── 指标查询的完整链路 ──────────────────────────────

    def _handle_indicator_query(self, query: str, user_role: str, trace_id: str):
        """处理"指标查询"类问题：改写 → 检索 → 生成SQL → 校验 → 执行 → 解释。"""

        # 步骤 2：Query 改写（口语 → 结构化）
        rewritten = self.query_rewriter.rewrite(query)

        # 改写失败（没识别出指标）→ 反问
        if not rewritten.resolved:
            # 区分两种失败：未来时间 vs 没找到指标
            if rewritten.time_range.get("type") == "future":
                return (
                    "抱歉，无法查询未来时间的数据，请查询已经发生的时间范围。",
                    "", QueryResult(success=False, data=[]),
                )
            return (
                "抱歉，我没有找到对应的指标，请问您想查什么数据？",
                "", QueryResult(success=False, data=[]),
            )

        indicator_name = rewritten.indicators[0]

        # 步骤 3：权限过滤（金融场景生死线）
        if not self.permission.check(indicator_name, user_role):
            return (
                f"抱歉，您没有权限查看「{indicator_name}」这个指标。",
                "", QueryResult(success=False, data=[]),
            )

        # 步骤 4：RAG 检索（多路召回 → RRF 融合 → 精排）
        indicator = self.catalog.get_indicator_by_name(indicator_name)
        vector_docs = self.retrievers["vector"].search(query)
        keyword_docs = self.retrievers["keyword"].search(query)
        rule_docs = self.retrievers["rule"].search(indicator_name)
        merged = rrf_fusion([vector_docs, keyword_docs, rule_docs])
        top_docs = self.reranker.rerank(query, merged)

        # 步骤 5：NL2SQL 生成
        sql = self.sql_generator.generate(indicator, rewritten.time_range)

        # 步骤 6：SQL 校验（安全门）
        validation = self.sql_validator.validate(sql)
        if validation.is_safety_block:
            # 安全阻断 → 明确拒绝
            return (
                "抱歉，这个操作被安全策略拦截了，系统只支持数据查询。",
                sql, QueryResult(success=False, data=[], error="安全阻断"),
            )
        if not validation.is_valid:
            # 普通校验失败 → 提示
            return (
                f"查询失败：{'; '.join(validation.violations)}",
                sql, QueryResult(success=False, data=[], error="校验失败"),
            )

        # 步骤 7：执行查询
        result = self.executor.execute(sql)

        # 步骤 8：结果解释（翻译成人话）
        answer = self.explainer.explain(indicator_name, result)

        return answer, sql, result

    # ── 口径解释的链路 ──────────────────────────────────

    def _handle_definition_query(self, query: str) -> str:
        """处理"口径解释"类问题：走 RAG 检索，直接回答，不查数。"""
        # 检索指标定义
        vector_docs = self.retrievers["vector"].search(query)
        keyword_docs = self.retrievers["keyword"].search(query)
        merged = rrf_fusion([vector_docs, keyword_docs])
        top_docs = self.reranker.rerank(query, merged, top_k=3)

        if not top_docs:
            return "抱歉，我没有找到相关的指标定义。"

        # 把检索到的定义拼起来回答
        definitions = "\n".join(f"- {doc.content}" for doc in top_docs)
        return f"根据资料，相关解释如下：\n{definitions}"

    # ── 血缘追溯的链路 ──────────────────────────────────

    def _handle_lineage_query(self, query: str) -> str:
        """
        处理"血缘追溯"类问题：查指标的血缘（从哪来、怎么算的）。

        小白理解：用户问"逾期率是怎么算的""这个指标数据来源是什么"，
        就是查血缘——这个指标从哪个源头、经过什么加工算出来的。

        和"口径解释"的区别：
        - 口径解释：指标"是什么"（定义、含义）→ 走 RAG 查 description
        - 血缘追溯：指标"从哪来、怎么算的"（来源链路）→ 查 lineage 字段
        之前两者混在一起走 RAG，现在拆开，各自查各自的内容。
        """
        # 用改写器提取指标名（"逾期率是怎么算的" → delinquency_rate）
        rewritten = self.query_rewriter.rewrite(query)
        if not rewritten.resolved or not rewritten.indicators:
            return "抱歉，我没有找到对应的指标，无法追溯其血缘。"

        indicator_name = rewritten.indicators[0]
        indicator = self.catalog.get_indicator_by_name(indicator_name)
        lineage = self.catalog.get_lineage(indicator_name)

        if not lineage:
            return f"抱歉，「{indicator_name}」暂未记录血缘信息。"

        formula = indicator.get("formula", "")
        return (
            f"「{indicator_name}」的数据血缘：\n{lineage}\n\n"
            f"计算公式：{formula}"
        )

    # ── 审计 ────────────────────────────────────────────

    def _log(self, trace_id, user_id, query, intent, rewritten, sql, result, t_start):
        """写审计日志。"""
        latency_ms = (time.perf_counter() - t_start) * 1000
        event = AuditEvent(
            trace_id=trace_id,
            user_id=user_id,
            query=query,
            intent=intent,
            rewritten=rewritten,
            sql=sql,
            result=result.data if result else None,
            latency_ms=round(latency_ms, 2),
            timestamp=time.time(),
        )
        self.audit.log(event)
