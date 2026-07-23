"""
推理流水线 — 风控决策核心编排器

三层决策流程:
  请求进入 → Phase 1: 并行获取特征/数据 (asyncio.gather)
          → Phase 2: 硬规则引擎 (同步, <5ms)
          → Phase 3: A卡模型打分 (XGBoost, ~10ms)
          → Phase 4: 额度策略
          → Phase 5: 异步写决策日志 → 返回响应

PRODUCTION 关键指标:
  P50 延迟: < 100ms
  P99 延迟: < 300ms
  吞吐量:   > 1000 QPS (单实例，取决于特征服务压力)

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §1.2, §2.3, §5.3
"""

import asyncio
import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, Union

import numpy as np

from src.decision_engine.rule_engine import Decision, RuleEngine, RuleResult
from src.decision_engine.ab_router import ABTrafficRouter, BucketConfig
from src.decision_engine.degradation import DegradationPolicy


# ═══════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════

@dataclass
class InferenceRequest:
    """推理请求"""
    user_id: str
    product_type: str          # 产品类型: cash_loan, installment, revolving
    apply_amount: float        # 申请金额（元）
    device_id: str
    trace_id: str = ""         # 全链路追踪ID（若为空则自动生成）

    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = uuid.uuid4().hex[:16]


@dataclass
class FeatureSnapshot:
    """推理时的特征快照（完整记录，可回溯）"""
    user_id: str
    features: dict[str, Any] = field(default_factory=dict)
    feature_version: str = ""
    missing_features: list[str] = field(default_factory=list)
    degraded_features: list[str] = field(default_factory=list)  # 降级获取
    fetch_latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "features": self.features,
            "feature_version": self.feature_version,
            "missing_features": self.missing_features,
            "degraded_features": self.degraded_features,
        }


@dataclass
class DecisionResult:
    """最终决策结果"""
    request_id: str
    user_id: str
    trace_id: str
    decision: str              # APPROVE / REJECT / MANUAL_REVIEW
    score: float               # 信用评分 (300-900)
    default_prob: float        # 违约概率 [0, 1]
    credit_limit: float        # 授信额度（元）
    model_name: str
    model_version: str
    ab_bucket: str             # A/B 分桶名
    reason_codes: list[str]
    shap_contributions: dict[str, float]   # Top-10 特征贡献
    latency_ms: float
    feature_snapshot: FeatureSnapshot

    def to_response_dict(self) -> dict:
        """返回给客户端的精简响应"""
        return {
            "request_id": self.request_id,
            "decision": self.decision,
            "score": round(self.score, 0),
            "credit_limit": self.credit_limit,
            "reason_codes": self.reason_codes,
        }

    def to_log_dict(self) -> dict:
        """返回给 Kafka 决策日志的完整记录"""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "trace_id": self.trace_id,
            "decision": self.decision,
            "score": self.score,
            "default_prob": self.default_prob,
            "credit_limit": self.credit_limit,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "ab_bucket": self.ab_bucket,
            "reason_codes": self.reason_codes,
            "shap_top10": self.shap_contributions,
            "latency_ms": self.latency_ms,
            "feature_snapshot": self.feature_snapshot.to_dict(),
            "timestamp": time.time(),
        }


# ═══════════════════════════════════════════════════════════
# 推理流水线
# ═══════════════════════════════════════════════════════════

