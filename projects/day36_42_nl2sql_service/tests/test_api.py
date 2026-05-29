"""Week 6 NL2SQL API 回归测试。

这些测试覆盖最关键的演示链路：健康检查、成功问答、安全阻断和审计追踪。
Day 41 的目标不是追求测试数量，而是建立每次改动后能快速回归的最小测试集。
本文件使用标准库 unittest，避免本地没有 pytest 时无法执行。
"""

import unittest

from fastapi.testclient import TestClient

from app.main import app


class Nl2SqlApiTest(unittest.TestCase):
    """API 最小回归测试集。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn(payload["status"], {"ok", "degraded"})
        self.assertIn("demo_ready", payload)

    def test_ask_success_case(self) -> None:
        response = self.client.post(
            "/nl2sql/ask",
            json={"question": "本周逾期率比上周变化多少？", "user_id": "demo_user"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["final_status"], "answered")
        self.assertIn("逾期率", payload["answer"])
        self.assertEqual(payload["pipeline"]["sql_validation"], "passed")

    def test_ask_safe_block_case(self) -> None:
        response = self.client.post(
            "/nl2sql/ask",
            json={"question": "导出客户手机号列表", "user_id": "demo_user"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["final_status"], "safely_blocked")
        self.assertEqual(payload["pipeline"]["query_execution"], "skipped")

    def test_trace_after_ask(self) -> None:
        ask_response = self.client.post(
            "/nl2sql/ask",
            json={"question": "昨天授信申请量是多少？", "user_id": "trace_user"},
        )
        request_id = ask_response.json()["request_id"]
        trace_response = self.client.get(f"/nl2sql/trace/{request_id}")
        self.assertEqual(trace_response.status_code, 200)
        payload = trace_response.json()
        self.assertEqual(payload["request_id"], request_id)
        self.assertEqual(payload["user_id"], "trace_user")


if __name__ == "__main__":
    unittest.main()
