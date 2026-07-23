---
source: learning
source_label: 学习复习计划
category: AI应用开发
count: 30
generated: 2026-07-23T15:44:23.592830
---

# 学习复习计划 · AI应用开发

> 共 30 题

---

## 1. 请举例说明一个让你记住一辈子的例子（20min）如何实现？

> ID: `L001`

### 1.1 完美的离线模型，归零的线上效果


```
场景：你训练了一个"用户流失预测"模型。

训练数据构造方式 A（错误）:
  X = 用户今天的所有行为特征（包括卸载 App 这个行为）
  y = 用户今天是否流失
  模型学到了: "只要用户执行了'卸载App'动作 → 一定会流失"
  AUC = 0.99 ✨ 完美！

模型上线后:
  用户还没卸载 → 模型说"不会流失"
  用户卸载了 → 你来告诉他"你要流失了" ← 毫无意义

AUC 0.99 是假的，因为模型作弊了。
它看到了"考试答案"（卸载行为）再去"预测考试结果"（是否流失）。

```

### 1.2 什么是时间泄漏


```
时间泄漏 = 用"今天之后的信息"预测"今天的结果"

正确做法:
  X(T时刻的特征) → 模型 → 预测 y(T+N时刻的结果)

时间泄漏（错误）:
  X(T+N时刻的特征) → 模型 → 预测 y(T时刻的结果)
  或
  X(T时刻的特征中混入了T+N的信息) → 模型 → 预测 y(T+N时刻的结果)

```

**在信贷项目中**：


```
特征快照时间 = 2026-07-01（申请日）
标签观察时间 = 2026-08-01（30天后是否逾期）

✅ 正确的样本: X(07-01的特征) → y(08-01的逾期标签)
❌ 时间泄漏:    X(08-01的特征) → y(08-01的逾期标签)
               （用还款结果预测逾期，模型学会了"已经还了=不会逾期"）

```

---

---

## 2. 请举例说明从代码看 PIT 正确性（1h）如何实现？

> ID: `L002`

### 2.1 阅读项目核心代码

打开 `src/data/warehouse/ads_layer.py` 第 41-81 行：


```python
def build_training_samples(
    self,
    dws_wide_table: pd.DataFrame,   # 用户在 T 时刻的特征快照
    label_df: pd.DataFrame,          # 用户在 T+30 天的逾期标签
    performance_window_days: int = 30,
) -> pd.DataFrame:
    """
    ★ 这段代码看似简单，但承载了整个建模流程最重要的假设：
    ★ dt_特征 < dt_标签

    如果这个假设被破坏 → 模型学到的都是假规律 → 上线即报废
    """
    samples = dws_wide_table.merge(
        label_df,
        on='user_id',        # 同一个用户
        how='inner',         # 必须两个时间点都有数据
    )
    return samples

```

**为什么用 `merge` 而不是 `pd.concat`？**


```python
# 对比实验：三种拼接方式

import pandas as pd
import numpy as np

# 模拟数据
features = pd.DataFrame({
    'user_id': ['u1', 'u2', 'u3'],
    'feature_a': [1.0, 2.0, 3.0],
    'feature_time': ['2026-07-01', '2026-07-01', '2026-07-01'],
})
labels = pd.DataFrame({
    'user_id': ['u3', 'u1', 'u2'],  # ← 注意！顺序和 features 不一样！
    'label': [0, 1, 0],
    'label_time': ['2026-08-01', '2026-08-01', '2026-08-01'],
})

# 方式 A: concat — 按行号对齐（不关心 user_id）
samples_A = pd.concat([features, labels], axis=1)
print("concat 结果:")
print(samples_A)
# user_id_x  u1  1.0  → label=0   ✅ 碰巧对 (同一行对齐了)
# user_id_x  u2  2.0  → label=1   ❌ 错！u2 的特征配了 u1 的标签
# user_id_x  u3  3.0  → label=0   ❌ 错！u3 的特征配了 u2 的标签

# 方式 B: merge — 按 user_id 关联（不关心行号）
samples_B = features.merge(labels, on='user_id', how='inner')
print("merge 结果:")
print(samples_B)
# u1  1.0  → label=1   ✅ 正确（merge 按 user_id 配对了）
# u2  2.0  → label=0   ✅ 正确
# u3  3.0  → label=0   ✅ 正确

```

**核心教训**：`concat` 假设两个 DataFrame 的行顺序一致——这个假设在生产中几乎永远不成立。`merge` 用 key 关联——key 是事实，行号是巧合。

### 2.2 谁保证了"特征时间 < 标签时间"？

两层保证：


```python
# 第一层：标签生成时（上游保证）
# scripts/generate_data_pipeline.py 第 122 行
label_df = pd.DataFrame({
    'user_id': users,
    'label': np.random.choice([0, 1], len(users)),
    'label_date': dt,  # ← 生产中是 dt + 30 天后的逾期观察
})

# 第二层：拼接时（本层保证）
# merge 只负责按 user_id 关联，不强写时间约束。
# 但如果在 SQL 中执行（生产环境），可以加显式约束：
# SELECT w.*, l.label
# FROM dws.user_risk_feature_wide w
# JOIN labels l ON w.user_id = l.user_id
#   AND w.dt = DATE_SUB(l.label_date, 30)  ← 时间约束写进 WHERE

```

---

---

## 3. 请讲讲PIT 样本构建 — 时间泄漏是 AI 工程师的第一课中的动手练习（1.5h）

> ID: `L003`

### 练习 1：写时间泄漏检测器（30min）


```python
def detect_time_leakage(
    samples: pd.DataFrame,
    feature_time_col: str,
    label_time_col: str,
) -> dict:
    """
    检测训练样本中是否存在时间泄漏。
    """
    # ★ 参考答案
    feature_dt = pd.to_datetime(samples[feature_time_col])
    label_dt = pd.to_datetime(samples[label_time_col])

    leaked = feature_dt >= label_dt
    leaked_indices = samples.index[leaked].tolist()
    n_leaked = len(leaked_indices)
    n_total = len(samples)

    return {
        "total_samples": n_total,
        "leaked_samples": n_leaked,
        "leak_rate": round(n_leaked / n_total, 4) if n_total > 0 else 0.0,
        "leaked_indices": leaked_indices,
        "is_critical": (n_leaked / n_total > 0.01) if n_total > 0 else False,
    }


# 测试用例
test_samples = pd.DataFrame({
    'user_id': ['u1', 'u2', 'u3', 'u4', 'u5'],
    'feature_dt': [
        '2026-07-01', '2026-07-01',
        '2026-07-01', '2026-07-01', '2026-08-01'
    ],
    'label_dt': [
        '2026-08-01', '2026-08-01',
        '2026-08-01', '2026-08-01', '2026-07-15'
    ],
})
result = detect_time_leakage(test_samples, 'feature_dt', 'label_dt')
print(result)
# 预期: total=5, leaked=1 (u5: 2026-08-01 >= 2026-07-15), is_critical=False (20% > 1%)

```

### 练习 2：为电商推荐写 PIT 样本构建（45min）


