"""金融信贷离线/实时仓库 + Agent 平台核心逻辑。

本文件把一个准生产项目拆成几个可检查的环节：数据接入、数据质量校验、数仓分层、
指标口径加工、实时事件聚合、权限安全、Agent 问答、审计和评测。代码刻意使用标准库，
保证在没有外部服务的本地环境也能复现完整交付链路。
"""

from __future__ import annotations

import csv
import json
import sqlite3
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_DIR / "config"
DATA_DIR = PROJECT_DIR / "data"
EVAL_DIR = PROJECT_DIR / "eval"
OUTPUT_DIR = PROJECT_DIR / "output"
WAREHOUSE_DB = OUTPUT_DIR / "warehouse.sqlite"
AUDIT_LOG = OUTPUT_DIR / "audit_log.jsonl"

SECURITY_ORDER = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}


@dataclass(frozen=True)
class UserContext:
    """描述一次问答的用户上下文。

    Agent 不能只看自然语言问题，还必须知道用户角色、可访问业务域和最高数据密级。
    这决定了后续能不能查指标、看实时告警、返回 SQL 或访问敏感字段。
    """

    role: str
    allowed_domains: list[str]
    max_security_level: str
    can_view_sql: bool
    can_view_realtime: bool
    can_view_customer_detail: bool


