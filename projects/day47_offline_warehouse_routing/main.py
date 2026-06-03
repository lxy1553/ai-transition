"""Day 47 - 信贷离线仓库分层与 Agent 离线路由练习。

这个脚本不连接真实数据库，而是用一组模拟的信贷离线仓库表和用户问题，
演示 Agent 在查询离线指标时应该如何选择 ODS、DWD、DWS、ADS 的入口。
生产里不能让 Agent 看到表名就随便查，必须先理解表层级、粒度、分区、权限和指标口径。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
LAYER_CATALOG_PATH = OUTPUT_DIR / "offline_layer_catalog.json"
ROUTING_CASES_PATH = OUTPUT_DIR / "offline_agent_routing_cases.json"
MERMAID_PATH = OUTPUT_DIR / "offline_warehouse_layering.mmd"
REPORT_PATH = OUTPUT_DIR / "offline_warehouse_routing_report.md"


@dataclass(frozen=True)
class WarehouseTable:
    """描述一张离线仓库表的生产关键信息。

    Agent 选择表时不能只看表名，还要看表层级、业务粒度、分区字段、权限级别和是否适合直接查询。
    """

    layer: str
    table_name: str
    subject: str
    grain: str
    partition_key: str
    sensitive_level: str
    agent_usage: str
    example_fields: list[str]


@dataclass(frozen=True)
class RoutingCase:
    """描述一个用户问题应该进入哪条离线查询路线。"""

    case_id: str
    user_question: str
    intent: str
    expected_layer: str
    expected_table: str
    route: list[str]
    reason: str
    forbidden_layers: list[str]


def build_layer_catalog() -> list[WarehouseTable]:
    """构建金融信贷离线仓库四层示例。"""

    return [
        WarehouseTable(
            layer="ODS",
            table_name="ods_credit_apply_raw_di",
            subject="授信申请",
            grain="一条原始授信申请记录",
            partition_key="dt",
            sensitive_level="high",
            agent_usage="不建议 Agent 直接查询；只用于排查明细和上游来源。",
            example_fields=["apply_id", "customer_id", "mobile_hash", "apply_time", "raw_channel"],
        ),
        WarehouseTable(
            layer="ODS",
            table_name="ods_repayment_raw_di",
            subject="还款流水",
            grain="一条原始还款流水",
            partition_key="dt",
            sensitive_level="high",
            agent_usage="不建议直接查；涉及客户、银行卡和交易明细。",
            example_fields=["repay_id", "loan_id", "customer_id", "repay_amount", "repay_status"],
        ),
        WarehouseTable(
            layer="DWD",
            table_name="dwd_credit_apply_detail_di",
            subject="授信申请",
            grain="清洗后的授信申请明细",
            partition_key="dt",
            sensitive_level="medium",
            agent_usage="只在需要明细过滤且有权限时使用，必须带时间范围和 limit。",
            example_fields=["apply_id", "customer_type", "channel", "risk_grade", "apply_status"],
        ),
        WarehouseTable(
            layer="DWD",
            table_name="dwd_loan_repayment_detail_di",
            subject="还款",
            grain="清洗后的还款明细",
            partition_key="dt",
            sensitive_level="medium",
            agent_usage="用于还款明细分析；普通指标优先走 DWS 或 ADS。",
            example_fields=["loan_id", "repay_date", "repay_amount", "overdue_days", "repay_status"],
        ),
        WarehouseTable(
            layer="DWS",
            table_name="dws_credit_apply_channel_1d",
            subject="授信经营",
            grain="按日期、渠道汇总的授信申请指标",
            partition_key="dt",
            sensitive_level="low",
            agent_usage="适合 Agent 查询渠道维度的申请量、通过率和拒绝率。",
            example_fields=["dt", "channel", "apply_cnt", "approve_cnt", "reject_cnt"],
        ),
        WarehouseTable(
            layer="DWS",
            table_name="dws_repayment_overdue_1d",
            subject="贷后还款",
            grain="按日期、产品汇总的还款和逾期指标",
            partition_key="dt",
            sensitive_level="low",
            agent_usage="适合 Agent 查询逾期率、还款成功率和贷后趋势。",
            example_fields=["dt", "product_code", "due_cnt", "repaid_cnt", "overdue_cnt"],
        ),
        WarehouseTable(
            layer="ADS",
            table_name="ads_credit_daily_metrics",
            subject="信贷日报",
            grain="面向经营日报的一天一行应用指标",
            partition_key="dt",
            sensitive_level="low",
            agent_usage="Agent 查询经营日报、总览指标和趋势时的首选入口。",
            example_fields=["dt", "apply_cnt", "approve_rate", "loan_amount", "overdue_rate"],
        ),
        WarehouseTable(
            layer="ADS",
            table_name="ads_risk_strategy_dashboard",
            subject="风控看板",
            grain="按日期、策略、产品汇总的风控看板指标",
            partition_key="dt",
            sensitive_level="low",
            agent_usage="适合 Agent 查询策略命中率、拒绝率和风险看板指标。",
            example_fields=["dt", "strategy_id", "hit_cnt", "reject_rate", "approve_rate"],
        ),
    ]


def build_routing_cases() -> list[RoutingCase]:
    """构建 Agent 离线查询路由样例。"""

    return [
        RoutingCase(
            case_id="D47-001",
            user_question="昨天信贷整体申请量、审批通过率和放款金额是多少？",
            intent="offline_summary_metric",
            expected_layer="ADS",
            expected_table="ads_credit_daily_metrics",
            route=[
                "intent_classifier",
                "offline_layer_router",
                "schema_catalog",
                "offline_sql_generator",
                "sql_validator",
                "offline_query_executor",
                "result_interpreter",
                "audit_logger",
            ],
            reason="经营日报总览优先走 ADS 应用指标表，避免从明细层临时聚合。",
            forbidden_layers=["ODS", "DWD"],
        ),
        RoutingCase(
            case_id="D47-002",
            user_question="近 7 天各渠道授信通过率趋势。",
            intent="offline_dimensional_metric",
            expected_layer="DWS",
            expected_table="dws_credit_apply_channel_1d",
            route=[
                "intent_classifier",
                "offline_layer_router",
                "schema_catalog",
                "offline_sql_generator",
                "sql_validator",
                "offline_query_executor",
                "result_interpreter",
                "audit_logger",
            ],
            reason="按渠道分析需要 DWS 汇总层，既保留维度又避免扫描申请明细。",
            forbidden_layers=["ODS"],
        ),
        RoutingCase(
            case_id="D47-003",
            user_question="查一下某个申请 ID 的审批状态和风险等级。",
            intent="authorized_detail_lookup",
            expected_layer="DWD",
            expected_table="dwd_credit_apply_detail_di",
            route=[
                "intent_classifier",
                "permission_checker",
                "schema_catalog",
                "offline_sql_generator",
                "sql_validator",
                "offline_query_executor",
                "audit_logger",
            ],
            reason="单笔申请明细需要 DWD，但必须先做权限校验、精确过滤和 limit。",
            forbidden_layers=["ODS"],
        ),
        RoutingCase(
            case_id="D47-004",
            user_question="导出昨天所有申请人的手机号和身份证号。",
            intent="sensitive_export",
            expected_layer="blocked",
            expected_table="none",
            route=["intent_classifier", "permission_checker", "safe_block", "audit_logger"],
            reason="敏感明细导出不允许进入离线 SQL 查询链路。",
            forbidden_layers=["ODS", "DWD", "DWS", "ADS"],
        ),
        RoutingCase(
            case_id="D47-005",
            user_question="上个月各产品逾期率变化。",
            intent="offline_postloan_metric",
            expected_layer="DWS",
            expected_table="dws_repayment_overdue_1d",
            route=[
                "intent_classifier",
                "offline_layer_router",
                "schema_catalog",
                "offline_sql_generator",
                "sql_validator",
                "offline_query_executor",
                "result_interpreter",
                "audit_logger",
            ],
            reason="贷后产品维度趋势适合 DWS 还款逾期汇总层。",
            forbidden_layers=["ODS", "DWD"],
        ),
    ]


def build_mermaid(tables: list[WarehouseTable]) -> str:
    """生成离线仓库分层 Mermaid 图。"""

    layer_to_tables: dict[str, list[str]] = {"ODS": [], "DWD": [], "DWS": [], "ADS": []}
    for table in tables:
        layer_to_tables[table.layer].append(table.table_name)

    lines = [
        "flowchart LR",
        "    source[业务系统\\n授信/风控/放款/还款] --> ods[ODS 原始数据层]",
        "    ods --> dwd[DWD 明细事实层]",
        "    dwd --> dws[DWS 主题汇总层]",
        "    dws --> ads[ADS 应用指标层]",
        "    ads --> agent[Agent 离线指标问答]",
        "    dws --> agent",
        "    dwd -. 权限校验后明细查询 .-> agent",
        "    ods -. 默认禁止直接查询 .-> guard[安全阻断/人工排查]",
    ]
    for layer, node in [("ODS", "ods"), ("DWD", "dwd"), ("DWS", "dws"), ("ADS", "ads")]:
        label = "\\n".join(layer_to_tables[layer])
        lines.append(f"    {node}:::layer")
        lines.append(f"    {node}_tables[{label}]:::table")
        lines.append(f"    {node} --> {node}_tables")
    lines.extend(
        [
            "    classDef layer fill:#eef6ff,stroke:#2f6f9f,color:#102a43;",
            "    classDef table fill:#f7f7f2,stroke:#8a7f5a,color:#2d2a22;",
        ]
    )
    return "\n".join(lines) + "\n"


def build_report(tables: list[WarehouseTable], cases: list[RoutingCase]) -> str:
    """生成 Day 47 练习报告。"""

    lines = [
        "# Day 47 信贷离线仓库分层与 Agent 离线路由报告",
        "",
        "## 分层原则",
        "",
        "- ODS 保留业务原始数据，默认不作为 Agent 查询入口。",
        "- DWD 是清洗后的明细事实层，只在有权限、精确过滤和 limit 时查询。",
        "- DWS 是主题汇总层，适合维度分析、趋势分析和指标聚合。",
        "- ADS 是应用指标层，适合经营日报、看板总览和高频问答。",
        "- Agent 查询离线指标时优先 ADS/DWS，避免直接扫 ODS/DWD 明细。",
        "",
        "## 分层表清单",
        "",
        "| 层级 | 表名 | 主题 | 粒度 | Agent 用法 |",
        "|------|------|------|------|------------|",
    ]
    for table in tables:
        lines.append(
            f"| {table.layer} | {table.table_name} | {table.subject} | "
            f"{table.grain} | {table.agent_usage} |"
        )

    lines.extend(
        [
            "",
            "## Agent 离线路由样例",
            "",
            "| Case | 用户问题 | 预期层级 | 预期表 | 路由原因 |",
            "|------|----------|----------|--------|----------|",
        ]
    )
    for case in cases:
        lines.append(
            f"| {case.case_id} | {case.user_question} | {case.expected_layer} | "
            f"{case.expected_table} | {case.reason} |"
        )

    lines.extend(
        [
            "",
            "## 生产启示",
            "",
            "- 离线指标问答不是让 Agent 随便挑表，而是先判断问题粒度和指标用途。",
            "- 总览指标优先 ADS，维度趋势优先 DWS，明细问题必须先过权限和精确过滤。",
            "- ODS 和 DWD 通常包含敏感明细，不能作为普通业务问答的默认入口。",
            "- SQL Validator 要检查分区、limit、只读、敏感字段和扫描成本。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """生成 Day 47 的离线仓库分层和 Agent 路由产物。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tables = build_layer_catalog()
    cases = build_routing_cases()

    LAYER_CATALOG_PATH.write_text(
        json.dumps([asdict(table) for table in tables], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ROUTING_CASES_PATH.write_text(
        json.dumps([asdict(case) for case in cases], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    MERMAID_PATH.write_text(build_mermaid(tables), encoding="utf-8")
    REPORT_PATH.write_text(build_report(tables, cases), encoding="utf-8")

    print(f"tables={len(tables)}")
    print(f"routing_cases={len(cases)}")
    print(f"catalog={LAYER_CATALOG_PATH}")
    print(f"cases={ROUTING_CASES_PATH}")
    print(f"diagram={MERMAID_PATH}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
