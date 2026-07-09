# 跨业务通用的 AI 应用开发能力（附代码详解）

> 从信贷风控项目中提炼可迁移到电商、医疗、物流等任何业务的底层 AI 应用开发能力。每个能力附带真实代码块 + "为什么这么写"的分析。

---

## 能力全景图

```
                     ┌──────────────────────────────────────┐
                     │      AI 应用开发工程师的核心能力        │
                     └──────────────────────────────────────┘
                                        │
        ┌───────────┬───────────┬───────┼───────┬───────────┬───────────┐
        ▼           ▼           ▼       ▼       ▼           ▼           ▼
    ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────┐
    │能力1 │  │能力2 │  │能力3 │  │能力4 │  │能力5 │  │能力6 │  │能力7      │
    │PIT   │  │特征  │  │规则+ │  │评估  │  │降级  │  │LLM   │  │可解释性   │
    │样本  │  │工程  │  │模型  │  │监控  │  │容错  │  │应用  │  │+合规      │
    └──────┘  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘  └──────────┘
```

---

## 能力 1：数据到训练样本的转化 — PIT + 标签工程

### 核心代码：PIT 正确的训练样本构建

```python
# src/data/warehouse/ads_layer.py 第41-81行

def build_training_samples(
    self,
    dws_wide_table: pd.DataFrame,   # 用户在 T 时刻的特征快照
    label_df: pd.DataFrame,          # 用户在 T+30 天的逾期标签
    performance_window_days: int = 30,
) -> pd.DataFrame:
    """
    构建不包含时间泄漏的训练样本。

    关键约束:
    - 特征快照时间:  dt (2026-07-01)
    - 标签观察时间:  dt + 30天 (2026-08-01)
    - 拼接条件:      dt_特征 < dt_标签  ← 严格不等式

    为什么这样写？
    1. inner join 而非 left join — 两个时间点都必须有数据，缺一个说明数据质量问题
    2. on='user_id' 关联 — 同一个用户在不同时间点的特征和标签各自独立
    3. merge 而非 concat — concat 只按行号对齐，可能把 T+30 的标签拼到 T 的特征
       → 严重时间泄漏 → 离线 AUC 虚高 → 上线后完全失效
    """
    samples = dws_wide_table.merge(
        label_df,
        on='user_id',        # 同一个用户
        how='inner',         # 两个时间点都必须有数据
    )

    # 清理 merge 产生的重名列（df.merge 会给同名列加 _x/_y 后缀）
    drop_cols = [
        c for c in ['dt_y', 'performance_date']
        if c in samples.columns
    ]
    samples = samples.drop(columns=drop_cols)
    return samples
```

**三种拼接方式的对比 —— 为什么选 merge 不选 concat**：

| 写法 | 后果 | 说明 |
|------|------|------|
| `pd.concat([features, labels], axis=1)` | **严重时间泄漏！** | concat 不关心时间，只按行索引对齐。可能把 T+30 标签拼到 T 特征 |
| `merge(on='user_id', how='inner')` | ✅ **正确** | 同一用户在不同时间的记录各自独立，上游保证时间顺序 |
| `merge(on='user_id', how='left')` | 可能引入无标签样本 | 保留只有特征没有标签的用户 → 无法用于训练 |

**实际上 PIT 正确性由两层共同保证**：

```python
# 第一层：标签生成时，label_date 必须 = dt + 30（上游保证）
# scripts/generate_data_pipeline.py 第122-128行
label_df = pd.DataFrame({
    'user_id': users,
    'label': np.random.choice([0, 1], len(users), p=[0.87, 0.13]),
    'label_date': dt,  # ← 生产中这是 "dt + 30天后的逾期观察结果"
})

# 第二层：拼接时 merge 只负责按 user_id 关联（本层保证）
# 生产 SQL 版（更安全，时间约束直接写进 SQL）:
# SELECT w.*, l.label
# FROM dws.user_risk_feature_wide w
# LEFT JOIN labels l
#   ON w.user_id = l.user_id
#   AND w.dt = DATE_SUB(l.label_date, 30)  ← 严格时间约束
```

### 换个业务：电商推荐 PIT 样本

```python
# 电商推荐 — 完全相同的模式，只是 T+N 换成了 T+7

def build_recommendation_samples(
    user_features: pd.DataFrame,     # 曝光时刻 T 的特征
    click_labels: pd.DataFrame,      # T+7 天内是否点击
) -> pd.DataFrame:
    """
    与信贷完全相同的 PIT 模式:
    - dt_特征 = 商品曝光时刻
    - dt_标签 = 曝光后 7 天
    - 严禁: 用点击后的浏览行为去预测是否会点击
    """
    samples = user_features.merge(
        click_labels,
        on=['user_id', 'item_id'],   # 比信贷多一个 item_id 维度
        how='inner',
    )
    # 双重保险：显式过滤时间泄漏
    samples = samples[samples['feature_time'] < samples['click_time']]
    return samples
```

| 业务 | 预测目标 | 特征时间 T | 标签时间 T+N | 典型泄漏错误 |
|------|---------|-----------|-------------|------------|
| 信贷 | 是否逾期 | 申请日 | T+30 | 用还款记录预测逾期 |
| 电商 | 是否购买 | 曝光日 | T+7 | 用购买后浏览预测购买 |
| 流失 | 是否流失 | 今天 | T+30 | 用卸载后行为预测流失 |
| 医疗 | 并发症 | 入院时 | T+72h | 用出院诊断预测入院诊断 |
| 物流 | 是否延误 | 发货时 | T+N | 用到货时间预测延误 |

---

## 能力 2：从原始事件到特征向量的转化 — 特征工程

### 核心代码：时间窗口 + 比率衍生

