"""
征信报告服务 — 对接央行征信/百行征信 API

PRODUCTION: HTTP/gRPC 调用真实征信机构 API
  - 央行征信: 个人信用报告查询
  - 百行征信: 互联网信用分
  - 返回: 信用评分、逾期记录、负债信息、查询记录

★ DEV: 内存模拟，返回合理范围的模拟数据

接口契约（生产与模拟保持一致）:
  query(user_id: str) → dict with keys:
    credit_score_raw, total_monthly_debt, overdue_cnt_hist,
    query_cnt_3m, credit_account_cnt, ...
"""

import hashlib
import random
from typing import Optional


class CreditReportService:
    """
    征信报告查询服务。

    PRODUCTION 注意事项:
    1. 征信查询需要用户授权（电子签章）
    2. 每次查询都会在征信报告留痕（"贷前查询"记录）
    3. 查询次数过多会降低用户信用分
    4. 需要专线/VPN 连接到征信机构
    5. 缓存策略: 同一用户24小时内不重复查询
    """

    def __init__(self, base_url: str = "", api_key: str = ""):
        self.base_url = base_url
        self.api_key = api_key
        self._cache: dict[str, tuple[dict, float]] = {}
        self._cache_ttl = 86400  # 24小时
        print("[CreditReportService] DEV模式: 使用模拟征信数据")

    async def query(self, user_id: str) -> dict:
        """
        查询征信报告。

        PRODUCTION:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/v1/credit/report",
                    json={"user_id": user_id},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=5.0,
                )
                return resp.json()

        Raises:
            TimeoutError: 征信接口超时（200ms后降级）
            ConnectionError: 征信服务不可用
        """
        import time

        # 检查缓存
        if user_id in self._cache:
            data, cached_at = self._cache[user_id]
            if time.time() - cached_at < self._cache_ttl:
                return data

        # ★ DEV: 生成模拟征信数据
        # 用 user_id 的哈希作为随机种子，保证同一用户数据一致
        seed = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        data = {
            "credit_score_raw": rng.randint(350, 850),
            "credit_score_normalized": round(
                (rng.randint(350, 850) - 300) / 600, 4
            ),
            "total_monthly_debt": round(
                rng.uniform(0, 20000), 2
            ),
            "debt_to_income_ratio": round(
                rng.uniform(0.1, 0.9), 4
            ),
            "overdue_cnt_hist": rng.randint(0, 5),
            "query_cnt_3m": rng.randint(0, 10),
            "credit_account_cnt": rng.randint(1, 15),
            "oldest_account_years": round(
                rng.uniform(0.5, 15), 1
            ),
            "recent_overdue_6m": rng.choice([0, 0, 0, 0, 1, 2]),
        }

        # 缓存
        self._cache[user_id] = (data, time.time())

        return data
