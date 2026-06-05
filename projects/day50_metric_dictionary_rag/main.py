"""Day 50 - 指标字典与 RAG 口径问答练习。

这个脚本不连接真实大模型，而是用规则版 RAG 演示：先把离线指标和实时指标整理成
可检索的指标字典，再根据用户口径问题召回相关指标，并返回分子、分母、窗口、来源表、
适用范围和引用。生产里口径解释应该走 RAG 或指标平台，而不是直接生成 SQL 查表。
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
METRIC_DICTIONARY_PATH = OUTPUT_DIR / "metric_dictionary.json"
RAG_CHUNKS_PATH = OUTPUT_DIR / "metric_rag_chunks.json"
QA_CASES_PATH = OUTPUT_DIR / "metric_rag_qa_cases.json"
EVAL_RESULTS_PATH = OUTPUT_DIR / "metric_rag_eval_results.json"
REPORT_PATH = OUTPUT_DIR / "metric_dictionary_rag_report.md"


@dataclass(frozen=True)
class MetricDefinition:
    """描述一个可被 RAG 口径问答引用的指标。

    指标字典必须写清分子、分母、窗口和限制。否则 Agent 只能回答“通过率就是通过数除以申请数”
    这类空泛说法，无法支撑生产里的口径对齐和审计追溯。
    """

    metric_id: str
    metric_name: str
    metric_type: str
    domain: str
    definition: str
    numerator: str
    denominator: str
    time_window: str
    grain: str
    source_table_or_event: str
    dimensions: list[str]
    security_level: str
    owner: str
    usage_notes: list[str]
    aliases: list[str]


@dataclass(frozen=True)
class RagChunk:
    """指标字典被切分后的检索单元。"""

    chunk_id: str
    metric_id: str
    title: str
    text: str
    source: str
    security_level: str
    keywords: list[str]


@dataclass(frozen=True)
class QaCase:
    """一条口径问答样例和评测预期。"""

    case_id: str
    question: str
    expected_metric_id: str
    expected_status: str
    expected_must_contain: list[str]


@dataclass(frozen=True)
class QaAnswer:
    """RAG 口径问答结果。"""

    case_id: str
    question: str
    final_status: str
    matched_metric_id: str
    answer: str
    citations: list[dict[str, str]]


def build_metric_dictionary() -> list[MetricDefinition]:
    """构建离线指标和实时指标字典。"""

    return [
        MetricDefinition(
            metric_id="credit_apply_cnt_1d",
            metric_name="授信申请量",
            metric_type="offline",
            domain="授信申请",
            definition="统计指定日期或日期范围内提交授信申请的申请单数量。",
            numerator="符合时间范围和过滤条件的授信申请单数。",
            denominator="无分母，计数型指标。",
            time_window="离线 T+1 日分区，按 dt 统计。",
            grain="dt + channel + product",
            source_table_or_event="dws_credit_apply_channel_1d",
            dimensions=["dt", "channel", "product", "city", "customer_type"],
            security_level="internal",
            owner="credit_data_team",
            usage_notes=["适合回答昨天、近 7 天、上月的申请量趋势。", "必须带时间范围，避免扫描全量分区。"],
            aliases=["申请量", "授信量", "进件量"],
        ),
        MetricDefinition(
            metric_id="credit_approval_rate_1d",
            metric_name="授信通过率",
            metric_type="offline",
            domain="授信申请",
            definition="审批通过申请数占授信申请总数的比例，分母包含拒绝和待处理申请。",
            numerator="approved_cnt，审批状态为 APPROVED 的申请数。",
            denominator="apply_cnt，统计时间范围内的授信申请总数。",
            time_window="离线 T+1 日分区，按 dt 或日期范围统计。",
            grain="dt + channel + product",
            source_table_or_event="dws_credit_apply_channel_1d / ads_credit_daily_metrics",
            dimensions=["dt", "channel", "product", "risk_grade"],
            security_level="internal",
            owner="metric_platform_team",
            usage_notes=["不能和放款成功率混用。", "渠道趋势优先查 DWS，总览优先查 ADS。"],
            aliases=["通过率", "审批通过率", "授信审批通过率"],
        ),
        MetricDefinition(
            metric_id="loan_amount_1d",
            metric_name="放款金额",
            metric_type="offline",
            domain="放款",
            definition="审批通过并实际放款成功的金额总和。",
            numerator="sum(loan_amount)，放款成功金额累计。",
            denominator="无分母，金额型指标。",
            time_window="离线 T+1 日分区，按放款成功日期 dt 统计。",
            grain="dt + channel + product",
            source_table_or_event="ads_credit_daily_metrics / dwd_loan_disbursement_detail_di",
            dimensions=["dt", "channel", "product", "city"],
            security_level="internal",
            owner="loan_data_team",
            usage_notes=["按放款成功时间统计，不按授信申请时间统计。", "明细层包含合同和资金信息，普通 Agent 不应直接查明细。"],
            aliases=["放款额", "放款金额", "放款规模"],
        ),
        MetricDefinition(
            metric_id="m1_overdue_rate_1d",
            metric_name="M1 逾期率",
            metric_type="offline",
            domain="逾期贷后",
            definition="到期贷款中逾期天数大于等于 30 天的贷款笔数占比。",
            numerator="m1_overdue_cnt，overdue_days >= 30 的到期贷款笔数。",
            denominator="due_loan_cnt，统计范围内到期贷款总笔数。",
            time_window="离线 T+1 日分区，按还款到期日或贷后统计日 dt 统计。",
            grain="dt + product + collection_queue",
            source_table_or_event="dws_repayment_overdue_1d / ads_postloan_daily_metrics",
            dimensions=["dt", "product", "collection_queue", "overdue_bucket"],
            security_level="internal",
            owner="postloan_data_team",
            usage_notes=["M1 是账龄口径，不等于任意逾期。", "客户名单和手机号属于敏感明细，口径问答不能返回明细。"],
            aliases=["M1", "M1逾期率", "逾期率"],
        ),
        MetricDefinition(
            metric_id="rt_risk_reject_rate_10m",
            metric_name="实时风控拒绝率",
            metric_type="realtime",
            domain="风控决策",
            definition="实时窗口内风控拒绝事件数占风控决策事件总数的比例。",
            numerator="reject_event_cnt，窗口内 decision_result = reject 的风控决策事件数。",
            denominator="risk_decision_event_cnt，窗口内风控决策事件总数。",
            time_window="实时 10 分钟滚动窗口，按事件时间聚合，延迟阈值 3 分钟。",
            grain="window_start + strategy_id + product",
            source_table_or_event="risk_decision_made event / rt_risk_reject_rate_10m",
            dimensions=["strategy_id", "product", "channel", "risk_grade"],
            security_level="internal",
            owner="risk_realtime_team",
            usage_notes=["必须返回窗口和延迟状态。", "链路延迟超过阈值时不能给出当前异常结论。"],
            aliases=["实时拒绝率", "风控拒绝率", "策略拒绝率"],
        ),
        MetricDefinition(
            metric_id="rt_repayment_failed_cnt_5m",
            metric_name="实时还款失败数",
            metric_type="realtime",
            domain="还款",
            definition="实时窗口内还款失败事件数量。",
            numerator="repayment_failed_event_cnt，窗口内还款失败事件数。",
            denominator="无分母，计数型实时指标。",
            time_window="实时 5 分钟滚动窗口，按事件时间聚合，延迟阈值 2 分钟。",
            grain="window_start + repay_channel + failure_code",
            source_table_or_event="repayment_failed event / rt_repayment_failed_cnt_5m",
            dimensions=["repay_channel", "failure_code", "product"],
            security_level="internal",
            owner="payment_realtime_team",
            usage_notes=["适合告警解释和实时状态查询。", "不能导出失败客户明细。"],
            aliases=["还款失败数", "实时还款失败", "扣款失败数"],
        ),
    ]


def build_chunks(metrics: list[MetricDefinition]) -> list[RagChunk]:
    """把指标字典转成 RAG 检索 chunk。"""

    chunks: list[RagChunk] = []
    for metric in metrics:
        text = (
            f"指标：{metric.metric_name}。类型：{metric.metric_type}。主题域：{metric.domain}。"
            f"定义：{metric.definition} 分子：{metric.numerator} 分母：{metric.denominator} "
            f"窗口：{metric.time_window} 粒度：{metric.grain} 来源：{metric.source_table_or_event} "
            f"维度：{', '.join(metric.dimensions)} 使用注意：{'；'.join(metric.usage_notes)}"
        )
        keywords = [metric.metric_name, metric.metric_id, metric.domain, *metric.aliases, *metric.dimensions]
        chunks.append(
            RagChunk(
                chunk_id=f"metric::{metric.metric_id}",
                metric_id=metric.metric_id,
                title=f"{metric.metric_name} 指标口径",
                text=text,
                source="metric_dictionary.json",
                security_level=metric.security_level,
                keywords=keywords,
            )
        )
    return chunks


def build_qa_cases() -> list[QaCase]:
    """构建口径问答评测样例。"""

    return [
        QaCase(
            case_id="D50-001",
            question="授信通过率的分子和分母分别是什么？",
            expected_metric_id="credit_approval_rate_1d",
            expected_status="answered",
            expected_must_contain=["approved_cnt", "apply_cnt", "分母"],
        ),
        QaCase(
            case_id="D50-002",
            question="M1 逾期率怎么算？是不是所有逾期都算 M1？",
            expected_metric_id="m1_overdue_rate_1d",
            expected_status="answered",
            expected_must_contain=["overdue_days >= 30", "due_loan_cnt", "账龄"],
        ),
        QaCase(
            case_id="D50-003",
            question="实时风控拒绝率的窗口和延迟阈值是什么？",
            expected_metric_id="rt_risk_reject_rate_10m",
            expected_status="answered",
            expected_must_contain=["10 分钟", "延迟阈值 3 分钟", "事件时间"],
        ),
        QaCase(
            case_id="D50-004",
            question="放款金额按什么时间统计？",
            expected_metric_id="loan_amount_1d",
            expected_status="answered",
            expected_must_contain=["放款成功日期", "loan_amount", "不按授信申请时间"],
        ),
        QaCase(
            case_id="D50-005",
            question="导出 M1 逾期客户手机号和身份证号。",
            expected_metric_id="none",
            expected_status="safely_blocked",
            expected_must_contain=["敏感明细", "阻断"],
        ),
        QaCase(
            case_id="D50-006",
            question="还款失败数的实时窗口是多少？",
            expected_metric_id="rt_repayment_failed_cnt_5m",
            expected_status="answered",
            expected_must_contain=["5 分钟", "repayment_failed", "延迟阈值 2 分钟"],
        ),
    ]


def retrieve_metric(question: str, chunks: list[RagChunk]) -> RagChunk | None:
    """用关键词打分模拟 RAG 检索。

    这里不做向量检索，目的是突出指标字典的结构和 citation。
    真实生产可以替换为 BM25、向量检索和 rerank。
    """

    if contains_sensitive_request(question):
        return None
    scores: Counter[str] = Counter()
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    for chunk in chunks:
        for keyword in chunk.keywords:
            if keyword and keyword in question:
                scores[chunk.chunk_id] += 3
        if "分子" in question or "分母" in question or "怎么算" in question or "口径" in question:
            scores[chunk.chunk_id] += 1
        if "实时" in question and "实时" in chunk.text:
            scores[chunk.chunk_id] += 2
        if "窗口" in question and "窗口" in chunk.text:
            scores[chunk.chunk_id] += 1
        if "延迟" in question and "延迟" in chunk.text:
            scores[chunk.chunk_id] += 1
    if not scores:
        return None
    best_id, score = scores.most_common(1)[0]
    if score <= 1:
        return None
    return chunk_by_id[best_id]


def contains_sensitive_request(question: str) -> bool:
    """识别敏感明细导出问题。"""

    return any(word in question for word in ["手机号", "身份证", "客户名单", "导出", "银行卡", "客户明细"])


def answer_question(case: QaCase, metrics: list[MetricDefinition], chunks: list[RagChunk]) -> QaAnswer:
    """回答一条指标口径问题。"""

    if contains_sensitive_request(case.question):
        return QaAnswer(
            case_id=case.case_id,
            question=case.question,
            final_status="safely_blocked",
            matched_metric_id="none",
            answer="该问题涉及客户敏感明细导出，口径问答系统只解释指标定义，不返回手机号、身份证号或客户名单，已阻断并建议走脱敏审批流程。",
            citations=[],
        )

    metric_by_id = {metric.metric_id: metric for metric in metrics}
    chunk = retrieve_metric(case.question, chunks)
    if not chunk:
        return QaAnswer(
            case_id=case.case_id,
            question=case.question,
            final_status="insufficient_evidence",
            matched_metric_id="none",
            answer="当前指标字典没有找到可靠口径资料，不能编造答案。请补充指标名或更新指标字典。",
            citations=[],
        )

    metric = metric_by_id[chunk.metric_id]
    answer = (
        f"{metric.metric_name}口径：{metric.definition} "
        f"分子是 {metric.numerator} 分母是 {metric.denominator} "
        f"时间/窗口口径：{metric.time_window}。"
        f"来源：{metric.source_table_or_event}。"
        f"适用粒度：{metric.grain}。"
        f"注意：{'；'.join(metric.usage_notes)}"
    )
    return QaAnswer(
        case_id=case.case_id,
        question=case.question,
        final_status="answered",
        matched_metric_id=metric.metric_id,
        answer=answer,
        citations=[
            {
                "chunk_id": chunk.chunk_id,
                "metric_id": metric.metric_id,
                "title": chunk.title,
                "source": chunk.source,
            }
        ],
    )


def evaluate_answers(cases: list[QaCase], answers: list[QaAnswer]) -> dict[str, object]:
    """评测口径问答是否命中指标、状态、关键词和引用。"""

    results = []
    answer_by_case = {answer.case_id: answer for answer in answers}
    for case in cases:
        answer = answer_by_case[case.case_id]
        failures: list[str] = []
        if answer.final_status != case.expected_status:
            failures.append("status_mismatch")
        if answer.matched_metric_id != case.expected_metric_id:
            failures.append("metric_mismatch")
        for keyword in case.expected_must_contain:
            if keyword not in answer.answer:
                failures.append(f"missing_keyword:{keyword}")
        if answer.final_status == "answered" and not answer.citations:
            failures.append("missing_citation")
        results.append(
            {
                "case_id": case.case_id,
                "question": case.question,
                "expected_metric_id": case.expected_metric_id,
                "matched_metric_id": answer.matched_metric_id,
                "expected_status": case.expected_status,
                "actual_status": answer.final_status,
                "passed": not failures,
                "failures": failures,
            }
        )
    passed = sum(1 for item in results if item["passed"])
    return {
        "summary": {
            "total_cases": len(results),
            "passed_cases": passed,
            "failed_cases": len(results) - passed,
            "pass_rate": round(passed / len(results), 4),
        },
        "results": results,
    }


def build_report(
    metrics: list[MetricDefinition],
    chunks: list[RagChunk],
    answers: list[QaAnswer],
    eval_payload: dict[str, object],
) -> str:
    """生成 Markdown 报告。"""

    summary = eval_payload["summary"]
    lines = [
        "# Day 50 指标字典与 RAG 口径问答报告",
        "",
        f"- 指标数量：{len(metrics)}",
        f"- RAG chunk 数量：{len(chunks)}",
        f"- 问答样例：{len(answers)}",
        f"- 评测通过率：{summary['pass_rate']}",
        "",
        "## 指标字典",
        "",
        "| 指标 | 类型 | 主题域 | 分子 | 分母 | 窗口/时间口径 | 来源 |",
        "|------|------|--------|------|------|--------------|------|",
    ]
    for metric in metrics:
        lines.append(
            f"| {metric.metric_name} | {metric.metric_type} | {metric.domain} | "
            f"{metric.numerator} | {metric.denominator} | {metric.time_window} | {metric.source_table_or_event} |"
        )

    lines.extend(
        [
            "",
            "## 口径问答样例",
            "",
            "| Case | 问题 | 状态 | 命中指标 | 引用 | 回答摘要 |",
            "|------|------|------|----------|------|----------|",
        ]
    )
    for answer in answers:
        citations = ", ".join(item["chunk_id"] for item in answer.citations) if answer.citations else "无"
        lines.append(
            f"| {answer.case_id} | {answer.question} | {answer.final_status} | "
            f"{answer.matched_metric_id} | {citations} | {answer.answer[:90]} |"
        )

    lines.extend(
        [
            "",
            "## 评测结果",
            "",
            "| Case | 预期状态 | 实际状态 | 预期指标 | 命中指标 | 通过 | 失败原因 |",
            "|------|----------|----------|----------|----------|------|----------|",
        ]
    )
    for item in eval_payload["results"]:
        passed = "是" if item["passed"] else "否"
        failures = ", ".join(item["failures"]) if item["failures"] else "无"
        lines.append(
            f"| {item['case_id']} | {item['expected_status']} | {item['actual_status']} | "
            f"{item['expected_metric_id']} | {item['matched_metric_id']} | {passed} | {failures} |"
        )

    lines.extend(
        [
            "",
            "## 生产启示",
            "",
            "- 口径问题优先走指标字典/RAG，不应该直接生成 SQL。",
            "- 离线指标必须写清分子、分母、时间字段、来源表和适用粒度。",
            "- 实时指标必须写清窗口、事件时间、处理时间、延迟阈值和告警规则。",
            "- 敏感明细导出不是口径问答，必须安全阻断并审计。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """生成 Day 50 本地练习产物。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = build_metric_dictionary()
    chunks = build_chunks(metrics)
    cases = build_qa_cases()
    answers = [answer_question(case, metrics, chunks) for case in cases]
    eval_payload = evaluate_answers(cases, answers)

    METRIC_DICTIONARY_PATH.write_text(
        json.dumps([asdict(metric) for metric in metrics], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    RAG_CHUNKS_PATH.write_text(
        json.dumps([asdict(chunk) for chunk in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    QA_CASES_PATH.write_text(
        json.dumps([asdict(answer) for answer in answers], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    EVAL_RESULTS_PATH.write_text(json.dumps(eval_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(build_report(metrics, chunks, answers, eval_payload), encoding="utf-8")

    print(f"metrics={len(metrics)}")
    print(f"chunks={len(chunks)}")
    print(f"qa_cases={len(cases)}")
    print(f"pass_rate={eval_payload['summary']['pass_rate']}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