```python
def build_电商推荐_训练样本(
    user_features: pd.DataFrame,   # 曝光时刻的特征
    click_labels: pd.DataFrame,    # T+7 的购买标签
) -> pd.DataFrame:
    """
    电商推荐场景的 PIT 样本构建。
    """
    # ★ 参考答案
    # 1. merge 按 user_id + item_id 关联（比信贷多一维）
    samples = user_features.merge(
        click_labels,
        on=['user_id', 'item_id'],
        how='inner',           # 必须两个时间点都有数据
    )

    # 2. 显式过滤时间泄漏
    samples['show_time'] = pd.to_datetime(samples['show_time'])
    samples['click_time'] = pd.to_datetime(samples['click_time'])
    samples = samples[samples['show_time'] < samples['click_time']]

    return samples


# 测试数据
user_features = pd.DataFrame({
    'user_id': ['u1', 'u1', 'u2'],
    'item_id': ['A', 'B', 'A'],
    'show_time': ['2026-07-01', '2026-07-01', '2026-07-01'],
    'user_age': [25, 25, 30],
})
click_labels = pd.DataFrame({
    'user_id': ['u1', 'u2'],
    'item_id': ['A', 'A'],
    'label': [1, 0],
    'click_time': ['2026-07-05', '2026-07-10'],
})

samples = build_电商推荐_训练样本(user_features, click_labels)
print(samples[['user_id', 'item_id', 'label', 'show_time', 'click_time']])
# 预期: u1-A 保留(label=1, 07-01 < 07-05), u2-A 保留(label=0, 07-01 < 07-10)
# u1-B 没有标签行 → inner join 自动丢弃
print(f"\n样本数: {len(samples)}")  # 预期: 2

```

### 练习 3：时间泄漏会怎样？（15min）

运行项目中的模型训练，观察时间泄漏的效果：


```bash
cd credit_risk_control_system

# 先看"正常"的模型（数据是随机生成的，所以效果差——这是预期的）
python3 scripts/train_model.py --from-warehouse --n-samples 2000
# 观察: AUC(train) ≈ 0.99, AUC(test) ≈ 0.47 → 严重过拟合随机噪声

# 思考: 如果 AUC(test) = 0.95（非常高），反而是坏事！
# 说明可能存在时间泄漏，模型看到了不该看的信息。

```

---

---

## 4. 请讲讲PIT 样本构建 — 时间泄漏是 AI 工程师的第一课中的跨业务思考（30min）

> ID: `L004`

### 场景 1：网约车 "ETA 预测"


```
模型: 预测"订单被接单后到乘客上车的等待时间"

特征: 接单时刻的司机位置、路况、天气
标签: 实际等待时间

问题: 如果特征里包含了"司机接单后的 GPS 轨迹"，有什么问题？
答案: 模型看到了"司机正在驶向乘客"的事实 → 它不需要预测路况，
      直接看"司机到哪了"就行 → 这和"用还款结果预测逾期"是一回事。

```

### 场景 2：医疗 "再入院预测"


```
模型: 预测"患者出院后 30 天内会不会再次入院"

特征: 出院时的诊断、用药、生命体征
标签: 30 天内是否再次入院

问题: 如果特征里包含了"出院后的门诊记录"，有什么问题？
答案: 模型看到"患者出院后频繁复诊"→ 预测会再入院。
      但出院时你并不知道患者会不会去复诊！
      这是典型的"用未来信息预测未来结果"。

```

---

---

## 5. 请讲讲PIT 样本构建 — 时间泄漏是 AI 工程师的第一课中的今日要点

> ID: `L005`

```
核心公式:
  ✅ 正确的训练样本: X(T) → y(T+N)
  ❌ 时间泄漏:       X(T+N) → y(T+N)

三个铁律:
  1. merge on key, never concat by index
  2. 显式过滤 feature_time < label_time（双重保险）
  3. AUC(test) 异常高（>0.95）→ 先怀疑时间泄漏，再高兴

```

---

---

## 6. 请讲讲PIT 样本构建 — 时间泄漏是 AI 工程师的第一课中的检查清单

> ID: `L006`

- [ ] 能用自己的话解释"时间泄漏"并举例
- [ ] 能说出 concat vs merge 的区别和风险
- [ ] 完成了 `detect_time_leakage()` 函数
- [ ] 完成了电商推荐 PIT 样本构建
- [ ] 理解了为什么 AUC(test)=0.99 反而可能是坏事


我们把这五个点逐一拆解，用最直白的语言说清楚，并结合信贷/电商场景给出例子和代码思路。

---

### 1. 用自己的话解释“时间泄漏”并举例
**时间泄漏**就是：训练模型时，不小心把“未来”的信息当成了特征，让模型在训练时提前看到了答案。  
就像考试前，老师提前把考题答案告诉你，你考了 100 分，但真正上考场时你根本不会，因为考场上没有答案。

**信贷实例**：  
- 目标：预测用户申请贷款后 **30 天内会不会逾期**。  
- 标签时间：申请日 +30 天（比如 1 月 30 日的逾期标记）。  
- 特征：应该使用 **1 月 30 日之前** 的数据，比如申请时点的信用分、近 30 天的登录次数。  
- **泄漏**：如果你用了用户在 2 月 5 日的“还款金额”作为特征，那模型就相当于看到“他后来还了钱”这个未来事实，学会了这个作弊规律。最终离线 AUC 可能高达 0.99，但上线后 2 月 5 日的数据根本还没发生，模型完全失效。

**技术上如何杜绝**：在拼接样本时，严格遵守 **特征时间戳 ≤ 标签时间戳**，并用 Feast 的 Point-in-Time Join 自动保证每个标签只关联它发生之前的最新特征快照。

---

### 2. concat vs merge 的区别和风险
这两个都是拼接数据的操作，但本质不同，用错会直接导致时间泄漏或数据混乱。

| 操作 | 含义 | 典型用法 | 风险 |
|------|------|----------|------|
| **concat** | 按行或列简单堆叠，**不关心键值对齐** | 把两个相同结构的 DataFrame 纵向拼起来（增加行）或横向拼起来（增加列，但要求索引对齐） | 横向拼接时如果只靠位置（行索引）对齐，可能张冠李戴，把 A 用户的特征接到 B 用户的标签上 |
| **merge** | 基于一个或多个键（如 user_id）进行关联，类似 SQL JOIN | 将特征表与标签表按 `user_id` 和 `timestamp` 条件关联 | 1. 如果只有 `user_id` 而忽略时间条件，可能会关联到未来特征（泄漏）<br>2. 多对多合并可能产生笛卡尔积，让样本量爆炸，且混杂错误标签 |

**在样本构建中的典型错误**：
- **用 concat 构建样本**：比如你有一个特征 DataFrame 和一个标签 DataFrame，你图方便直接 `pd.concat([X, y], axis=1)`，但索引可能错位，导致 user A 的特征接到了 user B 的标签上，训练出来的模型完全错乱。
- **merge 时忘记时间约束**：`merged = pd.merge(features, labels, on='user_id')`，这会把同一个用户的所有特征和所有标签做笛卡尔积，一个标签可能对应多个时间点的特征，包括标签发生之后的特征，从而引入时间泄漏。

