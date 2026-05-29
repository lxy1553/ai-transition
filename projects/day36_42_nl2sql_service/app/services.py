"""NL2SQL 问答服务层。

服务层负责读取 Day 35 的端到端演示结果，并把它包装成 API 能返回的结构。
这里先不重新生成 SQL，而是复用已经通过前几天验证的 JSON 产物；
Day 36-42 的重点是服务化、接口规范、配置、存储和测试。
"""

import json
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from .config import Settings
from .errors import ServiceError
from .storage import AuditStore


class Nl2SqlService:
    """NL2SQL 服务门面。

    API 层只调用这个类，不直接读文件或操作数据库。
    这样后续把演示 JSON 替换成真实 parser/generator/executor 时，接口层不用大改。
    """

    def __init__(self, settings: Settings, audit_store: AuditStore) -> None:
        self.settings = settings
        self.audit_store = audit_store
        self._payload: Optional[dict[str, Any]] = None

    def _load_payload(self) -> dict[str, Any]:
        """懒加载 Day 35 演示结果。

        懒加载能让测试替换路径，也能在服务启动时避免因为产物缺失直接崩溃。
        健康检查会显式报告 demo 是否可用。
        """

        if self._payload is not None:
            return self._payload
        path = Path(self.settings.demo_result_path)
        if not path.exists():
            raise ServiceError(
                code="demo_artifact_missing",
                message=f"演示产物不存在，请先运行 Day 35：{path}",
                status_code=503,
            )
        self._payload = json.loads(path.read_text(encoding="utf-8"))
        return self._payload

    def health(self) -> dict[str, Any]:
        """返回服务健康状态。"""

        demo_ready = Path(self.settings.demo_result_path).exists()
        return {
            "status": "ok" if demo_ready else "degraded",
            "app_name": self.settings.app_name,
            "env": self.settings.app_env,
            "version": self.settings.version,
            "demo_ready": demo_ready,
        }

    def list_questions(self) -> list[str]:
        """列出当前演示包支持的问题。"""

        payload = self._load_payload()
        return [item["question"] for item in payload["cases"]]

    def _find_case(self, question: str) -> Optional[dict[str, Any]]:
        payload = self._load_payload()
        normalized = question.strip()
        for item in payload["cases"]:
            if item["question"] == normalized:
                return item
        for item in payload["cases"]:
            if normalized in item["question"] or item["question"] in normalized:
                return item
        return None

    def ask(self, question: str, user_id: Optional[str], include_trace: bool) -> dict[str, Any]:
        """处理一次 NL2SQL 问答请求。"""

        normalized = " ".join(question.split())
        if len(normalized) > self.settings.max_question_length:
            raise ServiceError(
                code="question_too_long",
                message=f"问题长度不能超过 {self.settings.max_question_length} 个字符。",
                status_code=422,
            )

        case = self._find_case(normalized)
        if not case:
            raise ServiceError(
                code="question_not_in_demo_set",
                message="当前 Week 6 演示版只支持已收录样例问题。",
                status_code=404,
            )

        request_id = str(uuid4())
        self.audit_store.save(request_id, normalized, user_id, case)
        answer = case["answer"]

        return {
            "request_id": request_id,
            "question": case["question"],
            "final_status": case["final_status"],
            "answer": answer["business_answer"],
            "key_findings": answer["key_findings"],
            "risk_notes": answer["risk_notes"],
            "follow_up_questions": answer["follow_up_questions"],
            "pipeline": case["pipeline"] if include_trace else None,
            "sql": case["sql"] if self.settings.expose_sql and include_trace else None,
        }

    def get_trace(self, request_id: str) -> dict[str, Any]:
        """读取一次请求的审计追踪。"""

        trace = self.audit_store.get(request_id)
        if not trace:
            raise ServiceError(
                code="trace_not_found",
                message="没有找到对应 request_id 的审计记录。",
                status_code=404,
            )
        return trace

