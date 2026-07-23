# Day 03：规则 + 模型融合 — 四层决策架构

> 目标：掌握四层决策架构的设计原理，能手写融合逻辑，能说清"每一层为什么这么排"。

---

## 一、为什么不能只用模型？（20min）

### 1.1 模型的三个盲区

```
盲区 1: "绝对禁止"无法用概率表达
  "黑名单用户绝对不允许放款"
  → 模型输出: "违约概率 0.15" ← 15% 概率会违约 ≠ 绝对禁止
  → 需要规则: "IF 黑名单 THEN REJECT"（概率 = 100%）

盲区 2: 模型没见过的情况不可信
  新出现的欺诈手段 → 训练集里没有 → 模型会给低风险评分
  → 需要规则: "IF 设备是全新的 AND 深夜操作占比 > 80% THEN REVIEW"

盲区 3: 违反法规的决策不能发生
  "不能因为性别/种族拒绝贷款"
  → 模型可能从数据中学到这类偏见
  → 需要规则: 显式禁止这些特征进入模型，或加入公平性校验
```

### 1.2 融合方案：规则做安全底线，模型做效率工具

```
Layer 1: 硬规则 (Hard Reject) — 安全底线
  → 命中即短路，不跑模型
  → 例: 黑名单、欺诈高分、年龄不合法

Layer 2: 模型评分 (ML Score) — 效率工具
  → 量化风险，在规则空白处做主决策
  → 例: XGBoost 输出违约概率 → 评分卡映射 → 300-900 分

Layer 3: 融合判定 (Fusion) — 最终的决策者
  → 规则优先级 > 模型优先级
  → 规则说 REVIEW → 不管模型打多少分，都是 REVIEW

Layer 4: 策略执行 (Action) — 实施决定
  → APPROVE → 计算额度 → 放款
  → REJECT → 记录 reason_code → 生成拒绝函
  → MANUAL_REVIEW → 分配审核员
```

---

## 二、核心代码：`inference_pipeline.py` 的 execute()（1h）

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

## 三、动手练习（1.5h）

### 练习 1：手写四个版本的决策融合并对比（1h）

```python
# 场景: 用户 u1，模型评分 620(APPROVE)，但规则触发了"多头借贷预警(MANUAL_REVIEW)"

# 版本 A: 纯模型
def decision_v1(score, rules):
    if score >= 600: return "APPROVE"
    elif score >= 500: return "MANUAL_REVIEW"
    else: return "REJECT"
# → u1 结果是 APPROVE（忽略了"多头借贷"警告）

# 版本 B: 纯规则
def decision_v2(score, rules):
    if any(r.decision == 'REJECT' for r in rules): return "REJECT"
    if any(r.decision == 'MANUAL_REVIEW' for r in rules): return "MANUAL_REVIEW"
    return "APPROVE"
# → u1 结果是 MANUAL_REVIEW（浪费了 620 分这个"安全"信号）

# 版本 C: 规则优先 + 模型兜底（项目的方案）
def decision_v3(score, rules):
    if any(r.decision == 'REJECT' for r in rules):
        return "REJECT"                       # 硬规则直接拒绝
    if any(r.decision == 'MANUAL_REVIEW' for r in rules):
        return "MANUAL_REVIEW"                # 规则可以转人工
    if score >= 600: return "APPROVE"         # 规则通过 → 模型做主
    elif score >= 500: return "MANUAL_REVIEW"
    else: return "REJECT"
# → u1 结果是 MANUAL_REVIEW（规则有最终决定权）

# 版本 D: 加权融合
def decision_v4(score, rules):
    rule_penalty = 0
    for r in rules:
        if r.decision == 'MANUAL_REVIEW': rule_penalty -= 100
    adjusted_score = score + rule_penalty
    # 620 - 100 = 520 → 变成了 MANUAL_REVIEW
    ...
# → u1 结果是 MANUAL_REVIEW（和版本C一致），但规则多时可能不一致

# ★ 参考答案:
# | 版本 | 安全性 | 效率 | 可解释性 | 适用场景 |
# | A    | 低 (忽略规则) | 高 (只跑模型) | 高 (只看评分) | 无安全红线、纯评分场景 |
# | B    | 极高 (规则卡死) | 中 (规则优先) | 高 (规则明确) | 监管严格、安全第一 |
# | C    | 高 (规则覆盖模型) | 高 (短路节省算力) | 极高 (规则+模型互不干扰) | ★ 信贷、审核等需要安全和效率平衡 |
# | D    | 中 (权重可能不合适) | 中 (多步计算) | 低 (分数调整不透明) | 规则冲突多、需要精细调优 |
#
# 项目选择版本 C 的原因:
# 1. 安全性: 硬规则短路 + 规则可覆盖模型（REVIEW > APPROVE）
# 2. 效率: 硬拒绝直接返回，不跑模型
# 3. 可解释性: 规则结果(reason_code)和模型结果(SHAP)分开给
```