**正确做法**：在 merge 时显式加上时间条件 `features.timestamp <= labels.timestamp`，然后选择最接近的那个特征版本（用 `groupby` + `last` 或窗口函数）。

---

### 3. 完成了 `detect_time_leakage()` 函数
这个函数的核心作用是：**在训练前自动检查样本是否泄漏**。输入是拼接好的训练 DataFrame，包含特征时间列和标签时间列，输出是泄漏比例。

**实现逻辑**：
- 对于每一行样本，如果 `特征时间戳 > 标签时间戳`，就属于泄漏。
- 统计泄漏行数 / 总行数，给出警告。

**伪代码（Python）**：

```python
def detect_time_leakage(df, feature_ts_col='feature_timestamp', label_ts_col='label_timestamp'):
    leakage_mask = df[feature_ts_col] > df[label_ts_col]
    leak_count = leakage_mask.sum()
    total = len(df)
    leak_ratio = leak_count / total if total > 0 else 0
    if leak_ratio > 0:
        print(f"[ALERT] 时间泄漏比例: {leak_ratio:.2%}，共 {leak_count} 行!")
        # 可以抛出异常或强制中止训练
    else:
        print("✅ 无时间泄漏，通过检查。")
    return leak_ratio

```

在实际工程中，这个函数可以放在训练管道的**样本验证步骤**，作为数据质量保障的一环。如果泄漏比例 > 0，必须回退检查拼接逻辑。

---

### 4. 完成了电商推荐 PIT 样本构建
**PIT（Point-in-Time）样本构建** 的核心是：对每一个标签事件，都找到**该事件发生之前**的最新特征快照，构成一条训练样本。

**电商推荐场景**：
- 标签：用户对某个商品的点击（1）或未点击（0），标签时间戳就是曝光/点击的时间点。
- 特征：用户最近 7 天的购买次数、商品的价格、用户与商品的交互历史等。
- 任务：预测下一次展示时用户会不会点击。

**构建步骤**（手工实现，不依赖 Feast）：
1. 准备标签表 `labels`（user_id, item_id, label, label_ts）。
2. 准备特征表 `features`（user_id, item_id, 特征值..., feature_ts）。注意特征表可能有多条历史记录（例如每天更新的用户画像）。
3. 使用 merge 加时间条件：
   
```python
   merged = pd.merge_asof(
       labels.sort_values('label_ts'),
       features.sort_values('feature_ts'),
       by='user_id',          # 关联键
       left_on='label_ts',
       right_on='feature_ts',
       direction='backward',  # 只取 feature_ts <= label_ts 的记录
       allow_exact_matches=True
   )
   
```
   这里 `merge_asof` 会自动匹配每个标签时间之前最近的特征记录，完全避免泄漏。

4. 如果还有物品侧特征，同样按 item_id 和时间再做一次 asof join。

**最终得到的样本**：每一行都是“过去的特征 + 现在的标签”，模型学会的是从已知历史推断当前行为。

---

### 5. 理解了为什么 AUC(test)=0.99 反而可能是坏事
在真实业务场景中，AUC=0.99 几乎等同于**红灯信号**，它往往不是模型好，而是数据出错了。正常的风控模型 AUC 一般在 0.65~0.80 之间，推荐点击率模型 AUC 在 0.6~0.75 就很不错了。

**0.99 意味着什么？**  
模型能几乎完美地区分正负样本，这在存在大量不确定因素的真实人类行为预测中是不可能的，说明模型很可能**记住了某些可以直接推导出标签的作弊信息**。

**常见原因**：
1. **时间泄漏**（最可能）：特征里混入了标签之后的信息。比如预测“用户会否复购”，却把他复购后的浏览记录当特征，模型直接就“看到”未来动作。
2. **标签直接泄漏**：特征中包含了标签的衍生值。比如用“逾期金额”去预测“是否逾期”，或者用户 ID 直接和标签有强映射（如果训练集和测试集按 ID 随机分割，但某些 ID 是纯坏账用户，模型记住了 ID）。
3. **数据划分错误**：用随机分割而不是按时间分割，导致同一用户的未来行为出现在训练集和测试集中，造成“穿越”。
4. **测试集标签极不均衡且特征单一**：比如全是正样本，模型只要输出 1 就全对，这种 AUC 计算无意义。

**正确反应**：一旦看到 AUC=0.99，应该立刻**排查特征时间**、检查训练/测试是否按时间切分、确认是否有直接包含标签的列、以及进行时间泄漏检测。绝不能直接上线。

---

**总结**：这五点其实都围绕着一个核心——**训练数据的时序正确性**。从理解泄漏、样本构建到指标检验，每一步都是在保证“模型只能用过去预测未来”，这样上线后才不会翻车。

---

## 7. 请说说原始事件 vs 特征向量（20min）

> ID: `L007`

### 1.1 模型看不懂事件，只看懂数字


```
业务系统产生的是"事件流":
  user_000042 | page_view  | /mine  | 2026-07-01 23:45:39
  user_000042 | click      |        | 2026-07-01 18:14:58
  user_000042 | submit     | /mine  | 2026-07-01 23:45:39
  user_000042 | page_view  | /repay | 2026-07-01 18:23:45
  user_000042 | page_view  | /mine  | 2026-07-01 06:34:07
  ...（共 11 条）

模型需要的是"特征向量"（一行数字）:
  user_000042 | apply_cnt_7d=1 | night_ops_ratio=0.27 | page_view_7d=5 | error_7d=2 | ...

特征工程 = 把上面 11 行变成下面 1 行

```

---

---

## 8. 请讲讲特征工程 — 从事件流到特征向量的三种模式中的三种特征构造模式（1.5h）

> ID: `L008`

打开 `src/data/warehouse/dws_layer.py` 第 135-199 行 `_build_behavior_features()`，这是三种模式的完整实现。

### 模式 1：时间窗口 + COUNT WHERE


```python
# 第 162-173 行
in_7d = group['event_time'] >= ref_date - timedelta(days=7)
in_30d = group['event_time'] >= ref_date - timedelta(days=30)

apply_cnt_7d = (group[in_7d]['event_type'] == 'submit').sum()
page_view_7d = (group[in_7d]['event_type'] == 'page_view').sum()
input_7d = (group[in_7d]['event_type'] == 'input').sum()
error_7d = (group[in_7d]['event_type'] == 'error').sum()

```

**核心公式**：`COUNT(event_type = X) WHERE event_time IN [ref_date - N天, ref_date]`

**为什么用 `event_time` 而不是 `dt` 分区键？**


```
dt = 数据写入仓库的日期（可能会跨天延迟）
event_time = 事件实际发生的时间（业务真实时间）

场景：凌晨 01:30 的事件
  - dt 可能是当天（如果 ETL 在凌晨 3 点跑）
  - dt 也可能是第二天（如果 ETL 在半夜 12 点跑）
  - 但 event_time 永远是 "01:30" ← 这才是正确的时间语义

```

### 模式 2：比率衍生 — 用占比而不是绝对值


