"""Day 33 - NL2SQL 查询执行与结果格式化。

这个脚本接在 Day 32 SQL 校验器之后，只执行已经通过校验的 SQL。
本地练习使用 SQLite 和一批固定样例数据，模拟生产查询网关的核心职责：
执行安全 SQL、限制返回规模、格式化结果，并记录被跳过或执行失败的样例。
"""

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parents[1]
VALIDATION_RESULT_PATH = (
    ROOT_DIR / "projects/day32_nl2sql_sql_validator/output/sql_validation_results.json"
)
OUTPUT_DIR = PROJECT_DIR / "output"
RESULT_PATH = OUTPUT_DIR / "query_execution_results.json"
REPORT_PATH = OUTPUT_DIR / "query_execution_report.md"
DB_PATH = OUTPUT_DIR / "nl2sql_demo.sqlite"

# 固定运行日期能保证练习结果可复现。
# 生产数据库会用真实 current_date，本地学习阶段更需要稳定的样例输出。
RUN_DATE = date(2026, 5, 24)
MAX_PREVIEW_ROWS = 20


def load_json(path: Path) -> Any:
    """读取上游校验结果，让执行层只依赖明确的 JSON 契约。"""

    return json.loads(path.read_text(encoding="utf-8"))


def week_start(day: date) -> date:
    """按周一作为周起点，模拟常见数仓里的 date_trunc('week') 口径。"""

    return day - timedelta(days=day.weekday())


def month_start(day: date) -> date:
    """计算月初日期，用于替换 SQL 里的 date_trunc('month')。"""

    return day.replace(day=1)


def sql_date(day: date) -> str:
    """生成 SQLite 可识别的日期字面量。"""

    return f"'{day.isoformat()}'"


def adapt_sql_for_sqlite(sql: str) -> str:
    """把 Day 31 生成的演示 SQL 转成 SQLite 能执行的 SQL。

    Day 31 使用了更接近生产数仓的写法，例如 current_date、interval 和 date_trunc。
    SQLite 不支持这些方言，所以这里做一层很薄的本地适配。
    这不是生产 SQL 改写器，只服务于 Day 33 的可运行练习。
    """

    current_week = week_start(RUN_DATE)
    current_month = month_start(RUN_DATE)
    replacements = {
        "date_trunc('week', current_date) - interval '7' day": sql_date(
            current_week - timedelta(days=7)
        ),
        "date_trunc('week', current_date) - interval '1' day": sql_date(
            current_week - timedelta(days=1)
        ),
        "date_trunc('week', current_date)": sql_date(current_week),
        "date_trunc('month', current_date)": sql_date(current_month),
        "current_date - interval '7' day": sql_date(RUN_DATE - timedelta(days=7)),
        "current_date - interval '1' day": sql_date(RUN_DATE - timedelta(days=1)),
        "current_date + interval '1' day": sql_date(RUN_DATE + timedelta(days=1)),
        "current_date": sql_date(RUN_DATE),
    }

    adapted = sql
    for source, target in replacements.items():
        adapted = adapted.replace(source, target)
    # SQLite 对两个整数相除会产生整数结果。生产数仓里的通过率通常是小数，
    # 所以本地执行前把分子转成浮点数，避免 0.65 被截断成 0。
    adapted = adapted.replace(
        "sum(approval_count) / nullif(sum(application_count), 0)",
        "1.0 * sum(approval_count) / nullif(sum(application_count), 0)",
    )
    return adapted.rstrip(";") + ";"