class InferencePipeline:
    """
    风控推理流水线 — 编排整个决策流程。

    依赖注入设计:
    - rule_engine: 规则引擎实例
    - model_registry: 模型注册中心（返回可用模型）
    - feature_service: 在线特征服务
    - credit_report_service: 征信报告服务
    - multi_head_service: 多头借贷查询服务
    - device_fp_service: 设备指纹服务
    - ab_router: A/B 测试路由
    - decision_logger: 决策日志写入器（异步→Kafka）

    PRODUCTION 扩展方向:
    1. gRPC 替代 FastAPI REST（更低延迟）
    2. 模型推理使用 C++/ONNX Runtime（GPU 或优化CPU推理）
    3. 增加缓存层（相同用户短期内复用决策）
    """

    def __init__(
        self,
        rule_engine: RuleEngine,
        model_registry,         # ModelRegistry (from src/models)
        feature_service,        # FeatureService (from src/feature_store)
        credit_report_service=None,
        multi_head_service=None,
        device_fp_service=None,
        ab_router: Union[ABTrafficRouter, None] = None,
        decision_logger=None,   # DecisionLogger (async Kafka writer)
    ):
        self.rule_engine = rule_engine
        self.model_registry = model_registry
        self.feature_service = feature_service
        self.credit_report_service = credit_report_service
        self.multi_head_service = multi_head_service
        self.device_fp_service = device_fp_service
        self.ab_router = ab_router or ABTrafficRouter()
        self.decision_logger = decision_logger

    async def execute(self, request: InferenceRequest) -> DecisionResult:
        """
        执行完整的推理决策流水线。

        Args:
            request: 推理请求（用户ID、产品类型、金额、设备ID）

        Returns:
            完整决策结果（决策 + 评分 + 额度 + SHAP + 日志）
        """
        t_start = time.perf_counter()
        request_id = self._gen_request_id(request)

        # ── Phase 1: 并行获取所有特征和数据 ──
        feature_snapshot, external_data = await self._gather_features(request)

        # 构建完整决策上下文
        context = {
            **feature_snapshot.features,
            **external_data,
            "user_id_in_blacklist": self._check_blacklist(request.user_id),
        }

        # ── Phase 2: 规则引擎 ──
        rule_results = self.rule_engine.evaluate(context)
        reject_rules = [r for r in rule_results
                        if r.decision == Decision.REJECT]

        if reject_rules:
            # 硬拒绝：短路返回
            return self._build_result(
                request, request_id, "REJECT", 0, 1.0, 0,
                "rule_engine", "N/A", "hard_reject",
                [r.reason_code for r in reject_rules],
                {}, feature_snapshot, t_start,
            )

        # ── Phase 3: A/B 路由选择模型 ──
        bucket = self.ab_router.route(request.user_id)
        model_wrapper = self.model_registry.get_model(
            bucket.model, bucket.version
        )

        # 构建特征向量（按模型要求的顺序）
        feature_vector = self._build_feature_vector(
            context, model_wrapper.feature_names
        )

        # XGBoost / 评分卡 推理
        default_prob = model_wrapper.predict_proba(feature_vector)

        # SHAP 特征贡献（可解释性）
        shap_contributions = model_wrapper.explain(feature_vector)

        # 评分映射 (300-900)
        score = self._prob_to_score(default_prob)

        # ── Phase 4: 额度策略 ──
        # 规则引擎 Stage 3 的额度规则已在 context 中
        # 这里用评分做基础计算，规则可覆盖
        credit_limit = self._calculate_limit(
            score=score,
            monthly_income=context.get('monthly_income', 0),
            debt_ratio=context.get('debt_to_income_ratio', 0.5),
            apply_amount=request.apply_amount,
            rule_results=rule_results,
        )

        # ── Phase 5: 决策判定 ──
        if score >= 500:
            decision = "APPROVE"
        elif score >= 450:
            decision = "MANUAL_REVIEW"
        else:
            decision = "REJECT"

        # 人工审核规则触发
        manual_review_rules = [
            r for r in rule_results
            if r.decision == Decision.MANUAL_REVIEW
        ]
        if manual_review_rules:
            decision = "MANUAL_REVIEW"

        # ── Phase 6: 组装结果 ──
        result = self._build_result(
            request, request_id, decision,
            score, default_prob, credit_limit,
            model_wrapper.name, model_wrapper.version, bucket.name,
            [r.reason_code for r in rule_results],
            shap_contributions, feature_snapshot, t_start,
        )

        # 异步写入决策日志（不阻塞响应）
        if self.decision_logger:
            asyncio.create_task(self.decision_logger.log(result))

        return result

    # ── 私有方法 ──────────────────────────────────────

    async def _gather_features(
        self, request: InferenceRequest
    ) -> tuple[FeatureSnapshot, dict]:
        """
        并行获取所有数据源。

        每个数据源有独立的超时和降级策略。
        使用 asyncio.gather 实现真正的并发（非串行）。

        PRODUCTION: 各服务调用使用 gRPC 异步客户端
        """
        tasks = []

        # 任务1: 在线特征
        tasks.append(self._fetch_features_with_fallback(request))

        # 任务2-4: 外部数据（如果服务已注入）
        tasks.append(self._fetch_external_with_fallback(
            "credit_report", request.user_id,
            self.credit_report_service, 0.200
        ))
        tasks.append(self._fetch_external_with_fallback(
            "multi_head", request.user_id,
            self.multi_head_service, 0.150
        ))
        tasks.append(self._fetch_external_with_fallback(
            "device_fp", request.device_id,
            self.device_fp_service, 0.030
        ))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 解包结果
        feature_snapshot = (
            results[0] if not isinstance(results[0], Exception)
            else FeatureSnapshot(user_id=request.user_id)
        )

        external_data = {}
        for i, key in enumerate(["credit_report", "multi_head", "device_fp"], 1):
            if not isinstance(results[i], Exception) and results[i]:
                external_data.update(results[i])

        return feature_snapshot, external_data

    async def _fetch_features_with_fallback(
        self, request: InferenceRequest
    ) -> FeatureSnapshot:
        """获取在线特征，50ms 超时降级"""
        t0 = time.perf_counter()
        try:
            snapshot = await asyncio.wait_for(
                self.feature_service.get_online_features(request.user_id),
                timeout=0.050,
            )
        except asyncio.TimeoutError:
            # ★ PRODUCTION: 超时降级——使用缓存或默认值
            snapshot = FeatureSnapshot(user_id=request.user_id)
            cached = self.feature_service.get_cached_features(request.user_id)
            if cached:
                snapshot.features = cached
                snapshot.degraded_features = list(cached.keys())
            else:
                # 最坏情况：全默认值
                snapshot.features = DegradationPolicy.get_all_defaults(
                    self.feature_service.FEATURE_NAMES
                )
                snapshot.degraded_features = list(snapshot.features.keys())

        snapshot.fetch_latency_ms = (time.perf_counter() - t0) * 1000
        return snapshot

    async def _fetch_external_with_fallback(
        self, source: str, key: str,
        service, timeout: float
    ) -> dict:
        """获取外部数据（通用方法，带超时降级）"""
        if service is None:
            return {}
        try:
            return await asyncio.wait_for(
                service.query(key), timeout=timeout
            )
        except (asyncio.TimeoutError, Exception):
            # ★ PRODUCTION: 记录降级事件到监控
            return {}

    def _check_blacklist(self, user_id: str) -> bool:
        """
        检查用户是否在黑名单。

        PRODUCTION: 使用 Bloom Filter + Redis Set 双层检查
        - Bloom Filter: O(1) 空间高效，99% 场景直接返回 False
        - Redis Set: 精确验证，消除 Bloom 误判
        """
        # DEV: 简化实现
        return False

    def _build_feature_vector(
        self, context: dict, feature_names: list[str]
    ) -> np.ndarray:
        """按模型特征顺序构建 numpy 向量（缺失值用降级默认填充）"""
        vec = []
        for name in feature_names:
            val = context.get(name)
            if val is None:
                val = DegradationPolicy.get_default(name)
            vec.append(float(val))
        return np.array(vec, dtype=np.float32)

    def _prob_to_score(self, prob: float) -> float:
        """
        违约概率 → 信用评分映射 (标准评分卡公式)。

        score = base_score + factor * ln(odds)
        其中 odds = (1-p)/p, factor = PDO / ln(2)
        """
        base_score = 600
        pdo = 50
        factor = pdo / np.log(2)
        # 防止 p=0 或 p=1
        prob_clipped = np.clip(prob, 1e-6, 1 - 1e-6)
        odds = (1 - prob_clipped) / prob_clipped
        score = base_score + factor * np.log(odds)
        return float(np.clip(score, 300, 900))

    def _calculate_limit(
        self, score: float, monthly_income: float,
        debt_ratio: float, apply_amount: float,
        rule_results: list[RuleResult],
    ) -> float:
        """计算授信额度"""
        if monthly_income <= 0:
            return 0

        # 基础额度：评分 × 收入倍数
        if score >= 700:
            income_multiplier = 18
        elif score >= 600:
            income_multiplier = 12
        elif score >= 500:
            income_multiplier = 6
        else:
            return 0

        base_limit = monthly_income * income_multiplier

        # 负债率调整
        debt_adjustment = max(0.3, 1.0 - debt_ratio)

        # 规则引擎可能标记 REDUCE_LIMIT
        reduce_factor = 1.0
        for r in rule_results:
            if r.decision == Decision.REDUCE_LIMIT:
                if "50%" in r.reason_desc:
                    reduce_factor = min(reduce_factor, 0.5)
                elif "30%" in r.reason_desc:
                    reduce_factor = min(reduce_factor, 0.7)
                elif "20%" in r.reason_desc:
                    reduce_factor = min(reduce_factor, 0.8)

        final_limit = min(
            base_limit * debt_adjustment * reduce_factor,
            apply_amount,
            200000,  # 绝对上限 20万
        )
        return round(final_limit, 2)

    def _build_result(self, request, request_id, decision,
                      score, default_prob, credit_limit,
                      model_name, model_version, ab_bucket,
                      reason_codes, shap_contributions,
                      feature_snapshot, t_start) -> DecisionResult:
        """组装最终决策结果"""
        latency_ms = (time.perf_counter() - t_start) * 1000
        return DecisionResult(
            request_id=request_id,
            user_id=request.user_id,
            trace_id=request.trace_id,
            decision=decision,
            score=score,
            default_prob=default_prob,
            credit_limit=credit_limit,
            model_name=model_name,
            model_version=model_version,
            ab_bucket=ab_bucket,
            reason_codes=reason_codes,
            shap_contributions=shap_contributions,
            latency_ms=round(latency_ms, 2),
            feature_snapshot=feature_snapshot,
        )

    @staticmethod
    def _gen_request_id(request: InferenceRequest) -> str:
        raw = f"{request.user_id}:{request.trace_id}:{time.time()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