```python
# 第 182-188 行
night_hours = group_30d['event_time'].dt.hour.isin(
    [22, 23, 0, 1, 2, 3, 4, 5]
)
night_ops_ratio = night_hours.mean()  # ← 不是 sum()！

```

**为什么用 `mean()` 而不是 `sum()`？**


```
高频用户: 总共 100 次操作，其中 27 次在深夜 → sum=27, mean=0.27
低频用户: 总共 10 次操作，其中 2 次在深夜 → sum=2, mean=0.20

如果用 sum(次数):
  高频用户 → 27 → 看起来"高风险"
  低频用户 → 2 → 看起来"低风险"
  ❌ 错误！两者深夜占比差不多（27% vs 20%）

如果用 mean(占比):
  高频用户 → 0.27 → 风险中等
  低频用户 → 0.20 → 风险低
  ✅ 正确！占比消除了活跃度偏差

```

**类比其他业务**：

| 业务 | 错误的 sum | 正确的 mean |
|------|-----------|------------|
| 信贷 | 深夜操作次数 | 深夜操作占比 |
| 电商 | 加购次数 | 加购转化率 = 加购/浏览 |
| 客服 | 投诉次数 | 投诉率 = 投诉/总会话 |
| 游戏 | 充值次数 | 付费率 = 付费用户/活跃用户 |

### 模式 3：缺失值策略 — 填 0 而不是均值


```python
# 第 91-92 行
numeric_cols = wide_table.select_dtypes(include=[np.number]).columns
wide_table[numeric_cols] = wide_table[numeric_cols].fillna(0)

```

**为什么填 0 而不是均值？**


```
场景: 新用户，从未在 App 操作过
  行为特征全部为 NA

方案 A: fillna(均值)
  新用户 → 被赋予"平均用户"的行为特征
  问题: 新用户不应该像"平均用户"，他的风险是未知的

方案 B: fillna(0)
  新用户 → 行为特征全 0 → "无行为信息"
  优势: 0 明确表示"没有数据"，模型能学到"0 = 新用户 = 不同模式"

方案 C: fillna(-1)
  新用户 → 行为特征全 -1 → 在分布中形成一个"尖峰"
  优势: 模型更容易区分"新用户(全-1)"和"低频用户(接近0但>0)"
  但 -1 是虚构值，可能干扰模型 → 使用时需要实验验证

```

---

---

## 9. 请讲讲特征工程 — 从事件流到特征向量的三种模式中的动手练习（1.5h）

> ID: `L009`

### 练习 1：为电商写特征工程函数（1h）


```python
import pandas as pd
from datetime import datetime, timedelta

# 模拟电商行为数据
events = pd.DataFrame({
    'user_id': ['u1', 'u1', 'u1', 'u1', 'u1',
                'u2', 'u2',
                'u3', 'u3', 'u3', 'u3'],
    'event_type': [
        'view_item', 'add_cart', 'view_item', 'add_cart', 'purchase',  # u1: 浏览→加购→浏览→加购→购买
        'view_item', 'view_item',                                       # u2: 只浏览不买
        'view_item', 'add_cart', 'add_cart', 'search',                  # u3: 浏览→加购→加购→搜索
    ],
    'category': ['电子', '电子', '服装', '服装', '服装',
                 '电子', '电子',
                 '图书', '图书', '图书', '图书'],
    'event_time': pd.to_datetime([
        '2026-07-01 09:00', '2026-07-01 09:05', '2026-07-01 10:00',
        '2026-07-01 10:05', '2026-07-01 10:10',
        '2026-07-01 14:00', '2026-07-01 14:05',
        '2026-06-25 08:00', '2026-06-25 08:05', '2026-06-25 08:10',
        '2026-07-01 16:00',
    ]),
})

def build_ecommerce_behavior_features(events, ref_date):
    """
    从电商行为事件 → 用户行为特征。
    """
    ref = datetime.strptime(ref_date, '%Y-%m-%d')
    events['event_time'] = pd.to_datetime(events['event_time'])

    result = []
    for user_id, group in events.groupby('user_id'):
        in_7d = group['event_time'] >= ref - timedelta(days=7)
        g7 = group[in_7d]

        # ★ 参考答案
        row = {
            'user_id': user_id,
            # 模式1: COUNT WHERE
            'view_cnt_7d':    (g7['event_type'] == 'view_item').sum(),
            'cart_cnt_7d':    (g7['event_type'] == 'add_cart').sum(),
            'purchase_cnt_7d':(g7['event_type'] == 'purchase').sum(),
            'search_cnt_7d':  (g7['event_type'] == 'search').sum(),
            # 模式2: 比率衍生 (注意防除零)
            'cart_conversion_7d': ((g7['event_type'] == 'add_cart').sum()
                                    / max((g7['event_type'] == 'view_item').sum(), 1)),
            'purchase_conversion_7d': ((g7['event_type'] == 'purchase').sum()
                                        / max((g7['event_type'] == 'add_cart').sum(), 1)),
            # 模式3: 多样性 + 均值
            'category_diversity_7d': g7['category'].nunique(),
            'avg_daily_events_7d': round(len(g7) / 7, 2),
        }
        result.append(row)

    return pd.DataFrame(result)

result = build_ecommerce_behavior_features(events, '2026-07-02')
print(result)
# 预期:
# u1: view=2, cart=2, purchase=1, cart_conv=1.0, purchase_conv=0.5
# u2: view=2, cart=0, purchase=0, cart_conv=0.0, purchase_conv=0.0
# u3: view=1, cart=2, purchase=0, cart_conv=2.0, purchase_conv=0.0

```

### 练习 2：验证比率衍生优于 sum（30min）


```python
# ★ 参考答案
import numpy as np

# 构造两个用户: 总量不同但模式相同
np.random.seed(42)
high_freq_events = np.random.choice(['view', 'buy'], size=200,
                                     p=[0.8, 0.2])  # 200 次, 购买率 20%
low_freq_events  = np.random.choice(['view', 'buy'], size=20,
                                     p=[0.8, 0.2])   # 20 次, 购买率 20%

high_sum = (high_freq_events == 'buy').sum()  # 约 40
low_sum  = (low_freq_events == 'buy').sum()   # 约 4
high_rate = (high_freq_events == 'buy').mean()  # 0.20
low_rate  = (low_freq_events == 'buy').mean()   # 0.20

print(f"高频用户: sum={high_sum}, rate={high_rate:.2f}")
print(f"低频用户: sum={low_sum}, rate={low_rate:.2f}")
print()
print(f"按 sum 排序: 高频用户({high_sum}) > 低频用户({low_sum})")
print("  → 误判：低频用户被标记为"低购买意愿"")
print(f"按 rate 排序: 高频用户({high_rate:.2f}) = 低频用户({low_rate:.2f})")
print("  → 正确：购买模式相同，购买意愿相同")
print()
print("结论：sum 会受到"用户活跃度"的干扰，活跃的用户一切行为都多。")
print("rate（占比）消除了活跃度偏差，只反映行为模式本身。")
print("在信贷场景中：night_ops_ratio 用 mean() 而非 sum() 也是同样原因。")

```

---

---

## 10. 请讲讲特征工程 — 从事件流到特征向量的三种模式中的跨业务思考（30min）