```python
# src/data/warehouse/dws_layer.py 第135-199行

def _build_behavior_features(
    self, behavior_df: pd.DataFrame, dt: str
) -> pd.DataFrame:
    """
    从用户行为埋点日志 → 6维行为特征向量。

    输入: 明细级行为日志 (一行 = 一个事件的原始 SDK 上报)
      user_000042 | page_view | /mine  | 2026-07-01 23:45
      user_000042 | submit    | /apply | 2026-07-01 02:30
      ...

    输出: 用户级特征 (一行 = 一个用户的聚合向量)
      user_000042 | apply_cnt_7d=1 | night_ops_ratio=0.27 | ...
    """
    ref_date = datetime.strptime(dt, '%Y-%m-%d')
    behavior_df['event_time'] = pd.to_datetime(behavior_df['event_time'])

    result_rows = []
    for user_id, group in behavior_df.groupby('user_id'):

        # ═══ 技巧1: 用 event_time 而非 dt 分区键做窗口过滤 ═══
        # dt 是"数据写入仓库的日期"，event_time 是"事件实际发生时间"。
        # 凌晨 01:30 的事件可能 dt=T 也可能 dt=T+1（取决于 ETL 时间）。
        # 用 dt 做窗口 → 时间边界不精确 → 特征值不稳定。
        # 用 event_time → 真正的时序语义 → 任何时间窗口都精确。
        in_7d = group['event_time'] >= ref_date - timedelta(days=7)
        in_30d = group['event_time'] >= ref_date - timedelta(days=30)
        group_7d = group[in_7d]
        group_30d = group[in_30d]

        # ═══ 技巧2: 事件类型 → COUNT WHERE 模式 ═══
        # 不是 count(*) 全部事件，而是按 event_type 分类计数
        apply_cnt_7d = (group_7d['event_type'] == 'submit').sum()
        apply_cnt_30d = (group_30d['event_type'] == 'submit').sum()
        page_view_7d = (group_7d['event_type'] == 'page_view').sum()
        input_7d = (group_7d['event_type'] == 'input').sum()
        error_7d = (group_7d['event_type'] == 'error').sum()

        # ═══ 技巧3: 比率衍生 — 用占比而非绝对值 ═══
        # 为什么用 mean()（占比）而不是 sum()（次数）？
        # 高频用户行为总次数多 → sum 会将"高活跃"误判为"高风险"
        # 占比消除了活跃度偏差 → 只反映行为模式
        #   行为 100 次其中 27 次深夜 → 0.27（可疑）
        #   行为 10 次其中 2 次深夜 → 0.20（正常）
        #   如果用 sum：100 vs 2 → 高频用户被严重误判
        night_hours = group_30d['event_time'].dt.hour.isin(
            [22, 23, 0, 1, 2, 3, 4, 5]  # 为什么 22-05 而非 00-06？
        )                                 # 22-05 覆盖深夜+凌晨，00-06 会漏掉 22-24
        night_ops_ratio = (               # 20-06 太宽，包含正常晚间上网
            night_hours.mean()
            if len(group_30d) > 0 else 0
        )

        result_rows.append({
            'user_id': user_id,
            'apply_cnt_7d': apply_cnt_7d,
            'apply_cnt_30d': apply_cnt_30d,
            'night_ops_ratio_30d': round(night_ops_ratio, 4),
            'page_view_cnt_7d': page_view_7d,
            'input_cnt_7d': input_7d,
            'error_event_cnt_7d': error_7d,
        })

    return pd.DataFrame(result_rows)
```

**三行关键代码的深度解读**：

```python
# ① in_7d = group['event_time'] >= ref_date - timedelta(days=7)
#   为什么 event_time 而不是 dt？
#   dt 是分区键（数据写入日期），event_time 是事件时间。
#   凌晨事件可能跨天入库。用 dt 做窗口 → 时间边界漂移 → 特征不稳定。

# ② night_hours.isin([22,23,0,1,2,3,4,5])
#   为什么 22-05？
#   22:00-05:00 → 覆盖深夜 + 凌晨，欺诈团伙活跃时段
#   00:00-06:00 → 太窄，漏掉 22-24 晚间异常
#   20:00-06:00 → 太宽，包含正常晚间上网

# ③ night_ops_ratio = night_hours.mean()
#   为什么 mean()（占比）而不是 sum()（次数）？
#   高频用户一切行为都多 → sum 将"活跃 = 风险"误判
#   占比消除活跃度偏差 → 只反映行为模式本身
```

### 换个业务：电商用户特征

```python
# 电商 — 完全相同的三种模式，只换事件枚举值

def build_ecommerce_features(user_events: pd.DataFrame, ref_date: str):
    """与信贷特征工程完全相同的三种模式"""
    ref = datetime.strptime(ref_date, '%Y-%m-%d')
    user_events['event_time'] = pd.to_datetime(user_events['event_time'])

    result = []
    for uid, g in user_events.groupby('user_id'):
        in_7d = g['event_time'] >= ref - timedelta(days=7)
        g7 = g[in_7d]

        # 模式1: 事件类型 → COUNT WHERE（与 apply_cnt_7d 相同）
        view_cnt_7d = (g7['event_type'] == 'view_item').sum()
        cart_cnt_7d = (g7['event_type'] == 'add_cart').sum()
        buy_cnt_7d = (g7['event_type'] == 'purchase').sum()

        # 模式2: 比率衍生（与 night_ops_ratio 相同模式）
        cart_rate = cart_cnt_7d / max(view_cnt_7d, 1)   # 加购转化率
        buy_rate = buy_cnt_7d / max(cart_cnt_7d, 1)     # 购买转化率

        # 模式3: 多样性特征（distinct 聚合）
        category_diversity = g7['category'].nunique()

        result.append({
            'user_id': uid,
            'view_cnt_7d': view_cnt_7d,
            'cart_conversion_7d': round(cart_rate, 4),
            'purchase_conversion_7d': round(buy_rate, 4),
            'category_diversity_7d': category_diversity,
        })
    return pd.DataFrame(result)
```