def create_schema(connection: sqlite3.Connection) -> None:
    """创建本地演示表，字段和 Day 29 Schema Catalog 保持一致。

    查询执行层必须和 Schema Catalog 使用同一套字段口径。
    如果本地表结构和 Catalog 不一致，前面生成和校验通过的 SQL 到这里仍然会失败。
    """

    connection.executescript(
        """
        drop table if exists dws_credit_application_daily;
        drop table if exists dws_loan_disbursement_daily;
        drop table if exists dws_repayment_overdue_daily;
        drop table if exists dwd_credit_application_detail;

        create table dws_credit_application_daily (
            dt text,
            product_type text,
            channel text,
            risk_level text,
            application_count integer,
            approval_count integer,
            approval_rate real,
            avg_credit_amount real
        );

        create table dws_loan_disbursement_daily (
            dt text,
            product_type text,
            city text,
            disbursement_amount real,
            loan_count integer
        );

        create table dws_repayment_overdue_daily (
            dt text,
            product_type text,
            overdue_bucket text,
            risk_level text,
            due_amount real,
            repayment_amount real,
            overdue_amount real,
            overdue_rate real
        );

        create table dwd_credit_application_detail (
            application_id text,
            customer_id text,
            application_status text,
            approved_amount real,
            risk_level text,
            apply_time text
        );
        """
    )