> ID: `L010`

用三种模式分析以下业务的特征设计：

**游戏行业 — "玩家付费预测"**：


```
事件: 登录、副本、充值、社交、PVP

模式1(COUNT WHERE): login_days_7d, dungeon_cnt_7d, recharge_cnt_7d
模式2(比率衍生): pay_rate_30d = 付费天数/登录天数, social_ratio = 好友互动/总操作
模式3(缺失值): 新玩家(第1天) → fillna(0) → 所有行为=0 → 模型知道"这是新玩家"

```

**打车行业 — "司机流失预测"**：


```
事件: 接单、取消、完成、评价

模式1: online_hours_7d, order_cnt_7d, cancel_cnt_7d
模式2: cancel_rate = 取消/接单, bad_review_rate = 差评/完成
模式3: 新司机 → fillna(0) → 无历史数据 → 保守评估

```

---

---

## 11. 请讲讲特征工程 — 从事件流到特征向量的三种模式中的今日要点

> ID: `L011`

```
特征工程的三种模式:

模式1 — COUNT WHERE:
  公式: SUM(event_type = X) WHERE event_time IN [ref-N, ref]
  关键: 用 event_time 而非 dt 分区键

模式2 — 比率衍生:
  公式: mean(condition) 或 ratio = A类的SUM / B类的SUM
  关键: 消除用户活跃度偏差

模式3 — 缺失策略:
  公式: fillna(0) 而非 fillna(均值)
  关键: "无数据"本身就是信号

```

---

---

## 12. 为什么不能只用模型？（20min）

> ID: `L012`

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

---

## 13. 请举例说明核心代码：`inference_pipeline.py` 的 execute()（1h）如何实现？

> ID: `L013`

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

---

## 14. 请讲讲规则 + 模型融合 — 四层决策架构中的动手练习（1.5h）

> ID: `L014`

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

---

## 15. 请讲讲规则 + 模型融合 — 四层决策架构中的跨业务思考（30min）

> ID: `L015`

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

---

## 16. 请讲讲模型评估 + 线上监控 + 自动熔断中的模型不是训完就结束了（20min）

> ID: `L016`

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

---

## 17. 请讲讲模型评估 + 线上监控 + 自动熔断中的上线前评估：四个核心指标（1h）

> ID: `L017`

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

---

## 18. 请讲讲模型评估 + 线上监控 + 自动熔断中的熔断器：不让坏模型继续害人（40min）

> ID: `L018`

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

---

## 19. 请讲讲模型评估 + 线上监控 + 自动熔断中的动手练习（1.5h）

> ID: `L019`

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

---

## 20. 请举例说明三层降级代码精读（1h）如何实现？

> ID: `L020`

打开 `src/decision_engine/inference_pipeline.py` 第 310-350 行：


```python
async def _fetch_features_with_fallback(self, request):
    t0 = time.perf_counter()

    # ═══════════════════════════════════════════
    # 路径1: 在线特征 — 50ms 超时
    #
    # 为什么是 50ms？
    # 整个推理 P99 < 300ms。特征获取只是其中一环。
    # 50ms = 1/6 预算，留给规则(5ms)+模型(10ms)+序列化(10ms)
    #         +网络(20ms)+余量(205ms)。
    # 设太大(100ms)→ 挤压模型推理时间
    # 设太小(20ms)→ 正常请求也超时 → 频繁降级
    # ═══════════════════════════════════════════
    try:
        snapshot = await asyncio.wait_for(
            self.feature_service.get_online_features(request.user_id),
            timeout=0.050
        )
        return snapshot
    except asyncio.TimeoutError:
        pass  # → 降级

    # ═══════════════════════════════════════════
    # 路径2: 缓存特征 — TTL 5分钟
    #
    # 为什么缓存不是默认路径？
    # 默认走在线（最新数据），在线挂了走缓存（可用但可能过时）。
    # 缓存是"安全网"，不是"主路"。
    # ═══════════════════════════════════════════
    cached = self.feature_service.get_cached_features(request.user_id)
    if cached:
        snapshot = FeatureSnapshot(user_id=request.user_id)
        snapshot.features = cached
        snapshot.degraded_features = list(cached.keys())  # ← 标记降级
        return snapshot

    # ═══════════════════════════════════════════
    # 路径3: 默认值 — 最保守策略
    #
    # 为什么默认值偏保守（偏高风险）？
    # 不知道用户什么样 → 宁可误杀，不可放过
    #
    # night_ops_ratio 默认 0.5: 偏高（正常 0.1-0.3）
    # on_time_rate 默认 0.5: 偏低（正常 0.8-1.0）
    # monthly_income 默认 5000: 中等偏低
    #
    # 为什么不是 0？填 0 意味着"无风险"→ 会放行实际高风险用户
    # 为什么不是极端值？全拒绝会影响业务量
    # ═══════════════════════════════════════════
    snapshot = FeatureSnapshot(user_id=request.user_id)
    snapshot.features = DegradationPolicy.get_all_defaults()
    snapshot.degraded_features = list(snapshot.features.keys())
    return snapshot

```

### 2.1 降级默认值的选择——这是 AI 工程师的决策

打开 `src/decision_engine/degradation.py`：


```python
class DegradationPolicy:
    DEFAULTS = {
        # "越高越危险"的特征 → 默认偏高（保守）
        'night_ops_ratio_30d': 0.5,    # 正常 0.1-0.3
        'overdue_cnt_hist':    1.0,    # 正常 0
        'apply_cnt_7d':        2.0,    # 正常 0-1

        # "越低越危险"的特征 → 默认偏低（保守）
        'on_time_rate':        0.5,    # 正常 0.8-1.0
        'monthly_income':      5000,   # 正常 5000-20000
    }

```

**为什么 `on_time_rate` 默认 0.5 而不是 0 或 1？**


```
0.0 → "绝对坏" → 所有降级请求都被拒 → 业务量骤降
1.0 → "绝对好" → 所有降级请求都被通过 → 放行了高风险用户
0.5 → 中间值 → 评分大约 500 分 → MANUAL_REVIEW → 人工兜底

```

---

---

## 21. 请讲讲生产级降级 + 容错设计中的动手练习（1.5h）

> ID: `L021`

### 练习 1：实现三层降级（45min）