| 业务 | 原始事件 | 时间窗口特征(模式1) | 比率衍生(模式2) |
|------|---------|-------------------|----------------|
| 信贷 | 申请/浏览/还款 | apply_cnt_7d | night_ops_ratio |
| 电商 | 浏览/加购/下单 | view_cnt_7d | 加购转化率 = 加购/浏览 |
| 客服 | 消息/转接/挂断 | transfer_cnt_7d | 转接率 = 转接/总会话 |
| 游戏 | 登录/充值/副本 | login_days_7d | 付费率 = 付费/活跃 |

---

## 能力 3：规则 + 模型融合决策架构

### 核心代码：四层融合推理流水线

```python
# src/decision_engine/inference_pipeline.py 第164-260行

async def execute(self, request: InferenceRequest) -> DecisionResult:
    t_start = time.perf_counter()

    # Phase 1: 并行获取特征（asyncio.gather, 50ms 超时）
    feature_snapshot, external_data = await self._gather_features(request)
    context = {**feature_snapshot.features, **external_data}

    # ═══════════════════════════════════════════════════
    # Phase 2: 硬规则引擎 — Layer 1
    # ★ 核心设计: 命中硬拒绝 → 短路返回，不跑模型
    # 为什么？两个原因:
    #   1. 安全: 黑名单/欺诈规则是"绝对"的，不能被模型概率覆盖
    #      （模型可能给黑名单用户打高分，因为训练集里没有黑样本）
    #   2. 性能: 省一次 XGBoost 推理(~10ms)，高 QPS 下积累可观
    # ═══════════════════════════════════════════════════
    rule_results = self.rule_engine.evaluate(context)
    reject_rules = [r for r in rule_results
                    if r.decision == Decision.REJECT]

    if reject_rules:
        return DecisionResult(
            decision="REJECT",
            score=0,
            reason_codes=[r.reason_code for r in reject_rules],
            model_name="rule_engine",  # ← 标注决策来源，用于后续分析
            latency_ms=(time.perf_counter() - t_start) * 1000,
        )

    # Phase 3: 模型推理 — Layer 2
    model_wrapper = self.model_registry.get_model("credit_a_card_xgb")
    feature_vector = self._build_feature_vector(
        context, model_wrapper.feature_names
    )
    default_prob = model_wrapper.predict_proba(feature_vector)
    score = self._prob_to_score(default_prob)           # [300, 900]
    shap_vals = model_wrapper.explain(feature_vector)    # SHAP 贡献

    # Phase 4: 额度策略 — Layer 3
    # 规则引擎中的 REDUCE_LIMIT 可以覆盖模型计算的额度
    credit_limit = self._calculate_limit(
        score, context.get('monthly_income', 0),
        context.get('debt_to_income_ratio', 0.5),
        rule_results  # ← 传入规则结果，允许覆盖
    )

    # ═══════════════════════════════════════════════════
    # Phase 5: 融合判定 — Layer 4
    # ★ 核心逻辑: 规则优先级 > 模型优先级
    #   规则说 REVIEW → 不管模型打多少分，都是 REVIEW
    #   规则没触发 → 模型做主决策
    # ═══════════════════════════════════════════════════
    manual_review_rules = [
        r for r in rule_results
        if r.decision == Decision.MANUAL_REVIEW
    ]

    if manual_review_rules:
        decision = "MANUAL_REVIEW"       # 规则可强制转人工
    elif score >= 600:
        decision = "APPROVE"             # 高分直接通过
    elif score >= 500:
        decision = "MANUAL_REVIEW"       # 边界转人工
    else:
        decision = "REJECT"              # 低分拒绝

    return DecisionResult(
        decision=decision, score=score,
        credit_limit=credit_limit,
        reason_codes=[r.reason_code for r in rule_results],
        shap_contributions=shap_vals,
        latency_ms=(time.perf_counter() - t_start) * 1000,
    )
```

**四个关键的"为什么"**：

```python
# 决策1: 为什么硬拒绝要短路，不等模型结果？
#   → 安全: 模型可能误判黑名单用户（训练集没见过黑样本）
#   → 性能: 省 10ms 推理时间，1000 QPS 就是 10s CPU 时间
#   → 可解释: "命中黑名单"比"模型评分低"更容易被监管接受

# 决策2: 为什么规则可以覆盖模型，但模型不能覆盖规则？
#   → 规则 = MIN(安全性) → 安全底线不可被概率突破
#   → 模型 = MAX(效率)   → 在安全边界内做最优决策

# 决策3: 评分阈值为什么是 500/600？
#   → 600+ 通过: 坏账率约 3%，可接受
#   → 500-600 人工: 坏账率约 8%，需人工判断
#   → 500- 拒绝: 坏账率 > 15%，不值得放款

# 决策4: 为什么 reason_codes 取规则而非 SHAP？
#   → 规则结果是确定性的: "年龄不在授信范围"
#   → SHAP 是概率性的: "night_ops_ratio 贡献 +0.08"
#   → 给用户看确定原因，给风控分析师看 SHAP
```

### 换个业务：内容审核