def seed_demo_data(connection: sqlite3.Connection) -> None:
    """写入覆盖 Day 31 样例 SQL 的演示数据。

    数据量故意很小，但覆盖了指标查询、分组、趋势、TopN、周对比和明细查询。
    真实生产执行层不会手工造数，而是连接只读副本、查询网关或数仓服务。
    """

    credit_rows = [
        ("2026-05-23", "现金贷", "APP", "A", 180, 126, 0.70, 8200),
        ("2026-05-23", "现金贷", "小程序", "B", 110, 66, 0.60, 7600),
        ("2026-05-23", "分期贷", "线下", "C", 90, 45, 0.50, 6900),
        ("2026-05-11", "现金贷", "APP", "A", 120, 78, 0.65, 8000),
        ("2026-05-12", "现金贷", "APP", "A", 130, 91, 0.70, 8100),
        ("2026-05-13", "分期贷", "小程序", "B", 100, 58, 0.58, 7300),
        ("2026-05-14", "分期贷", "线下", "C", 80, 40, 0.50, 6800),
        ("2026-05-15", "现金贷", "APP", "B", 140, 84, 0.60, 7900),
        ("2026-05-16", "现金贷", "小程序", "A", 150, 102, 0.68, 8300),
        ("2026-05-17", "分期贷", "线下", "B", 90, 54, 0.60, 7000),
    ]
    connection.executemany(
        """
        insert into dws_credit_application_daily values (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        credit_rows,
    )

    loan_rows = [
        ("2026-05-17", "现金贷", "北京", 320000, 38),
        ("2026-05-18", "现金贷", "北京", 360000, 42),
        ("2026-05-19", "现金贷", "北京", 410000, 46),
        ("2026-05-20", "分期贷", "北京", 380000, 44),
        ("2026-05-21", "现金贷", "北京", 450000, 51),
        ("2026-05-22", "分期贷", "北京", 430000, 48),
        ("2026-05-23", "现金贷", "北京", 470000, 55),
        ("2026-05-11", "现金贷", "上海", 520000, 61),
        ("2026-05-12", "现金贷", "深圳", 610000, 70),
        ("2026-05-13", "分期贷", "广州", 480000, 54),
        ("2026-05-14", "现金贷", "杭州", 460000, 50),
        ("2026-05-15", "分期贷", "成都", 390000, 47),
        ("2026-05-16", "现金贷", "南京", 350000, 41),
        ("2026-05-17", "现金贷", "武汉", 330000, 39),
    ]
    connection.executemany(
        "insert into dws_loan_disbursement_daily values (?, ?, ?, ?, ?)",
        loan_rows,
    )

    overdue_rows = [
        ("2026-05-11", "现金贷", "M1", "A", 500000, 470000, 30000, 0.06),
        ("2026-05-12", "现金贷", "M2", "B", 420000, 382000, 38000, 0.09),
        ("2026-05-13", "分期贷", "M1", "A", 390000, 370500, 19500, 0.05),
        ("2026-05-14", "分期贷", "M3+", "C", 280000, 240800, 39200, 0.14),
        ("2026-05-15", "现金贷", "M1", "B", 460000, 432400, 27600, 0.06),
        ("2026-05-16", "分期贷", "M2", "C", 310000, 279000, 31000, 0.10),
        ("2026-05-17", "现金贷", "M3+", "C", 260000, 221000, 39000, 0.15),
        ("2026-05-18", "现金贷", "M1", "A", 530000, 503500, 26500, 0.05),
        ("2026-05-19", "现金贷", "M2", "B", 440000, 404800, 35200, 0.08),
        ("2026-05-20", "分期贷", "M1", "A", 410000, 393600, 16400, 0.04),
        ("2026-05-21", "分期贷", "M3+", "C", 300000, 252000, 48000, 0.16),
        ("2026-05-22", "现金贷", "M1", "B", 480000, 460800, 19200, 0.04),
        ("2026-05-23", "分期贷", "M2", "C", 330000, 300300, 29700, 0.09),
    ]
    connection.executemany(
        "insert into dws_repayment_overdue_daily values (?, ?, ?, ?, ?, ?, ?, ?)",
        overdue_rows,
    )

    detail_rows = [
        ("A123", "C001", "APPROVED", 12000, "A", "2026-05-23 10:30:00"),
        ("A124", "C002", "REJECTED", 0, "C", "2026-05-22 14:10:00"),
    ]
    connection.executemany(
        "insert into dwd_credit_application_detail values (?, ?, ?, ?, ?, ?)",
        detail_rows,
    )
    connection.commit()


def prepare_database() -> sqlite3.Connection:
    """初始化本地数据库，返回只用于本次执行的连接。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    create_schema(connection)
    seed_demo_data(connection)
    return connection


def format_value(value: Any) -> Any:
    """把查询结果转成适合 JSON 和 Markdown 展示的值。"""

    if isinstance(value, float):
        return round(value, 4)
    return value


def infer_response_type(case: dict, columns: list[str], rows: list[dict]) -> str:
    """根据查询类型和结果形态标记返回格式。

    生产接口通常不会只返回裸表格，还会告诉前端这是指标卡、趋势图、TopN 表、
    对比卡片还是明细表，方便页面选择合适的展示组件。
    """

    query_type = case.get("query_type")
    if query_type == "metric" and len(rows) == 1 and len(columns) == 1:
        return "scalar"
    if query_type == "trend":
        return "trend_table"
    if query_type == "comparison":
        return "comparison"
    if query_type == "detail":
        return "detail_table"
    return "table"


def summarize_rows(response_type: str, columns: list[str], rows: list[dict]) -> str:
    """生成简短业务摘要，避免执行层只把数据库原始结果甩给用户。"""

    if not rows:
        return "查询执行成功，但没有返回匹配数据。"
    if response_type == "scalar":
        return f"{columns[0]} = {rows[0][columns[0]]}"
    if response_type == "comparison":
        row = rows[0]
        return (
            f"当前值 {row.get('current_value')}，上期值 {row.get('previous_value')}，"
            f"差值 {row.get('diff_value')}。"
        )
    return f"查询返回 {len(rows)} 行，字段包括：{', '.join(columns)}。"


def execute_case(connection: sqlite3.Connection, case: dict) -> dict:
    """执行单条已放行 SQL，并把结果格式化成稳定结构。"""

    if not case.get("can_execute"):
        return {
            "question": case["question"],
            "query_type": case.get("query_type"),
            "status": "skipped",
            "skip_reason": ", ".join(case.get("issues") or ["not_approved_by_validator"]),
            "source_status": case.get("source_status"),
            "row_count": 0,
            "columns": [],
            "rows": [],
            "summary_text": "SQL 未通过校验或上游已阻断，执行层不会访问数据库。",
        }

    original_sql = case["sql"]
    executable_sql = adapt_sql_for_sqlite(original_sql)
    try:
        cursor = connection.execute(executable_sql)
        fetched_rows = cursor.fetchmany(MAX_PREVIEW_ROWS + 1)
    except sqlite3.Error as exc:
        # 执行失败也要结构化返回，生产里这类信息会进入日志和审计，
        # 但不能把底层数据库错误原样暴露给普通业务用户。
        return {
            "question": case["question"],
            "query_type": case.get("query_type"),
            "status": "execution_error",
            "error": str(exc),
            "source_status": case.get("source_status"),
            "sql": original_sql,
            "executable_sql": executable_sql,
            "row_count": 0,
            "columns": [],
            "rows": [],
            "summary_text": "SQL 已通过校验，但本地执行失败，需要检查方言适配、表结构或样例数据。",
        }

    preview_rows = fetched_rows[:MAX_PREVIEW_ROWS]
    columns = list(preview_rows[0].keys()) if preview_rows else [item[0] for item in cursor.description or []]
    rows = [
        {column: format_value(row[column]) for column in columns}
        for row in preview_rows
    ]
    response_type = infer_response_type(case, columns, rows)

    return {
        "question": case["question"],
        "query_type": case.get("query_type"),
        "status": "executed",
        "source_status": case.get("source_status"),
        "response_type": response_type,
        "row_count": len(rows),
        "truncated": len(fetched_rows) > MAX_PREVIEW_ROWS,
        "columns": columns,
        "rows": rows,
        "summary_text": summarize_rows(response_type, columns, rows),
        "sql": original_sql,
        "executable_sql": executable_sql,
    }


def summarize(results: list[dict]) -> dict:
    """汇总执行结果，帮助判断查询执行链路是否跑通。"""

    return {
        "total": len(results),
        "executed": sum(1 for item in results if item["status"] == "executed"),
        "skipped": sum(1 for item in results if item["status"] == "skipped"),
        "execution_errors": sum(1 for item in results if item["status"] == "execution_error"),
        "run_date": RUN_DATE.isoformat(),
    }


def markdown_table(columns: list[str], rows: list[dict]) -> list[str]:
    """把小结果集转成 Markdown 表，方便直接复盘查询返回值。"""

    if not columns:
        return ["无返回字段。"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return lines


def write_report(payload: dict) -> None:
    """写出执行报告，说明哪些 SQL 被执行、哪些被跳过以及返回了什么。"""

    lines = [
        "# Day 33 - NL2SQL 查询执行报告",
        "",
        "## 总览",
        "",
    ]
    for key, value in payload["summary"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## 执行明细",
            "",
            "| question | status | response_type | row_count | summary |",
            "|----------|--------|---------------|-----------|---------|",
        ]
    )
    for item in payload["results"]:
        lines.append(
            f"| {item['question']} | {item['status']} | {item.get('response_type', '-')} | "
            f"{item['row_count']} | {item['summary_text']} |"
        )

    lines.extend(["", "## 返回结果样例", ""])
    for index, item in enumerate(payload["results"], start=1):
        lines.append(f"### {index}. {item['question']}")
        lines.append("")
        lines.append(f"- 状态：{item['status']}")
        if item["status"] == "skipped":
            lines.append(f"- 跳过原因：{item['skip_reason']}")
            lines.append("")
            continue
        if item["status"] == "execution_error":
            lines.append(f"- 执行错误：{item['error']}")
            lines.append("")
            continue
        lines.append(f"- 摘要：{item['summary_text']}")
        lines.append("")
        lines.extend(markdown_table(item["columns"], item["rows"]))
        lines.append("")

    lines.extend(
        [
            "## 结论",
            "",
            "Day 33 的重点是把 SQL 校验结果接到查询执行层。",
            "执行层只处理校验通过的 SQL，并把结果整理成前端和业务用户能消费的结构。",
            "被拦截的 SQL 不应该再尝试访问数据库，这样才能把安全、权限和成本风险挡在执行层之外。",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """运行 Day 33 查询执行流程。"""

    validation_payload = load_json(VALIDATION_RESULT_PATH)
    connection = prepare_database()
    try:
        results = [execute_case(connection, case) for case in validation_payload["results"]]
    finally:
        connection.close()

    payload = {"summary": summarize(results), "results": results}
    RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(payload)

    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"结果文件: {RESULT_PATH}")
    print(f"报告文件: {REPORT_PATH}")
    print(f"演示数据库: {DB_PATH}")


if __name__ == "__main__":
    main()
