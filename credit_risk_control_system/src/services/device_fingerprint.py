"""
设备指纹服务 — 评估设备风险等级

PRODUCTION: 对接设备指纹 SDK（如 TrustDecision、同盾）
  - 获取设备硬件信息（IMEI/IDFA/Android ID）
  - 检测设备是否 Root/越狱/模拟器
  - 设备关联多账号分析
  - 设备位置变更频率

★ DEV: 内存模拟
"""

import hashlib
import random


class DeviceFingerprintService:
    """设备指纹风险评估服务"""

    def __init__(self):
        print("[DeviceFingerprintService] DEV模式: 使用模拟数据")

    async def query(self, device_id: str) -> dict:
        """查询设备风险信息"""
        seed = int(hashlib.md5(device_id.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        return {
            "device_risk_score": round(rng.uniform(0.0, 1.0), 4),
            "device_rooted_flag": rng.choice([0, 0, 0, 0, 0, 1]),
            "device_linked_users": rng.randint(0, 5),
            "sim_change_cnt_30d": rng.randint(0, 3),
            "device_age_days": rng.randint(1, 720),
            "is_emulator": rng.choice([0, 0, 0, 0, 0, 0, 1]),
        }