```python
# 内容审核 — 完全相同的四层架构

async def moderate_content(text: str, user: UserProfile):
    # Layer 1: 硬规则 — 敏感词绝对拦截
    if contains_blocked_keywords(text):
        return ModerationResult(action="BLOCK", reason="HIT_BLOCKED_KEYWORD")

    # Layer 2: 模型 — BERT 违规分类
    violation_prob = bert_model.predict(text)

    # Layer 3: 融合
    if user.is_new_account and violation_prob > 0.3:
        action = "MANUAL_REVIEW"     # 新账号+中等风险 → 人工
    elif violation_prob > 0.8:
        action = "AUTO_BLOCK"        # 高危 → 自动拦截
    elif violation_prob > 0.5:
        action = "FLAGGED"           # 中危 → 标记但放行
    else:
        action = "PASS"

    # Layer 4: 策略执行
    if action == "AUTO_BLOCK": delete_post()
    elif action == "FLAGGED": flag_for_review()
    return ModerationResult(action=action)
```

| 业务 | Layer 1 硬规则 | Layer 2 模型 | Layer 3 融合 | Layer 4 策略 |
|------|--------------|-------------|-------------|-------------|
| 信贷 | 黑名单/欺诈 | XGBoost 评分 | 规则覆盖+模型兜底 | 额度/通过/拒绝 |
| 电商风控 | 黑名单IP | 欺诈概率 | 低风险自动，中风险人工 | 放行/拦截 |
| 内容审核 | 敏感词 | BERT 分类 | 高置信自动，低置信人工 | 删帖/限流/封号 |
| 医疗分诊 | 生命体征异常 | 疾病预测 | 高危+高置信直接转诊 | 急诊/门诊 |

---

## 能力 4：模型评估体系 + 线上监控闭环

### 核心代码 4a：模型评估器

```python
# src/models/evaluator.py — 上线前质量把关

class ModelEvaluator:
    """
    四个核心指标 + 阈值 — 判断模型能否上线。

    为什么是这四个？
    - AUC: 排序能力（模型能不能把坏人排在好人前面）
    - KS:  区分能力（在最佳切分点，好坏分布差多远）
    - PSI: 稳定性（训练和测试的分数分布像一个分布吗）
    - Overfit Gap: 过拟合（训练集表现远好于测试集 = 记住了噪声）
    """

    MIN_AUC = 0.65          # < 0.65 → 比随机好不了太多
    MIN_KS = 0.25           # < 0.25 → 两分布几乎重叠
    MAX_PSI = 0.25          # > 0.25 → 分布显著漂移
    MAX_OVERFIT_GAP = 0.05  # > 0.05 → 过拟合噪声

    def evaluate(self, y_train, y_train_pred,
                 y_test, y_test_pred) -> EvalReport:
        auc_train = self._calculate_auc(y_train, y_train_pred)
        auc_test = self._calculate_auc(y_test, y_test_pred)
        ks_test = self._calculate_ks(y_test, y_test_pred)
        psi = self._calculate_psi(y_train_pred, y_test_pred)
        overfit_gap = auc_train - auc_test

        failures = []
        if auc_test < self.MIN_AUC:
            failures.append(f"AUC={auc_test:.4f} < {self.MIN_AUC}")
        if ks_test < self.MIN_KS:
            failures.append(f"KS={ks_test:.4f} < {self.MIN_KS}")
        if overfit_gap > self.MAX_OVERFIT_GAP:
            failures.append(f"Overfit={overfit_gap:.4f} > {self.MAX_OVERFIT_GAP}")

        return EvalReport(
            auc_train=auc_train, auc_test=auc_test,
            ks_test=ks_test, psi=psi, overfit_gap=overfit_gap,
            passed=len(failures) == 0,
            failures=failures,
        )

    # ═══ KS 计算 — 区分力指标 ═══
    def _calculate_ks(self, y_true, y_pred) -> float:
        """
        KS = max(|累积好样本比例 - 累积坏样本比例|)

        为什么 KS 和 AUC 都要看？
        - AUC 衡量整体排序 → 评估"模型能不能把坏人排前面"
        - KS 衡量最佳切分点 → 评估"在这个点上好坏分得够不够开"
        - 高 AUC + 低 KS → 排序对但不果断，阈值附近模糊
        """
        order = np.argsort(y_pred)[::-1]          # 按预测概率降序
        y_true_sorted = y_true[order]
        n_pos = (y_true == 1).sum()
        n_neg = (y_true == 0).sum()

        cum_pos = np.cumsum(y_true_sorted == 1) / n_pos
        cum_neg = np.cumsum(y_true_sorted == 0) / n_neg
        return float(np.max(np.abs(cum_pos - cum_neg)))

    # ═══ PSI 计算 — 稳定性指标 ═══
    def _calculate_psi(self, expected, actual, bins=10) -> float:
        """
        PSI = Σ (actual_i - expected_i) × ln(actual_i / expected_i)

        为什么是 10 个分箱？
        - 分箱太多 → 每个箱样本少 → PSI 方差大
        - 分箱太少 → 丢失分布形态
        - 10 箱是 FICO 评分卡行业标准
        """
        expected_bins = np.percentile(
            expected, np.linspace(0, 100, bins + 1)
        )
        ep = np.histogram(expected, bins=expected_bins)[0] / len(expected)
        ap = np.histogram(actual, bins=expected_bins)[0] / len(actual)

        ep = np.clip(ep, 1e-6, 1)  # 防除零
        ap = np.clip(ap, 1e-6, 1)
        return float(np.sum((ap - ep) * np.log(ap / ep)))
```

### 核心代码 4b：模型熔断器