### 练习 2：为内容审核设计分层决策（30min）

```python
# ★ 参考答案
SENSITIVE_KEYWORDS = ['诈骗', '赌博', '色情', '毒品', '枪支']

def moderate_content(text: str, user: dict, model_prob: float) -> dict:
    """
    四层审核架构 — 与信贷风控的四层完全对应
    """

    # ★ Layer 1: 硬规则 — 敏感词拦截（短路）
    for kw in SENSITIVE_KEYWORDS:
        if kw in text:
            return {
                "action": "BLOCK",
                "reason": f"命中敏感词: {kw}",
                "model_prob": model_prob,
                "layer": 1,
            }

    # Layer 2: 模型输出
    if model_prob > 0.8:
        level = "high"
    elif model_prob > 0.5:
        level = "medium"
    else:
        level = "low"

    # ★ Layer 3: 融合判定 — 规则覆盖 + 用户历史 + 模型
    if level == "high":
        if user.get("violation_count", 0) >= 3:
            return {"action": "BLOCK", "reason": "高危+惯犯", "layer": 3}
        return {"action": "MANUAL_REVIEW", "reason": "高风险", "layer": 3}

    elif level == "medium":
        if user.get("violation_count", 0) >= 3:
            return {"action": "BLOCK", "reason": "中危+惯犯", "layer": 3}
        if user.get("is_new", True):
            return {"action": "MANUAL_REVIEW", "reason": "新人+中危", "layer": 3}
        return {"action": "FLAG", "reason": "中危老人,标记观察", "layer": 3}

    else:
        # ★ Layer 4: 低危 — 放行（但记录日志）
        return {"action": "PASS", "reason": "安全", "layer": 4}

# 测试用例
users = [
    {"violation_count": 0, "is_new": True},
    {"violation_count": 5, "is_new": False},
]
texts = ["你好吗", "诈骗电话", "这个商品不错", "这是一个测试"]

for u in users:
    for t in texts:
        result = moderate_content(t, u, 0.6)
        print(f"user={u['violation_count']}次违规 | {t[:15]:15s} → {result['action']}")
```

---

## 四、跨业务思考（30min）

### 医疗分诊的融合架构

```
Layer 1 硬规则:
  - 心率=0 → 立即抢救（不用跑模型）
  - 已知过敏药物 → 禁止使用

Layer 2 模型:
  - 疾病风险评分

Layer 3 融合:
  - 模型说低风险 BUT 硬规则说"体温 41°C" → 无视模型，送急诊
  - 模型说高风险 BUT 无硬规则触发 → 送 ICU

Layer 4 策略:
  - ICU / 急诊 / 门诊 / 观察
```

---

## 五、今日要点

```
融合决策的三个铁律:
  1. 规则 > 模型: 安全底线不可被概率突破
  2. 短路: 硬拒绝后不跑模型，省算力 + 更安全
  3. reason_code: 每次决策都要能追溯"为什么"
```

---

## 六、检查清单

- [ ] 能画出四层决策架构图，标注每层的职责
- [ ] 完成了四个版本的决策融合代码 + 对比分析表
- [ ] 完成了内容审核分层决策的代码
- [ ] 能解释为什么"硬拒绝短路"既安全又高效
