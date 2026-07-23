# Day 04：模型评估 + 线上监控 + 自动熔断

> 目标：掌握 MLOps 闭环——上线前评估(AUC/KS/PSI) → 在线监控 → 自动熔断 → 触发重训。

---

## 一、模型不是训完就结束了（20min）

### 1.1 上线后的模型会退化

```
Day 1:  模型上线，AUC=0.72，通过率 65% → 一切正常
Day 30: 通过率降到 45%，但不知道为什么
Day 60: 逾期率突然翻倍 → 发现欺诈手段变了，模型已经失效 30 天

如果有监控:
Day 30: PSI 告警 → "特征分布漂移" → 触发人工排查 → 确认需要重训
Day 35: 新模型上线，恢复正常

结论: 没有监控的模型 = 定时炸弹
```

---

## 二、上线前评估：四个核心指标（1h）

打开 `src/models/evaluator.py`：

### 2.1 AUC — 排序能力

```
AUC 回答: "随机抽一个好人一个坏人，模型把坏人排在好人前面的概率"

AUC = 0.5 → 和扔硬币一样（完全没用）
AUC = 0.65 → 勉强可用（比随机好一点）
AUC = 0.75 → 良好
AUC = 0.85 → 优秀
AUC = 0.95 → 优秀但要检查是否过拟合或时间泄漏

项目的阈值: MIN_AUC = 0.65
```

### 2.2 KS — 区分能力

```python
# src/models/evaluator.py — _calculate_ks()

def _calculate_ks(self, y_true, y_pred) -> float:
    """
    KS = max(|好样本累积比例 - 坏样本累积比例|)

    为什么 AUC 和 KS 都要？
    - AUC 衡量整体排序 → "模型能不能把坏人排前面"
    - KS 衡量最佳切分点 → "在最优阈值处，好坏分得够不够开"
    - 高 AUC + 低 KS → 排序对但不果断（阈值附近好坏重叠严重）

    直观理解: KS = 0.30 → 在最佳切分点，能区分 30% 的好人和坏人
    """
    一句话定义：衡量模型在哪个分数段上，好客户和坏客户的累计分布差距最大。这个最大差距就是 KS 值。

计算逻辑（直观理解）：
将模型输出的分数从高到低排序（高分=好，低分=坏）。
计算每个分数点下，累计好客户占比（TPR）和累计坏客户占比（FPR）。
两者差值最大的那个点，就是 KS 值。
金融信贷实战解读：
KS 范围	业务含义	信贷场景建议
< 0.2	几乎无区分	模型不可用
0.2 - 0.3	勉强可用	可能需要补充外部数据源增强效果
0.3 - 0.4	较好	信贷风控模型的可接受下限
0.4 - 0.5	优秀	行业领先水平
0.5 - 0.6	极强	需警惕过拟合，交叉验证确认
> 0.75	可疑	强烈怀疑数据泄露或逻辑过拟合
AUC 与 KS 的关系：
KS 值是 AUC 的一个截面切片，它只看“差距最大的那一个点”。
一般来说，KS ≈ 1.4 ~ 1.7 倍 × (AUC - 0.5)（经验关系，非严格公式）。
实战取舍：如果两个模型 AUC 相近，选 KS 更高的那个——因为它说明在某个决策阈值上，可以更高效地拦截坏人。
    order = np.argsort(y_pred)[::-1]          # 按预测概率降序
    y_true_sorted = y_true[order]
    cum_pos = np.cumsum(y_true_sorted == 1) / (y_true == 1).sum()
    cum_neg = np.cumsum(y_true_sorted == 0) / (y_true == 0).sum()
    return float(np.max(np.abs(cum_pos - cum_neg)))



```

### 2.3 PSI — 分布稳定性

```python
# src/models/evaluator.py — _calculate_psi()

def _calculate_psi(self, expected, actual, bins=10) -> float:
    """
    PSI = Σ (actual_i - expected_i) × ln(actual_i / expected_i)

    为什么是 10 个分箱？
    - 太少 → 丢失分布形态
    - 太多 → 每个箱样本太少，PSI 不稳定
    - 10 箱是 FICO 评分卡的行业标准

    PSI 解读:
    < 0.10: 分布稳定 ✓
    0.10-0.25: 轻微漂移，关注
    > 0.25: 严重漂移，建议重训
    """
    expected_bins = np.percentile(expected, np.linspace(0, 100, bins + 1))
    ep = np.histogram(expected, bins=expected_bins)[0] / len(expected)
    ap = np.histogram(actual, bins=expected_bins)[0] / len(actual)
    ep = np.clip(ep, 1e-6, 1); ap = np.clip(ap, 1e-6, 1)
    return float(np.sum((ap - ep) * np.log(ap / ep)))
```

---

## 三、熔断器：不让坏模型继续害人（40min）

打开 `src/monitoring/circuit_breaker.py`：