```python
# src/monitoring/circuit_breaker.py — 线上自动保护

class ModelCircuitBreaker:
    """
    状态机: CLOSED → OPEN → HALF_OPEN → CLOSED

    为什么需要自动熔断？
    - 依赖人工发现模型退化 → 几小时到几天
    - 自动熔断 → 秒级响应，保护业务
    """

    delinquency_spike_threshold = 0.30  # 逾期率突增 30% → 熔断
    # 为什么 30% 而不是 10% 或 50%？
    # - 10%: 太敏感，正常客群波动频繁触发 → 运维疲劳
    # - 50%: 太迟钝，发现时已造成大量坏账
    # - 30%: 逾期率单日波动极少超过 30%，超过 = 大概率是模型问题

    recovery_seconds = 3600  # 冷却 1 小时后尝试恢复

    def check(self, delinquency_change_ratio, psi_critical_count, error_rate):
        if self.state == BreakerState.CLOSED:
            should_open = (
                delinquency_change_ratio > 0.30
                or psi_critical_count >= 3       # 3+ 特征 PSI > 0.25
                or error_rate > 0.10
            )
            if should_open:
                self.state = BreakerState.OPEN
                self.on_break()  # 切备用模型/纯规则模式

        elif self.state == BreakerState.OPEN:
            if (time.time() - self.last_state_change
                    > self.recovery_seconds):
                self.state = BreakerState.HALF_OPEN

        elif self.state == BreakerState.HALF_OPEN:
            if (delinquency_change_ratio < 0.30
                    and psi_critical_count == 0):
                self.state = BreakerState.CLOSED
                self.on_recover()   # 切回主模型
            elif delinquency_change_ratio > 0.30:
                self.state = BreakerState.OPEN  # 重新熔断

        return self.state
```

### 换个业务：推荐系统监控

```python
# 电商推荐 — 同样的 MLOps 模式，不同指标名

class RecommendationMonitor:
    ALERT_CTR_DROP = 0.20           # 点击率降 20% → 回退
    ALERT_CONVERSION_DROP = 0.15    # 转化率降 15% → 重训

    def check(self, current_ctr, baseline_ctr, current_conv, baseline_conv):
        ctr_drop = (baseline_ctr - current_ctr) / baseline_ctr
        if ctr_drop > self.ALERT_CTR_DROP:
            self.rollback_to_previous_model()  # 回退到上一版本
```

| 业务 | 离线评估指标 | 线上监控指标 | 熔断条件 |
|------|------------|------------|---------|
| 信贷 | AUC/KS/PSI | 通过率/均分/逾期率 | 逾期率突增 30% |
| 推荐 | NDCG/CTR | 点击率/转化率 | 点击率降 20% |
| 搜索 | MRR/NDCG@10 | 首条点击率 | 首条点击率降 15% |
| 翻译 | BLEU/COMET | 人工评分抽样 | 评分降 0.3 分 |
| 语音 | WER/CER | 识别准确率 | 某方言骤降 |

---

## 能力 5：生产级降级 + 容错设计

### 核心代码：三层降级的特征获取

```python
# src/decision_engine/inference_pipeline.py 第310-350行

async def _fetch_features_with_fallback(self, request):
    """
    三层降级路径:

    路径1: 在线特征(Feast) — 实时，精确，50ms 超时
    路径2: 本地缓存 — 可能过时但可用
    路径3: 默认值 — 保守估计（宁可误杀，不可放过）

    为什么是 50ms 超时？
    整个推理 P99 目标是 < 300ms。特征获取只是其中一个环节。
    50ms = 1/6 的总预算，留给规则+模型+HTTP 开销。
    """
    t0 = time.perf_counter()

    # ── 路径1: 在线特征 — 50ms 超时 ──
    try:
        snapshot = await asyncio.wait_for(
            self.feature_service.get_online_features(request.user_id),
            timeout=0.050
        )
        return snapshot
    except asyncio.TimeoutError:
        pass  # → 进入降级

    # ── 路径2: 本地缓存 — TTL 5分钟 ──
    # 为什么缓存不是默认路径？
    # 缓存的数据可能不是最新的（用户刚操作完 App）。
    # 默认走在线（最新），在线挂了走缓存（可用）。
    cached = self.feature_service.get_cached_features(request.user_id)
    if cached:
        snapshot = FeatureSnapshot(user_id=request.user_id)
        snapshot.features = cached
        snapshot.degraded_features = list(cached.keys())  # ← 标记降级
        return snapshot

    # ── 路径3: 全默认值 — 最保守策略 ──
    # 为什么默认值偏保守（偏高风险）？
    # 不知道用户什么样 → 宁可误杀不可放过。
    # night_ops_ratio 默认 0.5（正常 0.1-0.3，偏高 = 偏保守）
    # on_time_rate 默认 0.5（正常 0.8-1.0，偏低 = 偏保守）
    # 不是 0（会放行所有未知用户），也不是 1（会拒绝所有未知用户）
    snapshot = FeatureSnapshot(user_id=request.user_id)
    snapshot.features = DegradationPolicy.get_all_defaults()
    snapshot.degraded_features = list(snapshot.features.keys())
    return snapshot
```

**降级默认值的设计 — 这是 AI 工程师的决策**：

```python
# src/decision_engine/degradation.py

class DegradationPolicy:
    DEFAULTS = {
        # 风险方向"越高越危险" → 默认偏高的中间值
        'night_ops_ratio_30d': 0.5,    # 正常 0.1-0.3, 高危 >0.6
        'overdue_cnt_hist':    1.0,    # 正常 0, 高危 >2
        # 风险方向"越低越危险" → 默认偏低的中间值
        'on_time_rate':        0.5,    # 正常 0.8-1.0, 高危 <0.3
        'monthly_income':      5000,   # 正常 5000-20000
    }
```

### 换个业务：推荐系统

