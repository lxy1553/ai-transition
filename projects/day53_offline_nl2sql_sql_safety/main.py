"""Day 53 - 离线 NL2SQL 与 SQL 安全练习。

这个脚本模拟金融信贷离线指标查询链路：先把自然语言问题转换成候选 SQL，
再用 SQL Validator 做只读、表层、字段权限、分区、时间范围和扫描成本校验。
只有通过校验的 SQL 才会在本地 SQLite 中执行。
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
DB_PATH = OUTPUT_DIR / "offline_warehouse.sqlite"
CASES_PATH = OUTPUT_DIR / "nl2sql_cases.json"
RESULTS_PATH = OUTPUT_DIR / "nl2sql_eval_results.json"
REPORT_PATH = OUTPUT_DIR / "offline_nl2sql_sql_safety_report.md"


@dataclass(frozen=True)
class TablePolicy:
    """Schema Catalog 中与 SQL 安全相关的表策略。"""

    table_name: str
    layer: str
    domain: str
    partition_field: str
    time_field: str
    allowed_fields: list[str]
    sensitive_fields: list[str]
    max_scan_days: int
    query_role: str


@dataclass(frozen=True)
class Nl2SqlCase:
    """一条离线 NL2SQL 评测样例。"""

    case_id: str
    question: str
    expected_status: str
    expected_reason_contains: list[str]


def build_table_policies() -> dict[str, TablePolicy]:
    """构建最小 Schema Catalog 策略。"""

    return {
        "ads_credit_daily_metrics": TablePolicy(
            table_name="ads_credit_daily_metrics",
            layer="ADS",
            domain="授信申请",
            partition_field="biz_date",
            time_field="biz_date",
            allowed_fields=["biz_date", "channel", "product_code", "apply_cnt", "approved_cnt", "approval_rate", "loan_amount"],
            sensitive_fields=[],
            max_scan_days=31,
            query_role="offline_metric_query",
        ),
        "dws_credit_apply_channel_1d": TablePolicy(
            table_name="dws_credit_apply_channel_1d",
            layer="DWS",
            domain="授信申请",
            partition_field="dt",
            time_field="dt",
            allowed_fields=["dt", "channel", "product_code", "risk_grade", "apply_cnt", "approved_cnt", "rejected_cnt"],
            sensitive_fields=[],
            max_scan_days=31,
            query_role="offline_metric_query",
        ),
        "dwd_credit_apply_detail_di": TablePolicy(
            table_name="dwd_credit_apply_detail_di",
            layer="DWD",
            domain="授信申请",
            partition_field="dt",
            time_field="apply_time",
            allowed_fields=["apply_id", "customer_id", "phone", "id_card", "apply_time", "approve_status", "dt"],
            sensitive_fields=["customer_id", "phone", "id_card"],
            max_scan_days=1,
            query_role="restricted_detail_query",
        ),
    }


def build_cases() -> list[Nl2SqlCase]:
    """构建覆盖成功、澄清和阻断的评测样例。"""

    return [
        Nl2SqlCase("D53-001", "近 7 天各渠道授信通过率是多少？", "executed", ["DWS", "dt", "只读"]),
        Nl2SqlCase("D53-002", "昨天信贷经营日报的申请量和放款金额是多少？", "executed", ["ADS", "biz_date", "只读"]),
        Nl2SqlCase("D53-003", "查看最近 90 天各渠道授信通过率趋势。", "blocked", ["扫描天数", "超过", "31"]),
        Nl2SqlCase("D53-004", "导出昨天所有授信申请客户的手机号和身份证号。", "blocked", ["敏感字段", "DWD", "阻断"]),
        Nl2SqlCase("D53-005", "查一下授信通过率。", "need_clarification", ["缺少时间范围", "澄清"]),
        Nl2SqlCase("D53-006", "删除昨天的授信日报数据。", "blocked", ["非只读", "阻断"]),
    ]


def setup_database() -> None:
    """创建本地 SQLite 示例库。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            DROP TABLE IF EXISTS ads_credit_daily_metrics;
            DROP TABLE IF EXISTS dws_credit_apply_channel_1d;
            DROP TABLE IF EXISTS dwd_credit_apply_detail_di;

            CREATE TABLE ads_credit_daily_metrics (
                biz_date TEXT,
                channel TEXT,
                product_code TEXT,
                apply_cnt INTEGER,
                approved_cnt INTEGER,
                approval_rate REAL,
                loan_amount REAL
            );

            CREATE TABLE dws_credit_apply_channel_1d (
                dt TEXT,
                channel TEXT,
                product_code TEXT,
                risk_grade TEXT,
                apply_cnt INTEGER,
                approved_cnt INTEGER,
                rejected_cnt INTEGER
            );

            CREATE TABLE dwd_credit_apply_detail_di (
                apply_id TEXT,
                customer_id TEXT,
                phone TEXT,
                id_card TEXT,
                apply_time TEXT,
                approve_status TEXT,
                dt TEXT
            );
            """
        )
        conn.executemany(
            "INSERT INTO ads_credit_daily_metrics VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("2026-06-03", "app", "cash_loan", 1200, 780, 0.65, 3450000.0),
                ("2026-06-03", "web", "cash_loan", 800, 480, 0.60, 2100000.0),
                ("2026-06-02", "app", "cash_loan", 1100, 704, 0.64, 3200000.0),
            ],
        )
        conn.executemany(
            "INSERT INTO dws_credit_apply_channel_1d VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("2026-05-28", "app", "cash_loan", "A", 900, 630, 270),
                ("2026-05-29", "app", "cash_loan", "A", 950, 646, 304),
                ("2026-05-30", "web", "cash_loan", "B", 700, 420, 280),
                ("2026-05-31", "app", "cash_loan", "A", 1000, 650, 350),
                ("2026-06-01", "web", "cash_loan", "B", 760, 456, 304),
                ("2026-06-02", "app", "cash_loan", "A", 1100, 704, 396),
                ("2026-06-03", "web", "cash_loan", "B", 800, 480, 320),
            ],
        )
        conn.executemany(
            "INSERT INTO dwd_credit_apply_detail_di VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("A001", "C001", "13800000001", "110101199001010011", "2026-06-03 10:00:00", "APPROVED", "2026-06-03"),
                ("A002", "C002", "13800000002", "110101199001010022", "2026-06-03 10:10:00", "REJECTED", "2026-06-03"),
            ],
        )


def generate_candidate_sql(question: str) -> dict[str, object]:
    """用规则模拟 NL2SQL 生成候选 SQL。"""

    if any(word in question for word in ["删除", "更新", "修改", "drop", "delete", "update"]):
        return {"sql": "DELETE FROM ads_credit_daily_metrics WHERE biz_date = '2026-06-03'", "table": "ads_credit_daily_metrics"}

    if any(word in question for word in ["手机号", "身份证", "导出", "客户"]):
        return {
            "sql": "SELECT phone, id_card FROM dwd_credit_apply_detail_di WHERE dt = '2026-06-03'",
            "table": "dwd_credit_apply_detail_di",
        }

    if "90 天" in question:
        return {
            "sql": (
                "SELECT dt, channel, SUM(approved_cnt) * 1.0 / SUM(apply_cnt) AS approval_rate "
                "FROM dws_credit_apply_channel_1d WHERE dt BETWEEN '2026-03-06' AND '2026-06-03' GROUP BY dt, channel"
            ),
            "table": "dws_credit_apply_channel_1d",
        }

    if "近 7 天" in question and "各渠道" in question:
        return {
            "sql": (
                "SELECT dt, channel, SUM(approved_cnt) * 1.0 / SUM(apply_cnt) AS approval_rate "
                "FROM dws_credit_apply_channel_1d WHERE dt BETWEEN '2026-05-28' AND '2026-06-03' GROUP BY dt, channel"
            ),
            "table": "dws_credit_apply_channel_1d",
        }

    if "昨天" in question and ("申请量" in question or "放款金额" in question):
        return {
            "sql": (
                "SELECT biz_date, SUM(apply_cnt) AS apply_cnt, SUM(loan_amount) AS loan_amount "
                "FROM ads_credit_daily_metrics WHERE biz_date = '2026-06-03' GROUP BY biz_date"
            ),
            "table": "ads_credit_daily_metrics",
        }

    return {
        "sql": "SELECT SUM(approved_cnt) * 1.0 / SUM(apply_cnt) AS approval_rate FROM dws_credit_apply_channel_1d",
        "table": "dws_credit_apply_channel_1d",
    }


def validate_sql(sql: str, table_name: str, policies: dict[str, TablePolicy]) -> dict[str, object]:
    """校验 SQL 是否允许执行。"""

    lowered = sql.lower().strip()
    errors: list[str] = []
    warnings: list[str] = []

    if not lowered.startswith("select"):
        errors.append("非只读 SQL，必须阻断")

    policy = policies.get(table_name)
    if policy is None:
        errors.append("SQL 使用了未登记在 Schema Catalog 的表")
        return {"status": "blocked", "errors": errors, "warnings": warnings, "reason": "；".join(errors)}

    selected_fields = extract_selected_fields(sql)
    sensitive_hits = [field for field in selected_fields if field in policy.sensitive_fields]
    if sensitive_hits:
        errors.append(f"命中敏感字段 {sensitive_hits}，DWD 明细查询必须阻断")

    if policy.layer in {"ODS", "DWD"} and sensitive_hits:
        errors.append("普通离线指标查询不允许访问 DWD/ODS 敏感明细")

    if policy.partition_field not in lowered:
        if "where" not in lowered:
            return {"status": "need_clarification", "errors": ["缺少时间范围和分区条件，需要先澄清"], "warnings": warnings, "reason": "缺少时间范围，需要澄清"}
        errors.append(f"缺少分区字段 {policy.partition_field}")

    scan_days = estimate_scan_days(sql)
    if scan_days > policy.max_scan_days:
        errors.append(f"扫描天数 {scan_days} 超过上限 {policy.max_scan_days}")

    unknown_fields = [field for field in selected_fields if field not in policy.allowed_fields and field not in {"approval_rate"}]
    if unknown_fields:
        warnings.append(f"存在聚合表达式或别名字段 {unknown_fields}，需确认来自允许字段")

    if errors:
        status = "need_clarification" if any("澄清" in error for error in errors) else "blocked"
        return {"status": status, "errors": errors, "warnings": warnings, "reason": "；".join(errors)}

    return {
        "status": "validated",
        "errors": errors,
        "warnings": warnings,
        "reason": f"SQL 只读，使用 {policy.layer} 表，包含 {policy.partition_field} 分区条件，扫描天数 {scan_days}",
    }


def extract_selected_fields(sql: str) -> list[str]:
    """粗略抽取 SELECT 字段，够支撑本地练习的安全校验。"""

    match = re.search(r"select\s+(.*?)\s+from", sql, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    raw_fields = [part.strip() for part in match.group(1).split(",")]
    fields: list[str] = []
    for raw in raw_fields:
        if raw == "*":
            fields.append("*")
            continue
        tokens = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", raw)
        for token in tokens:
            if token.lower() not in {"sum", "as"}:
                fields.append(token)
    return sorted(set(fields))


def estimate_scan_days(sql: str) -> int:
    """从 SQL 里估算扫描天数。"""

    dates = re.findall(r"'(20\d{2}-\d{2}-\d{2})'", sql)
    if len(dates) >= 2:
        from datetime import date

        start = date.fromisoformat(dates[0])
        end = date.fromisoformat(dates[1])
        return (end - start).days + 1
    if len(dates) == 1:
        return 1
    return 9999


def execute_sql(sql: str) -> list[dict[str, object]]:
    """执行已经通过校验的 SQL。"""

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql).fetchall()
        return [dict(row) for row in rows]


def run_case(case: Nl2SqlCase, policies: dict[str, TablePolicy]) -> dict[str, object]:
    """生成、校验并按需执行一条样例。"""

    candidate = generate_candidate_sql(case.question)
    sql = str(candidate["sql"])
    table_name = str(candidate["table"])
    validation = validate_sql(sql, table_name, policies)

    rows: list[dict[str, object]] = []
    actual_status = validation["status"]
    if validation["status"] == "validated":
        rows = execute_sql(sql)
        actual_status = "executed"

    text = json.dumps({"validation": validation, "rows": rows, "sql": sql, "table": table_name}, ensure_ascii=False)
    checks = {
        "status_match": actual_status == case.expected_status,
        "reason_match": all(keyword in text for keyword in case.expected_reason_contains),
    }
    return {
        "case_id": case.case_id,
        "question": case.question,
        "sql": sql,
        "table": table_name,
        "expected_status": case.expected_status,
        "actual_status": actual_status,
        "validation": validation,
        "rows": rows,
        "checks": checks,
        "passed": all(checks.values()),
    }


def write_json(path: Path, data: object) -> None:
    """写入格式化 JSON 文件。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(results: list[dict[str, object]]) -> None:
    """生成 Markdown 评测报告。"""

    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    lines = [
        "# Day 53 离线 NL2SQL + SQL 安全报告",
        "",
        "## 评测结果",
        "",
        f"- 总样例数：{total}",
        f"- 通过样例数：{passed}",
        f"- 通过率：{passed / total:.4f}",
        "",
        "| Case | 问题 | 表 | 状态 | 通过 |",
        "|------|------|----|------|------|",
    ]
    for result in results:
        passed_text = "是" if result["passed"] else "否"
        lines.append(f"| {result['case_id']} | {result['question']} | {result['table']} | {result['actual_status']} | {passed_text} |")

    lines.extend(
        [
            "",
            "## 生产结论",
            "",
            "- 离线 NL2SQL 不能生成后直接执行，必须经过 SQL Validator。",
            "- 优先使用 ADS/DWS，普通指标查询不直接访问 DWD/ODS 敏感明细。",
            "- 分区条件和时间范围是控制扫描成本与结果范围的核心约束。",
            "- 命中手机号、身份证号、客户名单等敏感字段时必须阻断。",
            "- SQL 执行结果要结合指标口径解释，并写审计记录。",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """运行 Day 53 离线 NL2SQL 安全练习。"""

    setup_database()
    policies = build_table_policies()
    cases = build_cases()
    results = [run_case(case, policies) for case in cases]

    write_json(CASES_PATH, [asdict(case) for case in cases])
    write_json(RESULTS_PATH, results)
    write_report(results)

    passed = sum(1 for result in results if result["passed"])
    print("Day 53 离线 NL2SQL + SQL 安全练习完成")
    print(f"cases={len(cases)}")
    print(f"passed={passed}")
    print(f"pass_rate={passed / len(results):.4f}")
    print(f"database={DB_PATH}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
