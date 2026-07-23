---
id: L013
source: learning
category: AI应用开发
title: 请举例说明核心代码：`inference_pipeline.py` 的 execute()（1h）如何实现？
generated: 2026-07-23T15:41:19.859626
---

# 请举例说明核心代码：`inference_pipeline.py` 的 execute()（1h）如何实现？

> 来源: 学习复习计划 | 分类: AI应用开发

打开 `src/decision_engine/inference_pipeline.py` 第 164-260 行：


```python
async def execute(self, request: InferenceRequest) -> DecisionResult:

    # Phase 1: 获取特征（asyncio.gather 并行）
    feature_snapshot, external_data = await self._gather_features(request)
    context = {**feature_snapshot.features, **external_data}

    # ═══════════════════════════════════
    # Phase 2: Layer 1 — 硬规则引擎
    # ★ 命中了 → 直接 return，后面不跑
    # 为什么？安全 > 性能 > 模型
    # ═══════════════════════════════════
    rule_results = self.rule_engine.evaluate(context)
    reject_rules = [r for r in rule_results
                    if r.decision == Decision.REJECT]

    if reject_rules:
        return DecisionResult(
            decision="REJECT", score=0,
            reason_codes=[r.reason_code for r in reject_rules],
            model_name="rule_engine",  # ← 标注：这次决策没跑模型
        )

    # Phase 3: Layer 2 — 模型推理
    model_wrapper = self.model_registry.get_model("credit_a_card_xgb")
    default_prob = model_wrapper.predict_proba(feature_vector)
    score = self._prob_to_score(default_prob)   # [300, 900]
    shap_vals = model_wrapper.explain(feature_vector)

    # Phase 4: Layer 3 — 额度计算
    credit_limit = self._calculate_limit(
        score, monthly_income, debt_ratio,
        rule_results  # ← 规则可以覆盖额度
    )

    # ═══════════════════════════════════
    # Phase 5: Layer 4 — 融合判定
    # 规则优先 > 模型
    # ═══════════════════════════════════
    manual_review_rules = [
        r for r in rule_results
        if r.decision == Decision.MANUAL_REVIEW
    ]

    if manual_review_rules:
        decision = "MANUAL_REVIEW"      # 规则强制 Review
    elif score >= 600:                   # 高分
        decision = "APPROVE"
    elif score >= 500:                   # 边界
        decision = "MANUAL_REVIEW"
    else:                                # 低分
        decision = "REJECT"

    return DecisionResult(decision=decision, score=score, ...)

```

**四个关键的"为什么"**：


```python
# Q1: 为什么硬拒绝要短路，不跑模型？
# A: 两个原因——
#   1. 安全: 模型可能给黑名单用户打高分（训练集中黑样本少）
#   2. 性能: 省一次 XGBoost 推理(~10ms)，高 QPS 下加起来可观

# Q2: 为什么规则可以覆盖模型，模型不能覆盖规则？
# A: 规则 = MIN(安全性)，模型 = MAX(效率)
#   安全底线不可被概率突破 → 规则优先级更高

# Q3: 阈值为什么是 500/600？
# A: 需要分析评分分布 vs 坏账率的关系
#   600+ 通过: 坏账率 ~3%
#   500-600 人工: 坏账率 ~8%，需要审核员判断
#   500- 拒绝: 坏账率 >15%，不值得放

# Q4: 为什么 reason_codes 给规则结果而非 SHAP？
# A: 规则结果是确定性的"为什么"，SHAP 是概率性的"多少贡献"
#   给用户看"年龄不在范围"比"特征X贡献了0.08"清晰 100 倍

```

---