```python
# 电商推荐 — 同样的三层降级

async def get_recommendations_with_fallback(user_id, n=10):
    try:
        return await asyncio.wait_for(         # 路径1: 个性化
            deep_model.recommend(user_id, n),
            timeout=0.080
        )
    except TimeoutError:
        cached = cache.get(f"recs:{user_id}")  # 路径2: 缓存
        if cached:
            return cached
    return hot_items[:n]                       # 路径3: 热门兜底
```

| 业务 | 路径1(最优) | 路径2(降级) | 路径3(兜底) |
|------|-----------|-----------|-----------|
| 信贷 | 实时特征 | 缓存特征 | 默认值(保守) |
| 推荐 | 深度学习 | 协同过滤缓存 | 热门榜单 |
| 搜索 | 语义搜索 | 关键词匹配 | 时间倒序 |
| 语音 | 云端大模型 | 本地小模型 | 预设回复 |

---

## 能力 6：LLM 应用架构（NL2SQL / RAG / LangGraph）

### 6a. NL2SQL — 自然语言查数据仓库

**为什么数仓工程师天然适合做 NL2SQL**：NL2SQL 的瓶颈不是 LLM 生成 SQL 的能力，而是 **Schema Context 的质量**——你写的 COMMENT 注释就是 LLM 理解列语义的关键。

```python
# src/nl2sql/sql_generator.py（新增模块）

class NL2SQLGenerator:
    """
    将自然语言问题 → 数据仓库 SQL 查询。

    四个步骤:
    1. Schema Context 注入 — 从 SchemaRegistry 动态加载表结构
    2. LLM 生成 SQL — temperature=0.0，不需要创意只需要精确
    3. 安全校验 — 永远不信任 LLM 的输出
    4. 执行 + 返回
    """

    def __init__(self, schema_registry: SchemaRegistry):
        self.registry = schema_registry

    # ═══ Step 1: 构造 System Prompt — Schema Context ═══
    def _build_system_prompt(self) -> str:
        """
        从 SchemaRegistry 动态读取表结构，构造 LLM 上下文。

        为什么用 SchemaRegistry 而不是硬编码？
        - 表结构会变（加列、改类型、加表）
        - 硬编码 → 每次变化都要改 Prompt → 遗漏风险
        - SchemaRegistry → 自动感知变化 → Prompt 始终最新
        """
        tables = self.registry.list_tables()
        schema_parts = []
        for t in tables:
            cols = [
                f"  {c.name:30s} {c.type:10s} -- {c.description}"
                for c in t.columns
            ]
            schema_parts.append(
                f"表 {t.layer}.{t.table_name}:\n"
                + "\n".join(cols)
            )

        return f"""你是 SQL 专家，查询信贷风控数据仓库。

可用表:
{chr(10).join(schema_parts)}

规则:
1. 只生成 SELECT — 禁止 INSERT/UPDATE/DELETE/DROP
2. 日期过滤用 dt 列, 格式 YYYY-MM-DD
3. "通过率" = approval_rate 列
4. "逾期率" = overdue_cnt_hist > 0 的用户占比

只输出 SQL，不要解释。"""

    # ═══ Step 2: LLM 生成 SQL ═══
    def generate_sql(self, question: str) -> str:
        response = self.llm.chat(
            system=self._build_system_prompt(),
            user=question,
            temperature=0.0,  # SQL 生成不需要创意 → 0 温度保证确定性
        )
        return self._extract_sql(response)

    # ═══ Step 3: 安全校验 — 永远不信任 LLM ═══
    def validate_sql(self, sql: str) -> tuple[bool, str]:
        """LLM 可能幻觉出危险 SQL — 必须过三道校验"""
        sql_upper = sql.upper().strip()

        # 校验1: 禁止危险关键字
        forbidden = ['DROP', 'DELETE', 'TRUNCATE', 'INSERT',
                     'UPDATE', 'ALTER', 'CREATE']
        for kw in forbidden:
            if kw in sql_upper:
                return False, f"禁止关键字: {kw}"

        # 校验2: 必须有分区过滤（防止全表扫描）
        if 'DT' not in sql_upper:
            return False, "查询必须包含 dt 分区过滤"

        # 校验3: 必须是 SELECT
        if not sql_upper.startswith('SELECT'):
            return False, "只允许 SELECT"

        return True, "OK"

    # ═══ Step 4: 执行 ═══
    def query(self, question: str) -> dict:
        sql = self.generate_sql(question)
        valid, error = self.validate_sql(sql)
        if not valid:
            return {"success": False, "error": error, "sql": sql}

        result_df = self._execute_sql(sql)
        return {
            "success": True, "sql": sql,
            "data": result_df.to_dict(orient='records'),
            "row_count": len(result_df),
        }
```

**一次完整的 NL2SQL 请求过程**：

```
用户: "上周各渠道通过率？"
  → System Prompt 注入: "表 ads_model_monitor_daily, 列 approval_rate DOUBLE"
  → LLM 生成: SELECT channel, AVG(approval_rate) FROM ads_model_monitor_daily
              WHERE dt >= '2026-06-30' AND dt <= '2026-07-06' GROUP BY channel
  → 安全校验: ✓ 无 DROP/DELETE  ✓ 有 dt 过滤  ✓ 是 SELECT
  → 执行: APP_IOS 72%, APP_ANDROID 65%, H5 58%
```

### 6b. RAG — 项目知识库问答

