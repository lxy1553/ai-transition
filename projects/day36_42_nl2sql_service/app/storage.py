"""SQLite 审计存储。

Day 40 的目标是明确存储方案。这里用 SQLite 存审计记录：
本地轻量、可复现、无需外部服务，适合学习和面试演示。
生产环境可以替换成 Postgres、日志平台或公司内部审计系统。
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class AuditStore:
    """保存和读取 NL2SQL 请求审计记录。"""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        """创建审计表。

        审计表记录最终状态和完整 details，方便后续根据 request_id 回放一次请求。
        """

        with self._connect() as connection:
            connection.execute(
                """
                create table if not exists nl2sql_audit (
                    request_id text primary key,
                    question text not null,
                    user_id text,
                    final_status text not null,
                    created_at text not null,
                    details_json text not null
                )
                """
            )

    def save(self, request_id: str, question: str, user_id: Optional[str], case: dict[str, Any]) -> None:
        """保存一次问答记录。"""

        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                insert into nl2sql_audit (
                    request_id, question, user_id, final_status, created_at, details_json
                )
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    question,
                    user_id,
                    case["final_status"],
                    created_at,
                    json.dumps(case, ensure_ascii=False),
                ),
            )

    def get(self, request_id: str) -> Optional[dict[str, Any]]:
        """按 request_id 读取审计记录。"""

        with self._connect() as connection:
            row = connection.execute(
                """
                select request_id, question, user_id, final_status, created_at, details_json
                from nl2sql_audit
                where request_id = ?
                """,
                (request_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "request_id": row["request_id"],
            "question": row["question"],
            "user_id": row["user_id"],
            "final_status": row["final_status"],
            "created_at": row["created_at"],
            "details": json.loads(row["details_json"]),
        }

