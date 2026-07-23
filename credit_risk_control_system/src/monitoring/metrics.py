"""
Prometheus 监控指标 — 系统 + 业务双维度监控

PRODUCTION: prometheus_client + prometheus-fastapi-instrumentator
  - FastAPI Instrumentator 自动暴露 HTTP 指标
  - 自定义指标通过 prometheus_client 的 Counter/Gauge/Histogram

暴露端点: GET /metrics（由 prometheus-fastapi-instrumentator 自动注册）

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §5.6
"""

from prometheus_client import Counter, Gauge, Histogram, Info


# ═══════════════════════════════════════════════════════════
# 推理服务指标
# ═══════════════════════════════════════════════════════════

# 推理请求总数（按决策结果和模型分）
INFERENCE_REQUESTS = Counter(
    'credit_inference_requests_total',
    'Total inference requests',
    ['decision', 'model_name', 'model_version'],
)

# 推理延迟分布
INFERENCE_LATENCY = Histogram(
    'credit_inference_latency_ms',
    'Inference latency in milliseconds',
    buckets=[10, 25, 50, 100, 150, 200, 300, 500, 1000],
)

# 推理错误计数
INFERENCE_ERRORS = Counter(
    'credit_inference_errors_total',
    'Total inference errors',
    ['error_type'],  # timeout, model_error, feature_missing
)

# ── 特征服务指标 ──

# 特征获取延迟
FEATURE_FETCH_LATENCY = Histogram(
    'credit_feature_fetch_latency_ms',
    'Feature fetch latency in milliseconds',
    buckets=[5, 10, 20, 30, 50, 100, 200],
)

# 特征缺失率（降级率）
FEATURE_MISSING_RATE = Gauge(
    'credit_feature_missing_rate',
    'Rate of features fetched via degradation',
    ['feature_name'],
)

# 特征空值率
FEATURE_NULL_RATE = Gauge(
    'credit_feature_null_rate',
    'Rate of null feature values',
    ['feature_name'],
)

# ── 业务指标 ──

# 实时通过率
APPROVAL_RATE = Gauge(
    'credit_approval_rate',
    'Real-time approval rate (last 5 min)',
)

# 实时逾期率（T+15 早期信号）
EARLY_DELINQUENCY_RATE = Gauge(
    'credit_early_delinquency_rate_t15',
    'Early delinquency rate (T+15)',
)

# 额度使用率
CREDIT_UTILIZATION_RATE = Gauge(
    'credit_utilization_rate',
    'Average credit limit utilization rate',
)

# ── 模型健康指标 ──

# 模型 PSI（每特征）
MODEL_FEATURE_PSI = Gauge(
    'credit_model_feature_psi',
    'Feature PSI value',
    ['feature_name'],
)

# 模型 KS 值
MODEL_KS = Gauge(
    'credit_model_ks',
    'Current model KS value',
    ['model_name', 'model_version'],
)

# 在线模型版本
ACTIVE_MODEL_INFO = Info(
    'credit_active_model',
    'Currently active model information',
)

# ── 熔断器状态 ──

CIRCUIT_BREAKER_STATE = Gauge(
    'credit_circuit_breaker_state',
    'Circuit breaker state: 0=CLOSED, 1=OPEN, 2=HALF_OPEN',
)

# ── 规则引擎指标 ──

RULE_HIT_COUNTER = Counter(
    'credit_rule_hit_total',
    'Rule hit count',
    ['rule_id', 'decision'],
)

RULE_EVAL_LATENCY = Histogram(
    'credit_rule_eval_latency_us',
    'Rule condition evaluation latency in microseconds',
    buckets=[10, 50, 100, 500, 1000, 5000],
)


def record_inference(
    decision: str, model_name: str, model_version: str,
    latency_ms: float, feature_missing_count: int = 0,
) -> None:
    """记录单次推理的监控指标"""
    INFERENCE_REQUESTS.labels(
        decision=decision,
        model_name=model_name,
        model_version=model_version,
    ).inc()
    INFERENCE_LATENCY.observe(latency_ms)

    if feature_missing_count > 0:
        INFERENCE_ERRORS.labels(
            error_type='feature_missing'
        ).inc(feature_missing_count)


def record_rule_hit(rule_id: str, decision: str, eval_time_us: float) -> None:
    """记录规则命中"""
    RULE_HIT_COUNTER.labels(rule_id=rule_id, decision=decision).inc()
    RULE_EVAL_LATENCY.observe(eval_time_us)


def update_approval_rate(rate: float) -> None:
    """更新实时通过率"""
    APPROVAL_RATE.set(rate)


def update_circuit_breaker(state_value: int) -> None:
    """更新熔断器状态"""
    CIRCUIT_BREAKER_STATE.set(state_value)
