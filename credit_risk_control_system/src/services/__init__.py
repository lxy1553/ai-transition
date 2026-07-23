"""Services - 对外服务适配层

PRODUCTION: 通过 gRPC/HTTP 调用真实的第三方服务。
  本模块使用内存模拟（标注 ★DEV★），结构完全一致，切换只需替换实现。
"""

from src.services.api_gateway import create_app
from src.services.credit_report_service import CreditReportService
from src.services.device_fingerprint import DeviceFingerprintService
from src.services.multi_head_service import MultiHeadService

__all__ = [
    "create_app",
    "CreditReportService",
    "DeviceFingerprintService",
    "MultiHeadService",
]