```python
# src/rag/retrieval_qa.py（新增模块）

class WarehouseRAG:
    """
    基于项目文档的 RAG 问答。
    知识库: config/schemas/*.yaml + config/ddl/*.sql + 架构文档

    切片策略（关键！比向量模型更重要）:
    - YAML: 按顶级 key 切（一个表定义 = 一个 chunk）
    - SQL:  按 CREATE TABLE 语句切（一个建表语句 = 一个 chunk）
    - MD:   按 ## 标题切（一个章节 = 一个 chunk）

    为什么按语义边界而不是固定长度？
    "把一段话切两半" → 丢失上下文 → 检索结果不完整
    每个 chunk 自包含 → 检索质量高
    """

    def build_index(self):
        docs = []
        # 加载 schema → 每个表一个 chunk
        for yf in self.project_root.glob("config/schemas/*.yaml"):
            data = yaml.safe_load(open(yf))
            for key, val in data.items():
                docs.append(Document(
                    text=yaml.dump({key: val}),
                    metadata={"source": str(yf), "type": "schema", "key": key}
                ))
        # 加载 DDL → 每个建表语句一个 chunk
        # 加载规则 → 每条规则一个 chunk
        self.vector_store = ChromaDB.from_documents(docs, embedding_fn)

    def ask(self, question: str) -> str:
        """检索 Top-3 → 构造 Prompt → LLM 回答"""
        relevant = self.vector_store.similarity_search(question, k=3)
        context = "\n\n".join(d.text for d in relevant)
        sources = [d.metadata['source'] for d in relevant]

        return self.llm.chat(f"""根据以下文档回答:

{context}

问题: {question}

如果文档中没有相关信息，说"未找到"。
附上来源: {', '.join(set(sources))}""", temperature=0.0)
```

### 6c. LangGraph — 多步骤审批工作流

```python
# 信贷审批状态机 — LangGraph 实现

from langgraph.graph import StateGraph, END

class ApprovalState(TypedDict):
    user_id: str
    features: dict
    score: float
    decision: str          # APPROVE/REJECT/MANUAL_REVIEW/PENDING_DOCS
    explanation: str       # LLM 生成
    required_docs: list    # 补充材料清单

def build_approval_graph():
    graph = StateGraph(ApprovalState)

    # 注册节点（LLM 节点和普通函数节点统一 add_node）
    graph.add_node("rule_check", rule_check_node)
    graph.add_node("model_score", model_score_node)
    graph.add_node("request_docs", request_docs_node)              # LLM
    graph.add_node("generate_rejection_letter", rejection_node)    # LLM
    graph.add_node("disburse", disburse_node)

    # 条件路由
    graph.add_conditional_edges(
        "rule_check", route_after_rules,
        {"REJECT": "generate_rejection_letter", "PASS": "model_score"}
    )
    graph.add_conditional_edges(
        "model_score", route_after_score,
        {"APPROVE": "disburse",
         "MANUAL_REVIEW": "request_docs",
         "REJECT": "generate_rejection_letter"}
    )

    graph.set_entry_point("rule_check")
    return graph.compile()

# 审批流程可视化:
# rule_check ──REJECT──→ rejection_letter ──→ END
#     │
#     └──PASS──→ model_score ──APPROVE──→ disburse ──→ END
#                     │
#                     ├──MANUAL_REVIEW──→ request_docs ──→ END(等待用户上传)
#                     └──REJECT──→ rejection_letter ──→ END
```

**LangGraph vs 手写状态机**：

| 手写 if-else | LangGraph |
|-------------|-----------|
| 状态流转硬编码，改流程要改代码 | 节点和边可配置，加节点 = 一行 `add_node` |
| 异步操作（等用户上传材料）要自己管理状态 | checkpointer 自动序列化/恢复状态 |
| 流程图要额外画 | `get_graph().draw_mermaid_png()` 直接出图 |

### 换个业务：客服工单处理

```python
# 客服系统 — 完全相同的 LangGraph 模式

def build_customer_service_workflow():
    graph = StateGraph(TicketState)
    graph.add_node("classify", classify_node)       # LLM: 意图分类
    graph.add_node("auto_reply", auto_reply_node)   # LLM: 自动回复
    graph.add_node("route_agent", route_node)        # 路由人工

    graph.add_conditional_edges(
        "classify", route_by_intent,
        {"refund": "auto_reply",          # 退款 → 自动
         "technical": "route_agent",      # 技术 → 人工
         "complaint": "route_agent"}      # 投诉 → 升级
    )
    return graph.compile()
```

| 业务 | NL2SQL 问题示例 | RAG 知识库 | LangGraph 工作流 |
|------|---------------|-----------|-----------------|
| 信贷 | "上周通过率？" | Schema+DDL+规则 | 审批: 规则→模型→人工→放款 |
| 电商 | "哪个品类转化最高？" | 运营SOP+促销规则 | 促销审批: 提报→审核→库存→上线 |
| 医疗 | "糖尿病平均住院天数？" | 诊疗指南+药品说明 | 会诊: 发起→分配→报告→归档 |
| 客服 | "本周投诉最多原因？" | FAQ+退换货政策 | 退款: 申请→审核→退货→退款 |
| HR | "技术岗面试通过率？" | JD+薪酬政策+题库 | 招聘: 需求→审批→发布→面试→Offer |

---

## 能力 7：可解释性 + 合规性

### 核心代码：SHAP 解释 + reason_code 追溯