```python
import asyncio
import random

# 模拟的特征服务：有时正常、有时慢、有时直接抛异常
class MockFeatureService:
    async def get_online_features(self, user_id):
        delay = random.choice([0.01, 0.02, 0.06, 0.2])  # 最后一个超时
        await asyncio.sleep(delay)
        if random.random() < 0.1:  # 10% 概率直接崩溃
            raise ConnectionError("Redis 挂了")
        return {"f1": 1.0, "f2": 2.0}

    def get_cached_features(self, user_id):
        if random.random() > 0.3:  # 70% 概率命中缓存
            return {"f1": 0.9, "f2": 1.8}
        return None  # 缓存过期

DEFAULTS = {"f1": 0.5, "f2": 0.5}

async def fetch_features_with_fallback(user_id):
    """
    要求实现三层降级，和项目中的代码结构一致。
    """
    # ★ 参考答案
    t0 = time.perf_counter()

    try:
        # 路径1: 在线 — 50ms 超时
        features = await asyncio.wait_for(
            service.get_online_features(user_id), timeout=0.050
        )
        return {"features": features, "source": "online", "degraded": False}
    except (asyncio.TimeoutError, ConnectionError):
        pass  # 降级下一层

    # 路径2: 缓存
    cached = service.get_cached_features(user_id)
    if cached:
        return {"features": cached, "source": "cache",
                "degraded": True, "degraded_features": list(cached.keys())}

    # 路径3: 默认值（最保守）
    return {"features": DEFAULTS, "source": "defaults",
            "degraded": True, "degraded_features": list(DEFAULTS.keys())}


# 测试
async def test():
    for i in range(10):
        result = await fetch_features_with_fallback(f"user_{i}")
        print(f"user_{i}: source={result['source']:10s} "
              f"features={result['features']}")

asyncio.run(test())

```

### 练习 2：设计搜索系统的降级路径（30min）


```
搜索系统的四层降级:
  路径1: 语义搜索(深度学习) — 80ms 超时
  路径2: 关键词匹配(ES) — 50ms 超时
  路径3: 热门结果缓存 — 不超时
  路径4: 空结果 + "请优化搜索词"

要求:
  1. 写出每层超时时间的理由
  2. 路径4 返回空结果 → 用户体验很差 → 如何缓解？

```

---

---

## 22. 请讲讲生产级降级 + 容错设计中的跨业务思考（30min）

> ID: `L022`

```
语音助手:
  路径1: GPT-4o (2s超时) → 最智能
  路径2: 本地小模型 Whisper+LLaMA (500ms) → 还行
  路径3: 预设回复列表 → "请稍后再试"

自动驾驶:
  路径1: 多传感器融合 → 最优
  路径2: 纯视觉 → 降级
  路径3: 安全停车 → 绝对兜底
  ★ 注意: 自动驾驶不能"降级到默认值继续开"
          降级=停车，不是"保守策略"

```

---

---

## 23. 请讲讲★ 参考答案中的NL2SQL：让业务人员用自然语言查数仓（1.5h）

> ID: `L023`

### 1.1 四步骤架构


```
用户: "上周各渠道通过率是多少？"
  │
  ▼
Step 1: Schema Context 注入
  把表结构（表名、列名、COMMENT）作为 System Prompt
  → "表 ads_model_monitor_daily, 列 channel STRING -- 渠道,
     approval_rate DOUBLE -- 通过率, dt STRING -- 日期"

  │
  ▼
Step 2: LLM 生成 SQL (temperature=0.0)
  SELECT channel, AVG(approval_rate) as rate
  FROM ads.ads_model_monitor_daily
  WHERE dt >= '2026-06-30' AND dt <= '2026-07-06'
  GROUP BY channel ORDER BY rate DESC;

  │
  ▼
Step 3: 安全校验（永远不信任 LLM 的输出）
  ✓ 无 DROP/DELETE/INSERT/UPDATE
  ✓ 有 dt 分区过滤（防全表扫描）
  ✓ 是 SELECT 语句

  │
  ▼
Step 4: 执行 → 返回
  APP_IOS: 72%, APP_ANDROID: 65%, H5: 58%

```

### 1.2 为什么数仓工程师天然适合做 NL2SQL

**NL2SQL 的瓶颈不是 LLM 生成 SQL 的能力，而是 Schema Context 的质量。**


```
LLM 能生成:
  SELECT AVG(approval_rate) FROM ads_model_monitor_daily WHERE ...

但它不知道:
  - approval_rate 是"通过率" ← 你的 COMMENT 告诉它的
  - "上周"需要翻译为 dt >= '2026-06-30' AND dt <= '2026-07-06'
  - "渠道"是 channel 列
  - 不能不带 dt 过滤（会全表扫描 10 亿行）

没有好的 COMMENT → LLM 猜错列 → SQL 返回错误结果

```

**COMMENT 是 NL2SQL 的命脉**。你之前在 DDL 里写的每一行 COMMENT，现在都变成了 LLM 的上下文。

### 1.3 核心代码模式


```python
class NL2SQLGenerator:
    def __init__(self, schema_registry):
        self.registry = schema_registry

    def _build_system_prompt(self):
        """从 SchemaRegistry 动态构造 Prompt — COMMENT 在这里发挥作用"""
        tables = self.registry.list_tables()
        parts = []
        for t in tables:
            cols = [f"  {c.name} {c.type} -- {c.description}" for c in t.columns]
            parts.append(f"表 {t.layer}.{t.table_name}:\n" + "\n".join(cols))
        return f"可用表:\n{chr(10).join(parts)}\n只生成SELECT。用dt过滤。"

    def validate_sql(self, sql):
        """三道安全校验 — 永远不信任 LLM"""
        sql_up = sql.upper()
        # 1. 禁危险关键字
        for kw in ['DROP','DELETE','INSERT','UPDATE']:
            if kw in sql_up: return False, f"禁止: {kw}"
        # 2. 必须有分区过滤
        if 'DT' not in sql_up:
            return False, "必须包含 dt 分区过滤"
        # 3. 必须是 SELECT
        if not sql_up.startswith('SELECT'):
            return False, "只允许 SELECT"
        return True, "OK"

```

---

---

## 24. 请讲讲★ 参考答案中的RAG：让 LLM 基于项目文档回答（1h）

> ID: `L024`

### 2.1 RAG 的知识库 = 你的项目文档


```
问题: "night_ops_ratio_30d 超过多少算异常？"

RAG 检索:
  → config/schemas/dws_wide_table.yaml: "★ 深夜操作占比(22-05时)。>60%→高度可疑"
  → config/rules/credit_policy.yaml: "night_ops_ratio_30d > 0.6 → MANUAL_REVIEW"
  → 01_system_architecture.md: "风控强特征，欺诈团伙常在夜间批量操作"

LLM 综合:
  "night_ops_ratio_30d 超过 60% 触发人工审核(RC_BH001)。
   正常范围 < 30%。> 60% 是高度可疑信号，因为欺诈团伙常在夜间操作。"

```

### 2.2 切片策略（比向量模型更重要）


```
错误做法: 每 500 字切一刀
  文档: "特征分为三类: 申请画像、行为衍生、还款表现。申请画像包括..."
  一刀切在 "申请画像包括" 后面 → 丢失了具体特征列表

正确做法: 按语义边界切
  YAML: 每个顶级 key 一个 chunk（一个表定义 = 一个片段）
  SQL:  每个 CREATE TABLE 一个 chunk（一张表的完整 DDL）
  MD:   每个 ## 标题一个 chunk（一个章节一个片段）

为什么？检索时返回的是"完整片段"，不是"半句话"

```

---

---

## 25. 请讲讲★ 参考答案中的LangGraph：多步骤 AI 工作流（40min）

> ID: `L025`

### 3.1 信贷审批的状态机


```
rule_check ──REJECT──→ rejection_letter(LLM) ──→ END
    │
    └──PASS──→ model_score ──APPROVE──→ disburse ──→ END
                    │
                    ├──REJECT──→ rejection_letter(LLM)
                    └──MANUAL_REVIEW──→ request_docs(LLM) ──→ END
                                            ↑
                                    用户上传材料后恢复

```

