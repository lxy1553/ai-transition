"""Day 49 - 信贷主题域与 Agent 意图识别练习。

这个脚本用模拟的金融信贷主题域、意图分类规则和用户问题，演示 Agent 如何
先判断业务主题，再判断问题类型，最后选择离线查询、实时查询、RAG 口径问答、
血缘追溯、澄清或安全阻断。生产里意图识别是工具路由的前置条件，不能让模型
看到问题后直接自由选工具。
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
DOMAIN_CATALOG_PATH = OUTPUT_DIR / "credit_domain_catalog.json"
INTENT_RULES_PATH = OUTPUT_DIR / "intent_classification_rules.json"
CLASSIFICATION_CASES_PATH = OUTPUT_DIR / "intent_classification_cases.json"
MERMAID_PATH = OUTPUT_DIR / "credit_domain_intent_routing.mmd"
REPORT_PATH = OUTPUT_DIR / "credit_domain_intent_report.md"


@dataclass(frozen=True)
class CreditDomain:
    """描述一个金融信贷主题域。

    Agent 识别主题域后，才能选择合适的指标、表、实时事件、口径资料和权限规则。
    """

    domain: str
    description: str
    common_metrics: list[str]
    offline_tables: list[str]
    realtime_events: list[str]
    risk_notes: list[str]


@dataclass(frozen=True)
class IntentRule:
    """描述一类用户问题应该走什么工具路线。"""

    intent: str
    trigger_signals: list[str]
    required_context: list[str]
    target_route: list[str]
    fallback: str


@dataclass(frozen=True)
class ClassificationCase:
    """记录一条用户问题的主题域和意图分类结果。"""

    case_id: str
    user_question: str
    domain: str
    intent: str
    expected_route: list[str]
    reason: str
    risk_level: str


def build_domain_catalog() -> list[CreditDomain]:
    """构建金融信贷主题域目录。"""

    return [
        CreditDomain(
            domain="授信申请",
            description="用户发起授信申请、提交资料、渠道进入和申请状态流转。",
            common_metrics=["申请量", "审批通过率", "拒绝率", "渠道申请占比"],
            offline_tables=["dws_credit_apply_channel_1d", "ads_credit_daily_metrics"],
            realtime_events=["credit_apply_submitted"],
            risk_notes=["申请明细包含客户标识，明细查询必须做权限校验。"],
        ),
        CreditDomain(
            domain="额度管理",
            description="额度审批、额度调整、额度使用和额度冻结。",
            common_metrics=["授信额度", "额度使用率", "额度冻结数"],
            offline_tables=["dwd_credit_limit_detail_di", "ads_credit_daily_metrics"],
            realtime_events=["credit_limit_changed"],
            risk_notes=["额度明细属于敏感业务数据，不能直接导出客户级明细。"],
        ),
        CreditDomain(
            domain="风控决策",
            description="策略命中、审批拒绝、风险等级和实时反欺诈。",
            common_metrics=["策略命中率", "实时拒绝率", "高风险占比"],
            offline_tables=["ads_risk_strategy_dashboard", "dws_credit_apply_channel_1d"],
            realtime_events=["risk_decision_made"],
            risk_notes=["策略和规则解释必须引用口径资料，不能编造原因。"],
        ),
        CreditDomain(
            domain="放款",
            description="放款申请、放款成功、放款失败和放款金额。",
            common_metrics=["放款金额", "放款成功率", "放款失败数"],
            offline_tables=["ads_credit_daily_metrics", "dwd_loan_disbursement_detail_di"],
            realtime_events=["loan_disbursed", "loan_disbursement_failed"],
            risk_notes=["放款明细涉及合同和资金信息，必须限制权限和 limit。"],
        ),
        CreditDomain(
            domain="还款",
            description="主动还款、自动扣款、还款失败和渠道异常。",
            common_metrics=["还款成功率", "还款失败数", "失败原因分布"],
            offline_tables=["dws_repayment_overdue_1d", "dwd_loan_repayment_detail_di"],
            realtime_events=["repayment_succeeded", "repayment_failed"],
            risk_notes=["还款流水涉及交易明细，敏感导出必须阻断。"],
        ),
        CreditDomain(
            domain="逾期贷后",
            description="逾期天数、账龄、M1/M2、贷后表现和催收前置分析。",
            common_metrics=["逾期率", "M1 余额", "迁徙率", "回收率"],
            offline_tables=["dws_repayment_overdue_1d", "ads_postloan_daily_metrics"],
            realtime_events=["overdue_status_changed"],
            risk_notes=["逾期客户名单属于敏感明细，不能直接给普通用户导出。"],
        ),
        CreditDomain(
            domain="催收",
            description="催收触达、承诺还款、催收结果和坐席效果。",
            common_metrics=["触达率", "承诺还款率", "催回金额"],
            offline_tables=["dwd_collection_action_detail_di", "ads_collection_daily_metrics"],
            realtime_events=["collection_action_created"],
            risk_notes=["催收记录涉及客户沟通信息，必须做权限和审计。"],
        ),
    ]


def build_intent_rules() -> list[IntentRule]:
    """构建意图分类规则。"""

    return [
        IntentRule(
            intent="offline_metric",
            trigger_signals=["昨天", "近 7 天", "上月", "趋势", "按渠道", "按产品", "日报"],
            required_context=["时间范围", "指标", "维度"],
            target_route=[
                "intent_classifier",
                "domain_classifier",
                "offline_layer_router",
                "schema_catalog",
                "offline_sql_generator",
                "sql_validator",
                "offline_query_executor",
                "result_interpreter",
                "audit_logger",
            ],
            fallback="缺少时间范围或指标时进入 clarification。",
        ),
        IntentRule(
            intent="realtime_metric",
            trigger_signals=["近 5 分钟", "当前", "实时", "是否异常", "突增"],
            required_context=["窗口", "业务线或维度", "实时指标"],
            target_route=[
                "intent_classifier",
                "domain_classifier",
                "realtime_router",
                "realtime_metric_tool",
                "delay_checker",
                "result_interpreter",
                "audit_logger",
            ],
            fallback="缺少窗口或维度时进入 clarification。",
        ),
        IntentRule(
            intent="metric_definition",
            trigger_signals=["口径", "怎么算", "定义", "分子", "分母"],
            required_context=["指标名"],
            target_route=["intent_classifier", "domain_classifier", "rag_retriever", "result_interpreter", "audit_logger"],
            fallback="没有可靠引用时返回 insufficient_evidence。",
        ),
        IntentRule(
            intent="lineage",
            trigger_signals=["来自哪些表", "来源", "血缘", "上游", "下游"],
            required_context=["指标或表名"],
            target_route=["intent_classifier", "domain_classifier", "lineage_tool", "result_interpreter", "audit_logger"],
            fallback="找不到血缘时返回资料不足。",
        ),
        IntentRule(
            intent="sensitive_export",
            trigger_signals=["导出", "手机号", "身份证", "客户名单", "银行卡", "明细全部"],
            required_context=["用户权限"],
            target_route=["intent_classifier", "domain_classifier", "permission_checker", "safe_block", "audit_logger"],
            fallback="默认安全阻断。",
        ),
    ]


def build_classification_cases() -> list[ClassificationCase]:
    """构建用户问题分类样例。"""

    return [
        ClassificationCase(
            case_id="D49-001",
            user_question="近 7 天各渠道授信通过率趋势。",
            domain="授信申请",
            intent="offline_metric",
            expected_route=["intent_classifier", "domain_classifier", "offline_layer_router", "schema_catalog", "offline_sql_generator", "sql_validator", "offline_query_executor", "result_interpreter", "audit_logger"],
            reason="历史趋势和渠道维度属于离线指标查询。",
            risk_level="low",
        ),
        ClassificationCase(
            case_id="D49-002",
            user_question="近 5 分钟 STR_BLACKLIST 策略拒绝率是否异常？",
            domain="风控决策",
            intent="realtime_metric",
            expected_route=["intent_classifier", "domain_classifier", "realtime_router", "realtime_metric_tool", "delay_checker", "result_interpreter", "audit_logger"],
            reason="近 5 分钟和是否异常是实时窗口信号。",
            risk_level="medium",
        ),
        ClassificationCase(
            case_id="D49-003",
            user_question="审批通过率的分子和分母分别是什么？",
            domain="授信申请",
            intent="metric_definition",
            expected_route=["intent_classifier", "domain_classifier", "rag_retriever", "result_interpreter", "audit_logger"],
            reason="询问指标口径，应走 RAG 口径问答并返回引用。",
            risk_level="low",
        ),
        ClassificationCase(
            case_id="D49-004",
            user_question="逾期率来自哪些上游表和下游报表？",
            domain="逾期贷后",
            intent="lineage",
            expected_route=["intent_classifier", "domain_classifier", "lineage_tool", "result_interpreter", "audit_logger"],
            reason="询问来源和下游影响范围，应走血缘工具。",
            risk_level="low",
        ),
        ClassificationCase(
            case_id="D49-005",
            user_question="导出所有逾期客户的手机号和身份证号。",
            domain="逾期贷后",
            intent="sensitive_export",
            expected_route=["intent_classifier", "domain_classifier", "permission_checker", "safe_block", "audit_logger"],
            reason="客户敏感明细导出必须阻断并审计。",
            risk_level="high",
        ),
        ClassificationCase(
            case_id="D49-006",
            user_question="看一下还款失败是不是异常。",
            domain="还款",
            intent="clarification_required",
            expected_route=["intent_classifier", "domain_classifier", "clarification", "audit_logger"],
            reason="缺少窗口、渠道和判断口径，不能直接查实时或离线指标。",
            risk_level="medium",
        ),
    ]


def build_mermaid() -> str:
    """生成主题域和意图路由图。"""

    return "\n".join(
        [
            "flowchart LR",
            "    question[用户问题] --> intent[intent_classifier]",
            "    intent --> domain[domain_classifier\\n授信/额度/风控/放款/还款/逾期/催收]",
            "    domain --> offline{离线指标?}",
            "    domain --> realtime{实时状态?}",
            "    domain --> definition{口径解释?}",
            "    domain --> lineage{血缘追溯?}",
            "    domain --> sensitive{敏感导出?}",
            "    offline --> offline_route[ADS/DWS 路由 + SQL 校验]",
            "    realtime --> realtime_route[实时工具 + 延迟检查]",
            "    definition --> rag[RAG 口径问答 + 引用]",
            "    lineage --> lineagetool[血缘工具]",
            "    sensitive --> block[安全阻断 + 审计]",
            "    offline_route --> audit[audit_logger]",
            "    realtime_route --> audit",
            "    rag --> audit",
            "    lineagetool --> audit",
            "    block --> audit",
        ]
    ) + "\n"


def build_report(
    domains: list[CreditDomain],
    rules: list[IntentRule],
    cases: list[ClassificationCase],
) -> str:
    """生成 Day 49 主题域和意图分类报告。"""

    intent_counts = Counter(case.intent for case in cases)
    lines = [
        "# Day 49 信贷主题域与 Agent 意图识别报告",
        "",
        "## 信贷主题域目录",
        "",
        "| 主题域 | 说明 | 常见指标 | 主要离线表 | 实时事件 |",
        "|--------|------|----------|------------|----------|",
    ]
    for domain in domains:
        lines.append(
            f"| {domain.domain} | {domain.description} | {', '.join(domain.common_metrics)} | "
            f"{', '.join(domain.offline_tables)} | {', '.join(domain.realtime_events)} |"
        )

    lines.extend(
        [
            "",
            "## 意图分类规则",
            "",
            "| 意图 | 触发信号 | 必要上下文 | 兜底策略 |",
            "|------|----------|------------|----------|",
        ]
    )
    for rule in rules:
        lines.append(
            f"| {rule.intent} | {', '.join(rule.trigger_signals)} | "
            f"{', '.join(rule.required_context)} | {rule.fallback} |"
        )

    lines.extend(
        [
            "",
            "## 样例分类结果",
            "",
            "| Case | 用户问题 | 主题域 | 意图 | 风险 | 路由原因 |",
            "|------|----------|--------|------|------|----------|",
        ]
    )
    for case in cases:
        lines.append(
            f"| {case.case_id} | {case.user_question} | {case.domain} | "
            f"{case.intent} | {case.risk_level} | {case.reason} |"
        )

    lines.extend(
        [
            "",
            "## 意图分布",
            "",
            "| 意图 | 数量 |",
            "|------|------|",
        ]
    )
    for intent, count in sorted(intent_counts.items()):
        lines.append(f"| {intent} | {count} |")

    lines.extend(
        [
            "",
            "## 生产启示",
            "",
            "- Agent 先识别主题域，再识别意图，最后才能选择工具路线。",
            "- 离线、实时、口径、血缘和敏感导出是完全不同的处理路径。",
            "- 意图不清或缺少必要上下文时，正确行为是澄清，不是猜测。",
            "- 敏感导出不进入 SQL、实时事件或导出工具，必须安全阻断并审计。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """生成 Day 49 主题域和意图识别产物。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    domains = build_domain_catalog()
    rules = build_intent_rules()
    cases = build_classification_cases()

    DOMAIN_CATALOG_PATH.write_text(
        json.dumps([asdict(domain) for domain in domains], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    INTENT_RULES_PATH.write_text(
        json.dumps([asdict(rule) for rule in rules], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    CLASSIFICATION_CASES_PATH.write_text(
        json.dumps([asdict(case) for case in cases], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    MERMAID_PATH.write_text(build_mermaid(), encoding="utf-8")
    REPORT_PATH.write_text(build_report(domains, rules, cases), encoding="utf-8")

    print(f"domains={len(domains)}")
    print(f"intent_rules={len(rules)}")
    print(f"classification_cases={len(cases)}")
    print(f"domain_catalog={DOMAIN_CATALOG_PATH}")
    print(f"intent_rules_path={INTENT_RULES_PATH}")
    print(f"cases_path={CLASSIFICATION_CASES_PATH}")
    print(f"diagram={MERMAID_PATH}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