```python
class ModelCircuitBreaker:
    """
    状态机: CLOSED → OPEN → HALF_OPEN → CLOSED

    CLOSED(正常):    模型在正常服务
    OPEN(熔断):      切换到备用模型/纯规则模式
    HALF_OPEN(试探): 冷却期后，用 5% 流量试探恢复
    """

    delinquency_spike_threshold = 0.30  # 逾期率突增 30% → 熔断
    # 为什么 30%？
    # 10% → 太敏感，正常业务波动频繁触发
    # 50% → 太迟钝，等发现时坏账已经造成
    # 30% → 逾期率极少单日波动 30%，超过 = 大概率模型问题

    recovery_seconds = 3600  # 冷却 1 小时

    def check(self, delinquency_change, psi_critical_count, error_rate):
        if self.state == BreakerState.CLOSED:
            # 正常 → 检查是否需要熔断
            if (delinquency_change > 0.30
                or psi_critical_count >= 3      # 3+ 特征 PSI>0.25
                or error_rate > 0.10):
                self.state = BreakerState.OPEN
                self.on_break()  # 切换降级模式

        elif self.state == BreakerState.OPEN:
            # 熔断中 → 冷却后试探恢复
            if time_since_change > self.recovery_seconds:
                self.state = BreakerState.HALF_OPEN

        elif self.state == BreakerState.HALF_OPEN:
            # 试探中 → 指标正常就恢复，恶化就重新熔断
            if (delinquency_change < 0.30 and psi_critical_count == 0):
                self.state = BreakerState.CLOSED
                self.on_recover()
            elif delinquency_change > 0.30:
                self.state = BreakerState.OPEN  # 重新熔断
```

---

## 四、动手练习（1.5h）

### 练习 1：手写 KS 和 PSI 计算（45min）

```python
import numpy as np

def calculate_ks(y_true, y_pred):
    """手写 KS — 不能调 sklearn"""
    # 1. 按预测概率降序排列
    order = np.argsort(y_pred)[::-1]
    y_sorted = y_true[order]

    # 2. 计算好坏样本的累积比例
    n_pos = (y_true == 1).sum()
    n_neg = (y_true == 0).sum()
    cum_pos = np.cumsum(y_sorted == 1) / n_pos
    cum_neg = np.cumsum(y_sorted == 0) / n_neg

    # 3. KS = 最大差值
    return float(np.max(np.abs(cum_pos - cum_neg)))

# 验证：完美分离 → KS ≈ 1.0
y_true = np.array([0]*100 + [1]*100)
y_perfect = np.array([0.1]*100 + [0.9]*100)
print(f"完美 KS: {calculate_ks(y_true, y_perfect):.4f}")  # 应接近 1.0

y_random = np.random.random(200)
print(f"随机 KS: {calculate_ks(y_true, y_random):.4f}")   # 应接近 0.0


def calculate_psi(expected, actual, bins=10):
    """手写 PSI — 不能调库"""
    # 1. 用 expected 的百分位作为分箱边界（保持固定！）
    boundaries = np.percentile(expected, np.linspace(0, 100, bins + 1))

    # 2. 统计每箱占比
    ep = np.histogram(expected, bins=boundaries)[0] / len(expected)
    ap = np.histogram(actual, bins=boundaries)[0] / len(actual)

    # 3. PSI 公式，防止除零
    ep = np.clip(ep, 1e-6, 1)
    ap = np.clip(ap, 1e-6, 1)
    return float(np.sum((ap - ep) * np.log(ap / ep)))

# 验证：同分布 → PSI ≈ 0
a = np.random.beta(3, 5, 1000)
b = np.random.beta(3, 5, 1000)
print(f"同分布 PSI: {calculate_psi(a, b):.4f}")  # 应接近 0
```

### 练习 2：设计推荐系统的监控+熔断（30min）

```python
class RecommendationMonitor:
    """推荐系统监控器 — 和信贷完全相同的 MLOps 模式"""

    def __init__(self, baseline_ctr, baseline_conversion):
        self.baseline_ctr = baseline_ctr
        self.baseline_conversion = baseline_conversion

    def check(self, current_ctr, current_conversion, coverage):
        alerts = []
        ctr_drop = (self.baseline_ctr - current_ctr) / self.baseline_ctr
        conv_drop = (self.baseline_conversion - current_conversion) / \
                     self.baseline_conversion

        if ctr_drop > 0.20:
            alerts.append(f"⚠ 点击率下降 {ctr_drop:.1%} → 建议回退模型")
        if conv_drop > 0.15:
            alerts.append(f"⚠ 转化率下降 {conv_drop:.1%} → 建议触发重训")
        if coverage < 0.50:
            alerts.append(f"⚠ 推荐覆盖率 {coverage:.1%} → 模型可能坍塌")

        return alerts
```

---

## 五、今天要点

```
MLOps 闭环:
  上线前 → AUC/KS/PSI 三指标 + 阈值
  上线后 → 每日监控指标对比基线
  异常时 → 熔断 → 切备用 → 触发重训

四个指标的面试说法:
  AUC = "模型能不能把坏的排前面"
  KS = "在最优阈值处，好坏能分多开"
  PSI = "训练和线上分布像不像"
  Overfit Gap = "有没有记住噪声"
```

---

## 六、检查清单

- [ ] 能手写 calculate_ks() 和 calculate_psi()（不调库）
- [ ] 能解释为什么 PSI 用 10 个分箱
- [ ] 能解释为什么熔断阈值是 30% 不是 10% 或 50%
- [ ] 完成了推荐系统监控器