class CreditWarehouseAgentPlatform:
    """准生产金融信贷仓库 + Agent 平台。

    这个类负责把本地样例数据转成可问答、可审计、可评测的数仓资产。
    生产环境里同样可以保留这个分层：接入层、治理层、指标层、Agent 层和审计评测层。
    """

    def __init__(self) -> None:
        self.warehouse_catalog = self._load_json(CONFIG_DIR / "warehouse_catalog.json")
        self.metrics_catalog = self._load_json(CONFIG_DIR / "metrics_catalog.json")
        self.access_policy = self._load_json(CONFIG_DIR / "access_policy.json")
        self.agent_routes = self._load_json(CONFIG_DIR / "agent_routes.json")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def run_all(self) -> dict[str, Any]:
        """执行从数据接入到评测的完整闭环。"""

        warehouse_result = self.build_warehouse()
        demo_result = self.run_demo_questions()
        eval_result = self.run_evaluation()
        self._write_delivery_report(warehouse_result, demo_result, eval_result)
        return {
            "warehouse": warehouse_result,
            "demo": {"answers": len(demo_result)},
            "evaluation": eval_result["summary"],
            "outputs": {
                "warehouse_db": str(WAREHOUSE_DB),
                "audit_log": str(AUDIT_LOG),
                "delivery_report": str(OUTPUT_DIR / "delivery_report.md"),
            },
        }

    def build_warehouse(self) -> dict[str, Any]:
        """执行离线和实时数据接入、治理、指标加工。

        这里用 SQLite 模拟准生产仓库：ODS 保存原始接入，DWD 保存清洗事实，
        DWS/ADS 保存指标结果，RT 表保存实时聚合和告警。
        """

        if AUDIT_LOG.exists():
            AUDIT_LOG.unlink()
        applications = self._read_csv(DATA_DIR / "batch" / "credit_applications.csv")
        repayments = self._read_csv(DATA_DIR / "batch" / "repayment_snapshots.csv")
        realtime_events = self._read_jsonl(DATA_DIR / "realtime" / "risk_events.jsonl")
        quality_report = self._validate_data(applications, repayments, realtime_events)

        with self._connect() as conn:
            self._reset_tables(conn)
            self._load_ods(conn, applications, repayments, realtime_events)
            self._build_dwd(conn, applications, repayments)
            self._build_metrics(conn, applications, repayments)
            alerts = self._build_realtime(conn, realtime_events)
            self._load_metadata(conn)

        self._write_quality_report(quality_report)
        self._write_realtime_alerts(alerts)
        return {
            "applications": len(applications),
            "repayments": len(repayments),
            "realtime_events": len(realtime_events),
            "quality_errors": len(quality_report["errors"]),
            "quality_warnings": len(quality_report["warnings"]),
            "alerts": len(alerts),
            "warehouse_db": str(WAREHOUSE_DB),
        }

    def answer_question(self, question: str, role: str = "risk_analyst") -> dict[str, Any]:
        """执行一次受权限控制的 Agent 问答。

        这个 Agent 是规则版，不调用真实 LLM。它重点演示生产 Agent 的受控路线：
        先做安全判断，再做意图路由，再查指标/元数据/实时结果，最后写审计。
        """

        request_id = str(uuid.uuid4())
        user = self._build_user_context(role)
        question = question.strip()
        route = ["security_guard", "intent_router"]

        if not question:
            answer = self._final_answer(
                request_id, "clarification_required", route, "请补充要查询的指标、时间或业务域。"
            )
        elif self._contains_sensitive_request(question) and not user.can_view_customer_detail:
            route.append("safe_block")
            answer = self._final_answer(
                request_id,
                "safely_blocked",
                route,
                "该问题涉及客户明细或敏感个人信息，当前角色不能查询。建议改查汇总指标或走审批脱敏流程。",
            )
        elif self._is_realtime_question(question):
            route.append("realtime_monitor")
            answer = self._answer_realtime(request_id, question, user, route)
        elif self._is_metric_definition_question(question):
            route.append("metric_catalog")
            answer = self._answer_metric_definition(request_id, question, user, route)
        elif self._is_lineage_question(question):
            route.append("lineage_catalog")
            answer = self._answer_lineage(request_id, question, user, route)
        elif self._is_metric_query(question):
            route.append("metric_resolver")
            answer = self._answer_metric_query(request_id, question, user, route)
        else:
            route.append("clarification")
            answer = self._final_answer(
                request_id,
                "clarification_required",
                route,
                "当前问题没有匹配到受支持的指标、实时告警或口径查询。请补充授信、放款、逾期、渠道或时间范围。",
            )

        self._write_audit(question=question, role=role, answer=answer)
        return answer

    def run_demo_questions(self) -> list[dict[str, Any]]:
        """运行内置演示问题，生成作品集可展示答案。"""

        demo_questions = [
            ("本周授信通过率按渠道表现如何？", "risk_analyst"),
            ("放款金额最高的渠道是什么？", "credit_ops"),
            ("M1 逾期率口径是什么？", "collection_agent"),
            ("今天实时高风险事件和告警情况？", "risk_analyst"),
            ("授信通过率的血缘来自哪些表？", "credit_dev"),
            ("导出逾期客户手机号和身份证号", "customer_service"),
        ]
        answers = [self.answer_question(question, role) for question, role in demo_questions]
        (OUTPUT_DIR / "demo_answers.json").write_text(
            json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return answers

    def run_evaluation(self) -> dict[str, Any]:
        """运行固定评测集，检查问答、安全和实时链路是否符合预期。"""

        cases = self._load_json(EVAL_DIR / "eval_cases.json")
        results: list[dict[str, Any]] = []
        for case in cases:
            answer = self.answer_question(case["question"], case["role"])
            failures: list[str] = []
            if answer["final_status"] != case["expected_status"]:
                failures.append("status_mismatch")
            for tool in case.get("required_route_contains", []):
                if tool not in answer["route"]:
                    failures.append(f"missing_route:{tool}")
            if case.get("must_not_expose_sql") and answer.get("sql"):
                failures.append("sql_exposed")
            if case.get("requires_citation") and not answer.get("citations"):
                failures.append("missing_citation")
            results.append(
                {
                    "case_id": case["case_id"],
                    "question": case["question"],
                    "role": case["role"],
                    "expected_status": case["expected_status"],
                    "actual_status": answer["final_status"],
                    "passed": not failures,
                    "failures": failures,
                    "route": answer["route"],
                }
            )

        passed = sum(1 for item in results if item["passed"])
        summary = {
            "total_cases": len(results),
            "passed_cases": passed,
            "failed_cases": len(results) - passed,
            "pass_rate": round(passed / len(results), 4) if results else 0,
        }
        payload = {"summary": summary, "results": results}
        (OUTPUT_DIR / "eval_results.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._write_eval_report(payload)
        return payload

    def _answer_metric_query(
        self, request_id: str, question: str, user: UserContext, route: list[str]
    ) -> dict[str, Any]:
        """回答授信、放款、逾期等离线指标问题。"""

        metric = self._resolve_metric(question)
        if not metric:
            return self._final_answer(
                request_id, "clarification_required", route, "未识别到明确指标，请补充授信通过率、放款金额或 M1 逾期率。"
            )
        metric_def = self.metrics_catalog["metrics"][metric]
        route = route + ["permission_checker"]
        if not self._can_access_security_level(user, metric_def["security_level"]):
            return self._final_answer(
                request_id, "safely_blocked", route + ["audit_logger"], "当前角色无权查看该指标。"
            )
        route = route + ["sql_guard", "warehouse_query", "result_interpreter"]

        with self._connect() as conn:
            if metric in {"credit_apply_cnt", "credit_approval_rate", "loan_amount"}:
                rows = conn.execute(
                    """
                    select dt, channel, apply_cnt, approved_cnt, approval_rate, loan_amount
                    from dws_credit_daily_metrics
                    order by dt, channel
                    """
                ).fetchall()
                answer_text = self._summarize_credit_metrics(metric, rows)
                sql = "select dt, channel, apply_cnt, approved_cnt, approval_rate, loan_amount from dws_credit_daily_metrics"
            else:
                rows = conn.execute(
                    """
                    select dt, product, due_loan_cnt, m1_overdue_cnt, m1_overdue_rate
                    from dws_repayment_overdue_metrics
                    order by dt, product
                    """
                ).fetchall()
                answer_text = self._summarize_overdue_metrics(rows)
                sql = "select dt, product, due_loan_cnt, m1_overdue_cnt, m1_overdue_rate from dws_repayment_overdue_metrics"

        citations = [
            {
                "type": "metric",
                "id": metric,
                "name": metric_def["name"],
                "source_table": metric_def["source_table"],
            }
        ]
        return self._final_answer(
            request_id=request_id,
            final_status="answered",
            route=route + ["audit_logger"],
            answer=answer_text,
            citations=citations,
            sql=sql if user.can_view_sql else None,
        )

    def _answer_metric_definition(
        self, request_id: str, question: str, user: UserContext, route: list[str]
    ) -> dict[str, Any]:
        """回答指标口径问题。"""

        metric = self._resolve_metric(question)
        if not metric:
            return self._final_answer(request_id, "clarification_required", route, "请说明要查看哪个指标口径。")
        metric_def = self.metrics_catalog["metrics"][metric]
        if not self._can_access_security_level(user, metric_def["security_level"]):
            return self._final_answer(request_id, "safely_blocked", route, "当前角色无权查看该指标口径。")
        answer = (
            f"{metric_def['name']}：{metric_def['definition']} "
            f"计算公式：{metric_def['formula']}。来源表：{metric_def['source_table']}。"
        )
        return self._final_answer(
            request_id,
            "answered",
            route + ["audit_logger"],
            answer,
            citations=[{"type": "metric_definition", "id": metric, "source": "metrics_catalog.json"}],
        )

    def _answer_realtime(
        self, request_id: str, question: str, user: UserContext, route: list[str]
    ) -> dict[str, Any]:
        """回答实时风险事件和告警问题。"""

        if not user.can_view_realtime:
            return self._final_answer(request_id, "safely_blocked", route, "当前角色无权查看实时风控事件。")
        with self._connect() as conn:
            rows = conn.execute(
                """
                select event_minute, risk_level, event_type, event_cnt
                from rt_risk_minute_metrics
                order by event_minute, risk_level, event_type
                """
            ).fetchall()
        high_count = sum(row["event_cnt"] for row in rows if row["risk_level"] == "high")
        total = sum(row["event_cnt"] for row in rows)
        alerts = json.loads((OUTPUT_DIR / "realtime_alerts.json").read_text(encoding="utf-8"))
        answer = f"实时链路共接入 {total} 条风控事件，其中 high 风险 {high_count} 条，当前触发 {len(alerts)} 条告警。"
        return self._final_answer(
            request_id,
            "answered",
            route + ["audit_logger"],
            answer,
            citations=[{"type": "realtime_metric", "source": "rt_risk_minute_metrics"}],
        )

    def _answer_lineage(
        self, request_id: str, question: str, user: UserContext, route: list[str]
    ) -> dict[str, Any]:
        """回答表血缘和数仓分层问题。"""

        if "credit_data" not in user.allowed_domains:
            return self._final_answer(request_id, "safely_blocked", route, "当前角色无权查看数仓血缘。")
        metric = self._resolve_metric(question) or "credit_approval_rate"
        metric_def = self.metrics_catalog["metrics"][metric]
        lineage = metric_def["lineage"]
        answer = f"{metric_def['name']} 血缘：{' -> '.join(lineage)}。核心来源表是 {metric_def['source_table']}。"
        return self._final_answer(
            request_id,
            "answered",
            route + ["audit_logger"],
            answer,
            citations=[{"type": "lineage", "metric": metric, "lineage": lineage}],
        )

    def _reset_tables(self, conn: sqlite3.Connection) -> None:
        """重置本地仓库表，保证每次演示结果可复现。"""

        tables = [
            "ods_credit_applications",
            "ods_repayment_snapshots",
            "ods_risk_events",
            "dwd_credit_applications",
            "dwd_repayment_snapshots",
            "dws_credit_daily_metrics",
            "dws_repayment_overdue_metrics",
            "rt_risk_minute_metrics",
            "metric_catalog",
            "warehouse_catalog",
            "audit_events",
        ]
        for table in tables:
            conn.execute(f"drop table if exists {table}")
        conn.executescript(
            """
            create table ods_credit_applications (
                app_id text, customer_id text, channel text, product text, city text,
                apply_time text, decision_time text, status text, approved_amount real,
                loan_amount real, risk_level text, reject_reason text, is_new_customer integer, dt text
            );
            create table ods_repayment_snapshots (
                loan_id text, customer_id text, product text, due_date text, repay_date text,
                overdue_days integer, principal_balance real, paid_amount real, collection_queue text, dt text
            );
            create table ods_risk_events (
                event_id text, event_time text, app_id text, customer_id text, event_type text,
                risk_level text, channel text, decision text, rule_code text
            );
            create table dwd_credit_applications as select * from ods_credit_applications where 0;
            create table dwd_repayment_snapshots as select * from ods_repayment_snapshots where 0;
            create table dws_credit_daily_metrics (
                dt text, channel text, apply_cnt integer, approved_cnt integer,
                approval_rate real, loan_amount real
            );
            create table dws_repayment_overdue_metrics (
                dt text, product text, due_loan_cnt integer, m1_overdue_cnt integer, m1_overdue_rate real
            );
            create table rt_risk_minute_metrics (
                event_minute text, risk_level text, event_type text, event_cnt integer
            );
            create table metric_catalog (
                metric_id text primary key, name text, definition text, formula text,
                source_table text, security_level text
            );
            create table warehouse_catalog (
                table_name text primary key, layer text, domain text, grain text,
                security_level text, owner text
            );
            create table audit_events (
                request_id text, role text, final_status text, route text, created_at text
            );
            """
        )

    def _load_ods(
        self,
        conn: sqlite3.Connection,
        applications: list[dict[str, str]],
        repayments: list[dict[str, str]],
        realtime_events: list[dict[str, Any]],
    ) -> None:
        """把原始批数据和实时事件写入 ODS。"""

        conn.executemany(
            """
            insert into ods_credit_applications values (
                :app_id, :customer_id, :channel, :product, :city, :apply_time, :decision_time,
                :status, :approved_amount, :loan_amount, :risk_level, :reject_reason, :is_new_customer, :dt
            )
            """,
            [self._coerce_application(row) for row in applications],
        )
        conn.executemany(
            """
            insert into ods_repayment_snapshots values (
                :loan_id, :customer_id, :product, :due_date, :repay_date, :overdue_days,
                :principal_balance, :paid_amount, :collection_queue, :dt
            )
            """,
            [self._coerce_repayment(row) for row in repayments],
        )
        conn.executemany(
            """
            insert into ods_risk_events values (
                :event_id, :event_time, :app_id, :customer_id, :event_type,
                :risk_level, :channel, :decision, :rule_code
            )
            """,
            realtime_events,
        )
        conn.commit()

    def _build_dwd(
        self, conn: sqlite3.Connection, applications: list[dict[str, str]], repayments: list[dict[str, str]]
    ) -> None:
        """构建清洗后的 DWD 明细层。"""

        conn.execute(
            """
            insert into dwd_credit_applications
            select * from ods_credit_applications
            where app_id is not null and customer_id is not null and dt is not null
            """
        )
        conn.execute(
            """
            insert into dwd_repayment_snapshots
            select * from ods_repayment_snapshots
            where loan_id is not null and customer_id is not null and dt is not null
            """
        )
        conn.commit()

    def _build_metrics(
        self, conn: sqlite3.Connection, applications: list[dict[str, str]], repayments: list[dict[str, str]]
    ) -> None:
        """加工 DWS 指标层。"""

        conn.execute(
            """
            insert into dws_credit_daily_metrics
            select
                dt,
                channel,
                count(*) as apply_cnt,
                sum(case when status = 'APPROVED' then 1 else 0 end) as approved_cnt,
                round(sum(case when status = 'APPROVED' then 1.0 else 0 end) / count(*), 4) as approval_rate,
                round(sum(loan_amount), 2) as loan_amount
            from dwd_credit_applications
            group by dt, channel
            """
        )
        conn.execute(
            """
            insert into dws_repayment_overdue_metrics
            select
                dt,
                product,
                count(*) as due_loan_cnt,
                sum(case when overdue_days >= 30 then 1 else 0 end) as m1_overdue_cnt,
                round(sum(case when overdue_days >= 30 then 1.0 else 0 end) / count(*), 4) as m1_overdue_rate
            from dwd_repayment_snapshots
            group by dt, product
            """
        )
        conn.commit()

    def _build_realtime(self, conn: sqlite3.Connection, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """聚合实时风控事件并生成告警。

        本地用 JSONL 模拟流事件。生产里可替换成 Kafka/Flink，但告警口径仍应保留：
        按分钟、风险等级、事件类型聚合，并对高风险密集事件触发告警。
        """

        aggregate: Counter[tuple[str, str, str]] = Counter()
        for event in events:
            minute = event["event_time"][:16]
            aggregate[(minute, event["risk_level"], event["event_type"])] += 1
        conn.executemany(
            "insert into rt_risk_minute_metrics values (?, ?, ?, ?)",
            [(minute, risk, event_type, count) for (minute, risk, event_type), count in aggregate.items()],
        )
        conn.commit()

        alerts: list[dict[str, Any]] = []
        for (minute, risk, event_type), count in aggregate.items():
            if risk == "high" and count >= 2:
                alerts.append(
                    {
                        "alert_id": f"ALERT-{minute}-{event_type}",
                        "event_minute": minute,
                        "severity": "P1",
                        "reason": f"{minute} 高风险 {event_type} 事件达到 {count} 条",
                        "recommended_action": "通知风控值班同事复核规则命中和渠道异常。",
                    }
                )
        return alerts

    def _load_metadata(self, conn: sqlite3.Connection) -> None:
        """写入指标和表元数据，支撑 Agent 的口径、血缘和权限回答。"""

        conn.executemany(
            "insert into metric_catalog values (?, ?, ?, ?, ?, ?)",
            [
                (
                    metric_id,
                    item["name"],
                    item["definition"],
                    item["formula"],
                    item["source_table"],
                    item["security_level"],
                )
                for metric_id, item in self.metrics_catalog["metrics"].items()
            ],
        )
        conn.executemany(
            "insert into warehouse_catalog values (?, ?, ?, ?, ?, ?)",
            [
                (
                    item["table_name"],
                    item["layer"],
                    item["domain"],
                    item["grain"],
                    item["security_level"],
                    item["owner"],
                )
                for item in self.warehouse_catalog["tables"]
            ],
        )
        conn.commit()

    def _validate_data(
        self,
        applications: list[dict[str, str]],
        repayments: list[dict[str, str]],
        events: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        """做最小数据质量校验。"""

        errors: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        seen_apps: set[str] = set()
        for row in applications:
            if not row.get("app_id") or not row.get("customer_id") or not row.get("dt"):
                errors.append({"dataset": "applications", "type": "missing_required", "row": row})
            if row["app_id"] in seen_apps:
                errors.append({"dataset": "applications", "type": "duplicate_app_id", "app_id": row["app_id"]})
            seen_apps.add(row["app_id"])
            if float(row["loan_amount"]) > float(row["approved_amount"] or 0):
                warnings.append({"dataset": "applications", "type": "loan_gt_approved", "app_id": row["app_id"]})

        for row in repayments:
            if int(row["overdue_days"]) < 0:
                errors.append({"dataset": "repayments", "type": "negative_overdue_days", "loan_id": row["loan_id"]})

        event_ids = [event["event_id"] for event in events]
        for event_id, count in Counter(event_ids).items():
            if count > 1:
                errors.append({"dataset": "risk_events", "type": "duplicate_event_id", "event_id": event_id})
        return {"errors": errors, "warnings": warnings}

    def _summarize_credit_metrics(self, metric: str, rows: list[sqlite3.Row]) -> str:
        """把授信/放款指标结果解释成业务语言。"""

        if metric == "credit_approval_rate":
            best = max(rows, key=lambda row: row["approval_rate"])
            return (
                f"授信通过率最高的是 {best['dt']} 的 {best['channel']} 渠道，"
                f"通过率 {best['approval_rate']}，申请 {best['apply_cnt']} 笔，通过 {best['approved_cnt']} 笔。"
            )
        if metric == "loan_amount":
            totals: defaultdict[str, float] = defaultdict(float)
            for row in rows:
                totals[row["channel"]] += row["loan_amount"]
            channel, amount = max(totals.items(), key=lambda item: item[1])
            return f"放款金额最高渠道是 {channel}，样例周期累计放款 {round(amount, 2)} 元。"
        total_apply = sum(row["apply_cnt"] for row in rows)
        return f"样例周期共接入授信申请 {total_apply} 笔，可按渠道、日期继续拆分。"

    def _summarize_overdue_metrics(self, rows: list[sqlite3.Row]) -> str:
        """解释 M1 逾期率指标。"""

        worst = max(rows, key=lambda row: row["m1_overdue_rate"])
        return (
            f"M1 逾期率最高的是 {worst['dt']} 的 {worst['product']} 产品，"
            f"到期贷款 {worst['due_loan_cnt']} 笔，M1 逾期 {worst['m1_overdue_cnt']} 笔，"
            f"逾期率 {worst['m1_overdue_rate']}。"
        )

    def _build_user_context(self, role: str) -> UserContext:
        """从权限配置构建用户上下文。"""

        roles = self.access_policy["roles"]
        if role not in roles:
            role = "guest"
        item = roles[role]
        return UserContext(
            role=role,
            allowed_domains=item["allowed_domains"],
            max_security_level=item["max_security_level"],
            can_view_sql=item["can_view_sql"],
            can_view_realtime=item["can_view_realtime"],
            can_view_customer_detail=item["can_view_customer_detail"],
        )

    def _contains_sensitive_request(self, question: str) -> bool:
        """识别敏感字段或明细导出请求。"""

        sensitive_words = self.access_policy["sensitive_keywords"]
        return any(word in question for word in sensitive_words)

    def _is_metric_query(self, question: str) -> bool:
        return any(word in question for word in ["通过率", "放款金额", "申请量", "逾期率", "M1"])

    def _is_metric_definition_question(self, question: str) -> bool:
        return any(word in question for word in ["口径", "怎么算", "定义", "公式"])

    def _is_realtime_question(self, question: str) -> bool:
        return any(word in question for word in ["实时", "告警", "风险事件", "高风险"])

    def _is_lineage_question(self, question: str) -> bool:
        return any(word in question for word in ["血缘", "来自哪些表", "来源表", "数仓分层"])

    def _resolve_metric(self, question: str) -> str | None:
        """根据问题识别指标。"""

        if "通过率" in question:
            return "credit_approval_rate"
        if "放款金额" in question:
            return "loan_amount"
        if "申请量" in question:
            return "credit_apply_cnt"
        if "M1" in question or "逾期率" in question:
            return "m1_overdue_rate"
        if "实时" in question or "风险事件" in question:
            return "realtime_risk_event_cnt"
        return None

    def _can_access_security_level(self, user: UserContext, security_level: str) -> bool:
        return SECURITY_ORDER[user.max_security_level] >= SECURITY_ORDER[security_level]

    def _final_answer(
        self,
        request_id: str,
        final_status: str,
        route: list[str],
        answer: str,
        citations: list[dict[str, Any]] | None = None,
        sql: str | None = None,
    ) -> dict[str, Any]:
        """统一 Agent 响应结构。"""

        return {
            "request_id": request_id,
            "final_status": final_status,
            "route": route,
            "answer": answer,
            "citations": citations or [],
            "sql": sql,
        }

    def _write_audit(self, question: str, role: str, answer: dict[str, Any]) -> None:
        """写审计日志。

        审计日志保留 request_id、角色、问题、路线和最终状态，不写客户明细。
        真实生产里可接日志平台、审计库或安全运营平台。
        """

        event = {
            "request_id": answer["request_id"],
            "role": role,
            "question": question,
            "final_status": answer["final_status"],
            "route": answer["route"],
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        with AUDIT_LOG.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")
        with self._connect() as conn:
            try:
                conn.execute(
                    "insert into audit_events values (?, ?, ?, ?, ?)",
                    (
                        event["request_id"],
                        role,
                        event["final_status"],
                        " -> ".join(event["route"]),
                        event["created_at"],
                    ),
                )
                conn.commit()
            except sqlite3.OperationalError:
                # 如果还没执行 build_warehouse，JSONL 审计仍然可用；避免单独提问被审计表初始化阻塞。
                pass

    def _connect(self) -> sqlite3.Connection:
        """连接本地 SQLite 仓库。"""

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(WAREHOUSE_DB)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_json(self, path: Path) -> Any:
        if not path.exists():
            raise FileNotFoundError(path)
        return json.loads(path.read_text(encoding="utf-8"))

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as file:
            return [json.loads(line) for line in file if line.strip()]

    def _coerce_application(self, row: dict[str, str]) -> dict[str, Any]:
        item = dict(row)
        item["approved_amount"] = float(item["approved_amount"] or 0)
        item["loan_amount"] = float(item["loan_amount"] or 0)
        item["is_new_customer"] = int(item["is_new_customer"])
        return item

    def _coerce_repayment(self, row: dict[str, str]) -> dict[str, Any]:
        item = dict(row)
        item["overdue_days"] = int(item["overdue_days"])
        item["principal_balance"] = float(item["principal_balance"])
        item["paid_amount"] = float(item["paid_amount"])
        return item

    def _write_quality_report(self, report: dict[str, list[dict[str, Any]]]) -> None:
        lines = [
            "# 数据质量报告",
            "",
            f"- 错误数：{len(report['errors'])}",
            f"- 警告数：{len(report['warnings'])}",
            "",
            "## 错误",
            "",
        ]
        if report["errors"]:
            lines.extend(f"- {item}" for item in report["errors"])
        else:
            lines.append("- 无")
        lines.extend(["", "## 警告", ""])
        if report["warnings"]:
            lines.extend(f"- {item}" for item in report["warnings"])
        else:
            lines.append("- 无")
        (OUTPUT_DIR / "data_quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_realtime_alerts(self, alerts: list[dict[str, Any]]) -> None:
        (OUTPUT_DIR / "realtime_alerts.json").write_text(
            json.dumps(alerts, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _write_eval_report(self, payload: dict[str, Any]) -> None:
        lines = [
            "# Agent 评测报告",
            "",
            f"- 测试集数量：{payload['summary']['total_cases']}",
            f"- 通过数量：{payload['summary']['passed_cases']}",
            f"- 失败数量：{payload['summary']['failed_cases']}",
            f"- 通过率：{payload['summary']['pass_rate']}",
            "",
            "| Case | 角色 | 预期 | 实际 | 通过 | 失败原因 |",
            "|------|------|------|------|------|----------|",
        ]
        for item in payload["results"]:
            failures = ", ".join(item["failures"]) if item["failures"] else "无"
            passed = "是" if item["passed"] else "否"
            lines.append(
                f"| {item['case_id']} | {item['role']} | {item['expected_status']} | "
                f"{item['actual_status']} | {passed} | {failures} |"
            )
        (OUTPUT_DIR / "evaluation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_delivery_report(
        self,
        warehouse_result: dict[str, Any],
        demo_result: list[dict[str, Any]],
        eval_result: dict[str, Any],
    ) -> None:
        lines = [
            "# 金融信贷离线/实时仓库 + Agent 交付报告",
            "",
            "## 交付摘要",
            "",
            f"- 离线授信申请：{warehouse_result['applications']} 条",
            f"- 离线还款快照：{warehouse_result['repayments']} 条",
            f"- 实时风控事件：{warehouse_result['realtime_events']} 条",
            f"- 实时告警：{warehouse_result['alerts']} 条",
            f"- Demo 问答：{len(demo_result)} 条",
            f"- 评测通过率：{eval_result['summary']['pass_rate']}",
            "",
            "## 已闭环能力",
            "",
            "- 数据接入：批量 CSV + 实时 JSONL。",
            "- 数仓治理：ODS/DWD/DWS/RT 分层、数据质量报告、元数据目录。",
            "- 指标口径：授信申请量、授信通过率、放款金额、M1 逾期率、实时风险事件。",
            "- 实时链路：按分钟聚合风控事件，并输出 P1 告警。",
            "- 权限安全：角色、数据密级、敏感请求拦截、SQL 暴露开关。",
            "- Agent 问答：指标查询、口径解释、实时告警、血缘查询和安全拒答。",
            "- 审计评测：JSONL + SQLite 审计，固定评测集和 Markdown 报告。",
        ]
        (OUTPUT_DIR / "delivery_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