### 3.2 为什么用 LangGraph 而不是手写 if-else


```
手写 if-else 的问题:
  改流程 = 改代码 = 改 if-else 分支 = 容易出错
  异步操作(等用户上传材料) → 状态需要自己持久化
  流程可视化 → 要另外画图

LangGraph:
  加一个节点 = graph.add_node("new_step", new_step_fn)
  异步状态 = checkpointer 自动处理
  可视化 = graph.get_graph().draw_mermaid_png()

```

---

---

## 26. 请讲讲★ 参考答案中的动手练习（1.5h）

> ID: `L026`

### 练习 1：实现 NL2SQL 的 validate_sql()（30min）


```python
# ★ 参考答案
FORBIDDEN_KW = ['DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE',
                'ALTER', 'CREATE', 'GRANT', 'REVOKE']

def validate_sql(sql: str) -> tuple[bool, str]:
    sql_up = sql.upper().strip()

    # 校验1: 禁止危险关键字
    for kw in FORBIDDEN_KW:
        if kw in sql_up:
            return False, f"禁止关键字: {kw}"

    # 校验2: 必须是 SELECT
    if not sql_up.startswith('SELECT'):
        return False, "只允许 SELECT"

    # 校验3: 必须有分区过滤（dt）
    if 'DT' not in sql_up:
        return False, "必须包含 dt 分区过滤（防全表扫描）"

    return True, "OK"


# 5 个测试用例
tests = [
    ("SELECT * FROM t WHERE dt='2026-07-01'", True, "正常查询"),
    ("DROP TABLE t", False, "危险关键字"),
    ("SELECT * FROM t", False, "无 dt 分区"),
    ("  select channel, avg(rate) from t where dt > '2026-07-01'", True, "小写SELECT"),
    ("DELETE FROM t WHERE dt='2026-07-01'", False, "DELETE 应拦截"),
]
for sql, expected, desc in tests:
    ok, msg = validate_sql(sql)
    assert ok == expected, f"[{desc}] {sql} → {msg}"
print("✅ 所有测试用例通过")

```

### 练习 2：设计 RAG 的切片策略（30min）


```
★ 参考答案:

| 文件 | 切片策略 | chunk 数 | metadata |
|------|---------|:--------:|---------|
| ods_tables.yaml | 按顶级 key 切（ods_application/ods_user_behavior/ods_repayment 各一段） | 3 | source, table_name |
| dws_wide_table.yaml | 按 category 切（profile/behavior/repayment 三大类，每类一个 chunk） | 3 | source, category |
| credit_policy.yaml | 按 rule group 切（hard_reject/risk_assessment/credit_limit 各一段） | 3 | source, group_name |
| 流转过程.md | 按 ## 标题切（每站一个 chunk） | 5 | source, chapter |

YAML 按顶级 key 切的原因:
  → 每个 key 是一段自包含的定义（一张表、一条规则）
  → key 本身是 chunk 的"标题"，LLM 能理解这段在说什么

MD 按 ## 标题切的原因:
  → 文档作者的标题层级 = 自然语义边界
  → 按 # 切太粗（全文），按 ### 切太碎（可能不完整）
  → ## 是"章节"级别，刚好自包含

chunk metadata 必须包含 source 的原因:
  → LLM 引用时可以说"根据 ods_tables.yaml 中的描述..."
  → 来源可追溯 = 可信度可验证

```

### 练习 3：画出审批工作流的状态图（20min）


```
★ 参考答案（ASCII 状态图）:

               ┌─────────────────────────┐
               │    rule_check (普通)      │
               │    规则引擎检查           │
               └────────┬───────────────┘
                        │
               ┌────────┴────────┐
               │ 条件: 是否硬拒绝? │
               └────────┬────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    REJECT            PASS             (通往下一节点)
        │               │
        ▼               ▼
┌─────────────────┐  ┌─────────────────────────┐
│ rejection_letter│  │    model_score (普通)    │
│ (LLM 节点)       │  │    XGBoost 模型推理      │
│ 生成拒绝函       │  └────────┬────────────────┘
└────────┬────────┘           │
         │            ┌────────┴────────┐
         │            │ 条件: 评分判定?  │
         │            └────────┬────────┘
         │                     │
         │        ┌────────────┼────────────┐
         │        │            │            │
         │    APPROVE      MANUAL      REJECT
         │        │         REVIEW         │
         │        ▼            │            │
         │  ┌──────────┐       │            │
         │  │ disburse  │       │            │
         │  │ (普通)    │       ▼            │
         │  │ 放款     │  ┌──────────────┐  │
         │  └──────────┘  │ request_docs  │  │
         │                │ (LLM 节点)     │──┤
         │                │ 生成补充材料清单│  │
         │                └──────────────┘  │
         └──────────────────────────────────┘
                              │
                              ▼
                           ┌──────┐
                           │ END  │
                           └──────┘

LLM 节点 vs 普通函数节点的区别:
  LLM 节点: 需要调用大模型（如生成拒绝函、生成材料清单）
    特点: 有延迟、不稳定（可能输出不符合格式）
    应对: temperature=0 保证确定性、失败后重试

  普通节点: 纯计算/规则（如规则引擎、模型推理）
    特点: 低延迟、确定性的
    优势: 没有 LLM 的"幻觉"风险和延迟问题

```

---

---

## 27. 请讲讲可解释性 + 综合项目：智能客服质检系统中的SHAP 可解释性（1h）

> ID: `L027`

### 1.1 为什么需要 SHAP？


```
用户问: "为什么拒绝我的贷款？"

不好的回答: "模型评分低于阈值"  ← 等于没说
好的回答: "主要原因——历史逾期2次(影响最大)，近7天申请3次(次要)，深夜操作占比40%(偏高等)"
           ← SHAP 值告诉你的

```

### 1.2 项目中的 SHAP 实现

打开 `src/models/trainer.py` 的 `ModelWrapper.explain()`：


```python
class ModelWrapper:
    def explain(self, feature_vector, top_n=10) -> dict:
        """
        返回每个特征对"这个用户"的 SHAP 贡献值。

        和 feature_importance 的区别:
        - feature_importance: 全局性——"哪个特征整体最重要"
        - SHAP:              局部性——"对这个用户，哪个特征贡献最大"

        SHAP 值含义:
        +0.15 → 推高违约概率 0.15 → 这个特征增加了风险
        -0.10 → 拉低违约概率 0.10 → 这个特征降低了风险
        """
        shap_vals = self._shap.shap_values(dmatrix)[0]
        return dict(sorted(
            zip(self.feature_names, shap_vals),
            key=lambda x: abs(x[1]), reverse=True  # 按贡献绝对值排序
        )[:top_n])

```

### 1.3 RuleResult 的 reason_code 体系