```python
# src/models/trainer.py — SHAP 特征贡献

class ModelWrapper:
    def explain(self, feature_vector: np.ndarray, top_n: int = 10) -> dict:
        """
        返回 Top-N 特征的 SHAP 贡献值。

        SHAP 值含义:
        - 正值(+): 推高违约概率 → 贡献了风险
        - 负值(-): 拉低违约概率 → 降低了风险
        - 绝对值: 贡献大小

        为什么 SHAP 而不是 XGBoost 自带的 feature_importance？
        - feature_importance 是全局的: "模型最看重哪个特征"
        - SHAP 是局部的: "这个用户为什么被拒"
        - 信贷需要的是后者
        """
        if self._shap is None:
            return {}
        shap_vals = self._shap.shap_values(
            xgb.DMatrix(feature_vector.reshape(1, -1),
                       feature_names=self.feature_names)
        )[0]
        return dict(sorted(
            zip(self.feature_names, map(float, shap_vals)),
            key=lambda x: abs(x[1]), reverse=True
        )[:top_n])


# src/decision_engine/rule_engine.py — 规则 reason_code 追溯

class RuleEngine:
    def evaluate(self, context: dict) -> list[RuleResult]:
        """
        每条命中规则都带 reason_code。

        为什么设计 reason_code 体系？
        - RC_BL001 = 命中黑名单 → 明确告诉运营/用户具体原因
        - 不是返回 True/False → 返回"为什么 True"
        - reason_code 进入决策日志 → 可做规则效能分析:
          哪条规则命中率最高？误杀率最高？是否该调整阈值？
        """
        results = []
        for group in self.rule_groups:
            for rule_def in group.get('rules', []):
                if self.evaluator.evaluate(
                    rule_def['condition'], context
                ):
                    results.append(RuleResult(
                        rule_id=rule_def['id'],
                        decision=Decision(rule_def['decision']),
                        reason_code=rule_def.get(
                            'reason_code', 'RC_DEFAULT'
                        ),
                        reason_desc=rule_def.get('reason_desc', ''),
                        triggered=True,
                    ))
        return results
```

**YAML 规则配置中 reason_code 的设计**：

```yaml
# config/rules/credit_policy.yaml
# 每条规则都有唯一 reason_code，可被监控系统追踪

rules:
  - id: BLACKLIST_HIT
    condition: "user_id_in_blacklist == True"
    decision: REJECT
    reason_code: "RC_BL001"            # ← 唯一编码，监控可追踪
    reason_desc: "命中内部黑名单"       # ← 人类可读，可展示给用户
    overridable: false

  - id: FRAUD_SCORE_HIGH
    condition: "fraud_score > 0.8"
    decision: REJECT
    reason_code: "RC_FR001"
    reason_desc: "反欺诈评分过高"
```

**用户申诉时，系统提供完整证据链**：

```
决策 ID: req_a1b2c3d4e5f6
用户: user_000042

── 规则引擎 ──
✓ BLACKLIST_HIT     → 未命中
✓ AGE_RESTRICTION   → 未命中 (年龄=30，范围 18-65)

── 模型评分 ──
违约概率: 0.12 → 评分: 672/900 → APPROVE

── SHAP Top 3 ──
1. on_time_rate=0.33     → +0.12 (历史还款率低)
2. overdue_cnt_hist=2    → +0.08 (有逾期记录)
3. monthly_income=8000   → -0.05 (收入较高，拉低风险)

── 最终 ──
APPROVE, 额度 ¥5,000
```

### 跨业务映射

| 业务 | 可解释性需求 | 合规要求 |
|------|------------|---------|
| 信贷 | "为什么被拒？" → SHAP + reason_code | 不能使用性别/种族等敏感特征 |
| 医疗 | "为什么诊断高风险？" → 关键异常指标 | 不能使用患者宗教信仰 |
| 招聘 | "为什么不匹配？" → 技能差距 | 不能使用性别/年龄/婚育 |
| 保险 | "为什么保费高？" → 风险因子权重 | 不能使用基因信息 |
| 推荐 | "为什么推荐这条？" → 浏览历史+标签 | 不能形成信息茧房 |

---

## 能力总结：面试时怎么说

### 七个能力一句话

| 能力 | 面试一句话 | 代码证明 |
|------|-----------|---------|
| PIT 样本 | "我设计过严格防时间泄漏的样本生成，用 merge 而非 concat" | `ads_layer.py` |
| 特征工程 | "我能从任意事件日志提取特征：时间窗口+比率衍生+缺失策略" | `dws_layer.py` |
| 规则+模型融合 | "我设计过四层决策：硬规则短路→模型评分→融合→策略" | `inference_pipeline.py` |
| 评估+监控 | "我搭建过离线评估+在线监控+自动熔断的 MLOps 闭环" | `evaluator.py + circuit_breaker.py` |
| 降级容错 | "我设计过三层降级：在线→缓存→默认值，每层有触发条件" | `inference_pipeline.py` |
| LLM 应用 | "我用 NL2SQL 让业务查数仓，用 LangGraph 编排审批工作流" | NL2SQL/RAG/LangGraph |
| 可解释性 | "我用 SHAP+reason_code 为每笔决策提供三层可追溯解释" | `ModelWrapper.explain()` |

### 面试官关心的五个问题

1. **能不能把业务问题抽象成 AI 方案？** → 规则+模型融合架构
2. **知不知道模型上线后会发生什么？** → 监控+熔断+降级
3. **懂不懂数据？能不能从脏数据中提炼出特征？** → DWD→DWS 特征工程
4. **会不会用 LLM？不只是调 API？** → NL2SQL + RAG + LangGraph
5. **有没有工程思维？代码能上生产？** → FastAPI + 异步 + 降级 + 熔断

### 你的独特卖点

> "我是从数据仓库转型的 AI 应用开发工程师。独特优势是**全链路打通**：从底层数据建模(ODS/DWD/DWS/ADS)到
> 上层 AI 应用(训练+推理+监控+熔断)独立完成。同时擅长 LLM 应用架构——NL2SQL 让业务自然语言查数仓，
> RAG 把项目文档变知识库，LangGraph 编排多步骤 AI 工作流。能从数据库做到 AI 服务，这是单一技术栈 AI 工程师不具备的广度。"
