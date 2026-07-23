"""
推理 API 网关 — FastAPI 异步推理服务

PRODUCTION: 生产级 API 网关
  - FastAPI + uvicorn (异步高性能)
  - gRPC 用于内部服务间通信（更低延迟）
  - Kong/APISIX 做最外层限流/鉴权/路由

端点:
  POST /api/v1/credit/apply    — 实时信贷审批
  GET  /api/v1/health           — 健康检查
  GET  /metrics                 — Prometheus 指标

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §1.2, §5.3
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.decision_engine.rule_engine import RuleEngine
from src.decision_engine.ab_router import ABTrafficRouter
from src.decision_engine.inference_pipeline import (
    InferencePipeline, InferenceRequest, DecisionResult
)


# ═══════════════════════════════════════════════════════════
# Pydantic 模型 (请求/响应校验)
# ═══════════════════════════════════════════════════════════

class CreditApplyRequest(BaseModel):
    """贷款申请请求"""
    user_id: str = Field(..., description="用户唯一标识")
    product_type: str = Field(
        default="cash_loan",
        description="产品类型: cash_loan, installment, revolving"
    )
    apply_amount: float = Field(
        ..., gt=0, le=500000,
        description="申请金额（元）"
    )
    device_id: str = Field(..., description="设备指纹ID")
    trace_id: Optional[str] = Field(
        default=None,
        description="全链路追踪ID（可选，不传则自动生成）"
    )


class CreditApplyResponse(BaseModel):
    """贷款申请响应"""
    request_id: str
    decision: str          # APPROVE / REJECT / MANUAL_REVIEW
    score: float           # 信用评分 300-900
    credit_limit: float    # 授信额度（元）
    reason_codes: list[str]
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float


# ═══════════════════════════════════════════════════════════
# 应用生命周期
# ═══════════════════════════════════════════════════════════

# 全局变量（应用启动时初始化）
pipeline: Optional[InferencePipeline] = None
_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理"""
    global pipeline, _start_time
    _start_time = time.time()

    # 启动: 初始化推理流水线
    print("[API Gateway] 正在初始化推理服务...")
    rule_engine = RuleEngine("config/rules/credit_policy.yaml")
    # ★ PRODUCTION: 使用真实的 MLflow Model Registry
    from src.models.trainer import LocalModelRegistry
    model_registry = LocalModelRegistry("./data/models")

    # ★ PRODUCTION: 使用真实的 Redis OnlineFeatureStore
    from src.feature_store.online_store import OnlineFeatureStore
    from src.feature_store.registry import FeatureRegistry

    registry = FeatureRegistry("config/features/feature_defs.yaml")
    feature_service = OnlineFeatureStore(
        feature_names=registry.feature_names,
    )

    ab_router = ABTrafficRouter()

    pipeline = InferencePipeline(
        rule_engine=rule_engine,
        model_registry=model_registry,
        feature_service=feature_service,
        ab_router=ab_router,
    )

    print(f"[API Gateway] 推理服务就绪 (features={registry.feature_count}, "
          f"rules={rule_engine.get_statistics()['total_rules']})")

    yield

    # 关闭
    print("[API Gateway] 服务关闭")


# ═══════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════

def create_app() -> FastAPI:
    """创建 FastAPI 应用（供 uvicorn 调用）"""

    app = FastAPI(
        title="信贷风控推理服务",
        description="Credit Risk Control Inference API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS（生产环境需配置具体域名）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 请求日志中间件 ──
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id", uuid.uuid4().hex[:16])
        request.state.trace_id = trace_id
        request.state.start_time = time.time()

        response = await call_next(request)

        latency = (time.time() - request.state.start_time) * 1000
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Latency-Ms"] = f"{latency:.2f}"

        # ★ PRODUCTION: 结构化日志输出到 EFK
        return response

    # ── 端点注册 ──
    @app.get("/api/v1/health", response_model=HealthResponse)
    async def health_check():
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            uptime_seconds=time.time() - _start_time,
        )

    @app.post(
        "/api/v1/credit/apply",
        response_model=CreditApplyResponse,
    )
    async def credit_apply(request: CreditApplyRequest, req: Request):
        """
        信贷审批接口 — 实时授信决策。

        处理流程:
        1. 并行获取特征 + 外部数据
        2. 规则引擎硬拒绝检查
        3. A卡模型打分 + SHAP 解释
        4. 额度策略计算
        5. 异步写决策日志 → 返回响应

        超时: P99 < 300ms
        """
        if pipeline is None:
            raise HTTPException(status_code=503, detail="服务未就绪")

        try:
            inference_request = InferenceRequest(
                user_id=request.user_id,
                product_type=request.product_type,
                apply_amount=request.apply_amount,
                device_id=request.device_id,
                trace_id=request.trace_id or getattr(
                    req.state, 'trace_id', ''
                ),
            )

            result = await pipeline.execute(inference_request)

            # ★ PRODUCTION: 记录 Prometheus 指标
            # APPROVE_COUNTER.labels(model=result.model_name).inc()
            # LATENCY_HISTOGRAM.observe(result.latency_ms)

            return CreditApplyResponse(
                request_id=result.request_id,
                decision=result.decision,
                score=result.score,
                credit_limit=result.credit_limit,
                reason_codes=result.reason_codes,
                latency_ms=result.latency_ms,
            )

        except Exception as e:
            # ★ PRODUCTION: 记录错误到 Sentry + Prometheus
            raise HTTPException(
                status_code=500,
                detail=f"推理服务异常: {str(e)}"
            )

    @app.post("/api/v1/credit/apply/detailed")
    async def credit_apply_detailed(
        request: CreditApplyRequest, req: Request
    ):
        """
        详细决策接口 — 返回完整信息（含 SHAP 值、特征快照）。
        供审批后台和调试使用。
        """
        if pipeline is None:
            raise HTTPException(status_code=503, detail="服务未就绪")

        inference_request = InferenceRequest(
            user_id=request.user_id,
            product_type=request.product_type,
            apply_amount=request.apply_amount,
            device_id=request.device_id,
            trace_id=request.trace_id or getattr(req.state, 'trace_id', ''),
        )

        result = await pipeline.execute(inference_request)
        return JSONResponse(content=result.to_log_dict())

    return app


# ═══════════════════════════════════════════════════════════
# 直接运行
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    import uvicorn
    app = create_app()
    uvicorn.run(
        app, host="0.0.0.0", port=8000,
        log_level="info",
    )