```python
# 规则引擎的输出——确定性原因
RuleResult(
    rule_id="MULTI_HEAD_SPIKE",
    decision=Decision.MANUAL_REVIEW,
    reason_code="RC_MH001",         # ← 唯一编码
    reason_desc="近7天多头借贷次数>=5"  # ← 人类可读
)

# SHAP——概率性贡献
{"overdue_cnt_hist": +0.15, "night_ops_ratio": +0.08}

# 给用户看 reason_desc（"多头借贷次数过多"）
# 给分析师看 SHAP（"overdue_cnt_hist 贡献 +0.15"）
# 两者互补，不是替代

```

---

---

## 28. 请讲讲可解释性 + 综合项目：智能客服质检系统中的综合项目：智能客服质检系统（3h）

> ID: `L028`

### 2.1 业务理解


```
业务: 智能客服质检系统

需求: 自动评估客服对话质量，减少人工抽检工作量

数据源:
  - 对话记录(文本): "用户: 我的订单怎么还没到？ 客服: 我帮您查一下..."
  - 客服信息: 工龄、技能组、历史质检分数
  - 用户评价: 1-5 星、评价标签（态度好/解决问题/态度差）
  - 订单信息: 订单状态、物流状态、金额

质检维度:
  - 态度: 是否礼貌、是否主动道歉
  - 准确性: 回答是否正确、是否遗漏关键信息
  - 效率: 对话轮次、解决时长
  - 合规: 是否说了违禁词（如承诺赔偿金额）

```

### 2.2 任务清单

**任务 1: 特征设计（30min）**

设计至少 10 个特征，分为三类：


```python
# 对话文本特征（NLP 提取）:
f1_conversation_turns: int       # 对话轮次 → 越高越差?
f2_avg_reply_time_sec: float     # 平均回复间隔
f3_customer_anger_score: float   # 用户情绪愤怒程度 (NLP)
f4_has_apology: bool             # 客服是否道歉
f5_keyword_compliance_hits: int  # 违禁词命中次数

# 客服画像特征:
f6_tenure_days: int             # 工龄
f7_historical_quality_score: float # 历史质检均分

# 上下文特征:
f8_order_complexity: str         # 订单状态(退款/换货/查询 → 难度不同)
f9_conversation_time_hour: int   # 对话时间（深夜→客服可能疲劳）
f10_user_vip_level: int          # 用户等级（VIP → 更难处理）

```

**任务 2: PIT 样本构建（20min)**


```python
# 质检的"时间泄漏"风险:
# 特征: 对话结束时的所有信息（包括用户评价！）
# 标签: 质检是否合格
# 如果特征里包含了用户评价 → 模型学会了"差评=不合格"→ 毫无意义

# 正确做法: 特征只用对话结束时的客观信息（不含用户评价）
# 标签用后续的专家抽检结果

```

**任务 3: 规则+模型融合（30min）**


```
Layer 1 — 合规红线:
  说了违禁词 → 直接不合格（不需要跑模型）
  举例: "我保证赔偿"（客服不能承诺赔偿金额）

Layer 2 — NLP 模型评分:
  BERT Fine-tune 对对话文本打分 [0, 1]

Layer 3 — 融合:
  新客服(工龄<30天) + 模型分 0.4-0.6 → 人工复核(新人保护)
  老客服 + 模型分 0.4 → 不合格(对老人不宽容)

Layer 4 — 策略:
  不合格 → 通知主管 + 扣绩效 + 培训提醒
  人工复核 → 进入质检员队列

```

**任务 4: 监控+熔断（15min）**


```
质检模型监控指标:
  - 不合格率日环比 > 50% → 告警（可能是模型偏差或客服整体质量崩溃）
  - 人工复核率 > 30% → 模型区分力不足
  - 平均评分日环比 > 0.2 → 分布漂移

熔断: 不合格率突增 80% → 暂停自动质检，全部转人工

```

**任务 5: LLM 应用设计（30min）**


```
NL2SQL: 运营主管问"本周哪个客服的投诉率最高？"
  → 查询 ads_customer_service_daily 表

RAG: 客服问"用户说货没到，我应该怎么处理？"
  → 知识库: 客服FAQ + 退换货政策 + 物流异常SOP
  → 检索最相关的处理流程
  → 生成建议话术

LangGraph: 申诉工作流
  客服被扣绩效 → 提交申诉 → 主管审核 → AI 辅助判责(LLM分析对话记录)
  → 判定: 维持/撤销

```

**任务 6: 可解释性（15min）**


```
客服: "为什么我的对话被判不合格？"

系统输出:
  评分: 0.32/1.0 → 不合格

  SHAP 主要贡献:
  1. keyword_compliance_hits=3 → +0.18（说了 3 个违规词: "保证""绝对""最"）
  2. customer_anger_score=0.78 → +0.12（用户情绪非常愤怒）
  3. conversation_turns=25 → +0.08（对话轮次过长）
  4. has_apology=False → +0.05（没有道歉）
  5. historical_quality_score=0.85 → -0.06（历史表现良好，拉低了不合格概率）

```

---

---

## 29. 请讲讲可解释性 + 综合项目：智能客服质检系统中的自评表（30min）

> ID: `L029`

| 能力 | Day 1 自评 | Day 7 自评 | 提升 | 面试怎么说 |
|------|----------|----------|------|-----------|
| PIT 样本构建 | /5 | /5 | | "设计过严格防时间泄漏的样本生成" |
| 特征工程 | /5 | /5 | | "能对任意事件日志提取预测特征" |
| 规则+模型融合 | /5 | /5 | | "设计过四层决策架构" |
| 评估+监控+熔断 | /5 | /5 | | "搭建过完整 MLOps 闭环" |
| 降级容错 | /5 | /5 | | "设计过多层降级路径，永不停服" |
| LLM 应用 | /5 | /5 | | "NL2SQL+RAG+LangGraph 全链路" |
| 可解释性+合规 | /5 | /5 | | "SHAP+reason_code 双轨追溯" |

---

---

## 30. 请讲讲可解释性 + 综合项目：智能客服质检系统中的一周回顾

> ID: `L030`

两个 7 天计划到此结束。回顾一下你完成的所有产出物：


```
数仓工程师 7 天产出:
  Day 1: 电商 ODS 定义 + DDL
  Day 2: 电商清洗函数 + 扣分权重设计
  Day 3: 电商消费画像宽表 + 聚合函数选择
  Day 4: SchemaRegistry.validate_dataframe() + 血缘图
  Day 5: 电商脱敏策略 + 生产级 DDL
  Day 6: 分区策略 + 广告投放数据产品
  Day 7: ★ 在线教育平台完整数仓

AI 应用工程师 7 天产出:
  Day 1: PIT 样本构建 + 时间泄漏检测器
  Day 2: 电商行为特征工程 + ratio vs sum 分析
  Day 3: 四个版本的决策融合 + 内容审核分层
  Day 4: 手写 KS/PSI + 推荐系统监控
  Day 5: 三层降级代码 + 搜索系统降级
  Day 6: validate_sql() + RAG 切片策略 + LangGraph 状态图
  Day 7: ★ 智能客服质检系统完整 AI 应用

```

这些产出物就是你面试时可以说的"项目经验"——不只是"我做过信贷风控"，而是"我能把信贷风控中的方法论应用到任何业务"。

---

