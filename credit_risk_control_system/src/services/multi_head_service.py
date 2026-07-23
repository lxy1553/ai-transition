"""
多头借贷查询服务 — 第三方多头/共债数据

PRODUCTION: 对接第三方数据商（如同盾、百行、朴道）
  - 查询用户近7/30/90天在多少个平台申请过贷款
  - 返回多头借贷次数、平台类型分布、总负债估计

★ DEV: 内存模拟
"""

import hashlib
import random


class MultiHeadService:
    """多头借贷数据查询服务"""

    def __init__(self):
        print("[MultiHeadService] DEV模式: 使用模拟数据")

    async def query(self, user_id: str) -> dict:
        """查询多头借贷记录"""
        seed = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        mh_7d = rng.randint(0, 8)
        mh_30d = mh_7d + rng.randint(0, 6)

        return {
            "multi_head_cnt_7d": mh_7d,
            "multi_head_cnt_30d": mh_30d,
            "multi_head_cnt_90d": mh_30d + rng.randint(0, 8),
            "multi_head_platform_types": rng.randint(1, 5),
            "total_estimated_debt": round(rng.uniform(0, 100000), 2),
        }
