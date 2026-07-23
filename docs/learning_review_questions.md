# 学习复习计划

> 共 139 题 | 更新: 2026-07-23
> 数据来源: interview/learning/ 目录

---

### L001
**分类：** AI应用开发
**题目：** 请举例说明一个让你记住一辈子的例子（20min）如何实现？
**参考答案：** ### 1.1 完美的离线模型，归零的线上效果


```text
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

```text
### 1.2 什么是时间泄漏


```text
时间泄漏 = 用"今天之后的信息"预测"今天的结果"

正确做法:
  X(T时刻的特征) → 模型 → 预测 y(T+N时刻的结果)

时间泄漏（错误）:
  X(T+N时刻的特征) → 模型 → 预测 y(T时刻的结果)
  或
  X(T时刻的特征中混入了T+N的信息) → 模型 → 预测 y(T+N时刻的结果)

```text
**在信贷项目中**：


```text
特征快照时间 = 2026-07-01（申请日）
标签观察时间 = 2026-08-01（30天后是否逾期）

✅ 正确的样本: X(07-01的特征) → y(08-01的逾期标签)
❌ 时间泄漏:    X(08-01的特征) → y(08-01的逾期标签)
               （用还款结果预测逾期，模型学会了"已经还了=不会逾期"）

```text

---

---

---

### L002
**分类：** AI应用开发
**题目：** 请举例说明从代码看 PIT 正确性（1h）如何实现？
**参考答案：** ### 2.1 阅读项目核心代码

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

```text
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

```text
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

```text

---

---

---

### L003
**分类：** AI应用开发
**题目：** 请讲讲PIT 样本构建 — 时间泄漏是 AI 工程师的第一课中的动手练习（1.5h）
**参考答案：** ### 练习 1：写时间泄漏检测器（30min）


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

```text
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

```text
### 练习 3：时间泄漏会怎样？（15min）

运行项目中的模型训练，观察时间泄漏的效果：


```bash
cd credit_risk_control_system

# 先看"正常"的模型（数据是随机生成的，所以效果差——这是预期的）
python3 scripts/train_model.py --from-warehouse --n-samples 2000
# 观察: AUC(train) ≈ 0.99, AUC(test) ≈ 0.47 → 严重过拟合随机噪声

# 思考: 如果 AUC(test) = 0.95（非常高），反而是坏事！
# 说明可能存在时间泄漏，模型看到了不该看的信息。

```text

---

---

---

### L004
**分类：** AI应用开发
**题目：** 请讲讲PIT 样本构建 — 时间泄漏是 AI 工程师的第一课中的跨业务思考（30min）
**参考答案：** ### 场景 1：网约车 "ETA 预测"


```text
模型: 预测"订单被接单后到乘客上车的等待时间"

特征: 接单时刻的司机位置、路况、天气
标签: 实际等待时间

问题: 如果特征里包含了"司机接单后的 GPS 轨迹"，有什么问题？
答案: 模型看到了"司机正在驶向乘客"的事实 → 它不需要预测路况，
      直接看"司机到哪了"就行 → 这和"用还款结果预测逾期"是一回事。

```text
### 场景 2：医疗 "再入院预测"


```text
模型: 预测"患者出院后 30 天内会不会再次入院"

特征: 出院时的诊断、用药、生命体征
标签: 30 天内是否再次入院

问题: 如果特征里包含了"出院后的门诊记录"，有什么问题？
答案: 模型看到"患者出院后频繁复诊"→ 预测会再入院。
      但出院时你并不知道患者会不会去复诊！
      这是典型的"用未来信息预测未来结果"。

```text

---

---

---

### L005
**分类：** AI应用开发
**题目：** 请讲讲PIT 样本构建 — 时间泄漏是 AI 工程师的第一课中的今日要点
**参考答案：** ```text
核心公式:
  ✅ 正确的训练样本: X(T) → y(T+N)
  ❌ 时间泄漏:       X(T+N) → y(T+N)

三个铁律:
  1. merge on key, never concat by index
  2. 显式过滤 feature_time < label_time（双重保险）
  3. AUC(test) 异常高（>0.95）→ 先怀疑时间泄漏，再高兴

```text

---

---

---

### L006
**分类：** AI应用开发
**题目：** 请讲讲PIT 样本构建 — 时间泄漏是 AI 工程师的第一课中的检查清单
**参考答案：** - [ ] 能用自己的话解释"时间泄漏"并举例
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

```text
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
   
```text
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

---

### L007
**分类：** AI应用开发
**题目：** 请说说原始事件 vs 特征向量（20min）
**参考答案：** ### 1.1 模型看不懂事件，只看懂数字


```text
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

```text

---

---

---

### L008
**分类：** AI应用开发
**题目：** 请讲讲特征工程 — 从事件流到特征向量的三种模式中的三种特征构造模式（1.5h）
**参考答案：** 打开 `src/data/warehouse/dws_layer.py` 第 135-199 行 `_build_behavior_features()`，这是三种模式的完整实现。

### 模式 1：时间窗口 + COUNT WHERE


```python
# 第 162-173 行
in_7d = group['event_time'] >= ref_date - timedelta(days=7)
in_30d = group['event_time'] >= ref_date - timedelta(days=30)

apply_cnt_7d = (group[in_7d]['event_type'] == 'submit').sum()
page_view_7d = (group[in_7d]['event_type'] == 'page_view').sum()
input_7d = (group[in_7d]['event_type'] == 'input').sum()
error_7d = (group[in_7d]['event_type'] == 'error').sum()

```text
**核心公式**：`COUNT(event_type = X) WHERE event_time IN [ref_date - N天, ref_date]`

**为什么用 `event_time` 而不是 `dt` 分区键？**


```text
dt = 数据写入仓库的日期（可能会跨天延迟）
event_time = 事件实际发生的时间（业务真实时间）

场景：凌晨 01:30 的事件
  - dt 可能是当天（如果 ETL 在凌晨 3 点跑）
  - dt 也可能是第二天（如果 ETL 在半夜 12 点跑）
  - 但 event_time 永远是 "01:30" ← 这才是正确的时间语义

```text
### 模式 2：比率衍生 — 用占比而不是绝对值


```python
# 第 182-188 行
night_hours = group_30d['event_time'].dt.hour.isin(
    [22, 23, 0, 1, 2, 3, 4, 5]
)
night_ops_ratio = night_hours.mean()  # ← 不是 sum()！

```text
**为什么用 `mean()` 而不是 `sum()`？**


```text
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

```text
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

```text
**为什么填 0 而不是均值？**


```text
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

```text

---

---

---

### L009
**分类：** AI应用开发
**题目：** 请讲讲特征工程 — 从事件流到特征向量的三种模式中的动手练习（1.5h）
**参考答案：** ### 练习 1：为电商写特征工程函数（1h）


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

```text
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

```text

---

---

---

### L010
**分类：** AI应用开发
**题目：** 请讲讲特征工程 — 从事件流到特征向量的三种模式中的跨业务思考（30min）
**参考答案：** 用三种模式分析以下业务的特征设计：

**游戏行业 — "玩家付费预测"**：


```text
事件: 登录、副本、充值、社交、PVP

模式1(COUNT WHERE): login_days_7d, dungeon_cnt_7d, recharge_cnt_7d
模式2(比率衍生): pay_rate_30d = 付费天数/登录天数, social_ratio = 好友互动/总操作
模式3(缺失值): 新玩家(第1天) → fillna(0) → 所有行为=0 → 模型知道"这是新玩家"

```text
**打车行业 — "司机流失预测"**：


```text
事件: 接单、取消、完成、评价

模式1: online_hours_7d, order_cnt_7d, cancel_cnt_7d
模式2: cancel_rate = 取消/接单, bad_review_rate = 差评/完成
模式3: 新司机 → fillna(0) → 无历史数据 → 保守评估

```text

---

---

---

### L011
**分类：** AI应用开发
**题目：** 请讲讲特征工程 — 从事件流到特征向量的三种模式中的今日要点
**参考答案：** ```text
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

```text

---

---

---

### L012
**分类：** AI应用开发
**题目：** 为什么不能只用模型？（20min）
**参考答案：** ### 1.1 模型的三个盲区


```text
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

```text
### 1.2 融合方案：规则做安全底线，模型做效率工具


```text
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

```text

---

---

---

### L013
**分类：** AI应用开发
**题目：** 请举例说明核心代码：`inference_pipeline.py` 的 execute()（1h）如何实现？
**参考答案：** 打开 `src/decision_engine/inference_pipeline.py` 第 164-260 行：


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

```text
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

```text

---

---

---

### L014
**分类：** AI应用开发
**题目：** 请讲讲规则 + 模型融合 — 四层决策架构中的动手练习（1.5h）
**参考答案：** ### 练习 1：手写四个版本的决策融合并对比（1h）


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

```text
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

```text

---

---

---

### L015
**分类：** AI应用开发
**题目：** 请讲讲规则 + 模型融合 — 四层决策架构中的跨业务思考（30min）
**参考答案：** ### 医疗分诊的融合架构


```text
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

```text

---

---

---

### L016
**分类：** AI应用开发
**题目：** 请讲讲模型评估 + 线上监控 + 自动熔断中的模型不是训完就结束了（20min）
**参考答案：** ### 1.1 上线后的模型会退化


```text
Day 1:  模型上线，AUC=0.72，通过率 65% → 一切正常
Day 30: 通过率降到 45%，但不知道为什么
Day 60: 逾期率突然翻倍 → 发现欺诈手段变了，模型已经失效 30 天

如果有监控:
Day 30: PSI 告警 → "特征分布漂移" → 触发人工排查 → 确认需要重训
Day 35: 新模型上线，恢复正常

结论: 没有监控的模型 = 定时炸弹

```text

---

---

---

### L017
**分类：** AI应用开发
**题目：** 请讲讲模型评估 + 线上监控 + 自动熔断中的上线前评估：四个核心指标（1h）
**参考答案：** 打开 `src/models/evaluator.py`：

### 2.1 AUC — 排序能力


```text
AUC 回答: "随机抽一个好人一个坏人，模型把坏人排在好人前面的概率"

AUC = 0.5 → 和扔硬币一样（完全没用）
AUC = 0.65 → 勉强可用（比随机好一点）
AUC = 0.75 → 良好
AUC = 0.85 → 优秀
AUC = 0.95 → 优秀但要检查是否过拟合或时间泄漏

项目的阈值: MIN_AUC = 0.65

```text
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


```text
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

```text

---

---

---

### L018
**分类：** AI应用开发
**题目：** 请讲讲模型评估 + 线上监控 + 自动熔断中的熔断器：不让坏模型继续害人（40min）
**参考答案：** 打开 `src/monitoring/circuit_breaker.py`：


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

```text

---

---

---

### L019
**分类：** AI应用开发
**题目：** 请讲讲模型评估 + 线上监控 + 自动熔断中的动手练习（1.5h）
**参考答案：** ### 练习 1：手写 KS 和 PSI 计算（45min）


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

```text
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

```text

---

---

---

### L020
**分类：** AI应用开发
**题目：** 请举例说明三层降级代码精读（1h）如何实现？
**参考答案：** 打开 `src/decision_engine/inference_pipeline.py` 第 310-350 行：


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

```text
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

```text
**为什么 `on_time_rate` 默认 0.5 而不是 0 或 1？**


```text
0.0 → "绝对坏" → 所有降级请求都被拒 → 业务量骤降
1.0 → "绝对好" → 所有降级请求都被通过 → 放行了高风险用户
0.5 → 中间值 → 评分大约 500 分 → MANUAL_REVIEW → 人工兜底

```text

---

---

---

### L021
**分类：** AI应用开发
**题目：** 请讲讲生产级降级 + 容错设计中的动手练习（1.5h）
**参考答案：** ### 练习 1：实现三层降级（45min）


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

```text
### 练习 2：设计搜索系统的降级路径（30min）


```text
搜索系统的四层降级:
  路径1: 语义搜索(深度学习) — 80ms 超时
  路径2: 关键词匹配(ES) — 50ms 超时
  路径3: 热门结果缓存 — 不超时
  路径4: 空结果 + "请优化搜索词"

要求:
  1. 写出每层超时时间的理由
  2. 路径4 返回空结果 → 用户体验很差 → 如何缓解？

```text

---

---

---

### L022
**分类：** AI应用开发
**题目：** 请讲讲生产级降级 + 容错设计中的跨业务思考（30min）
**参考答案：** ```text
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

```text

---

---

---

### L023
**分类：** AI应用开发
**题目：** 请讲讲★ 参考答案中的NL2SQL：让业务人员用自然语言查数仓（1.5h）
**参考答案：** ### 1.1 四步骤架构


```text
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

```text
### 1.2 为什么数仓工程师天然适合做 NL2SQL

**NL2SQL 的瓶颈不是 LLM 生成 SQL 的能力，而是 Schema Context 的质量。**


```text
LLM 能生成:
  SELECT AVG(approval_rate) FROM ads_model_monitor_daily WHERE ...

但它不知道:
  - approval_rate 是"通过率" ← 你的 COMMENT 告诉它的
  - "上周"需要翻译为 dt >= '2026-06-30' AND dt <= '2026-07-06'
  - "渠道"是 channel 列
  - 不能不带 dt 过滤（会全表扫描 10 亿行）

没有好的 COMMENT → LLM 猜错列 → SQL 返回错误结果

```text
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

```text

---

---

---

### L024
**分类：** AI应用开发
**题目：** 请讲讲★ 参考答案中的RAG：让 LLM 基于项目文档回答（1h）
**参考答案：** ### 2.1 RAG 的知识库 = 你的项目文档


```text
问题: "night_ops_ratio_30d 超过多少算异常？"

RAG 检索:
  → config/schemas/dws_wide_table.yaml: "★ 深夜操作占比(22-05时)。>60%→高度可疑"
  → config/rules/credit_policy.yaml: "night_ops_ratio_30d > 0.6 → MANUAL_REVIEW"
  → 01_system_architecture.md: "风控强特征，欺诈团伙常在夜间批量操作"

LLM 综合:
  "night_ops_ratio_30d 超过 60% 触发人工审核(RC_BH001)。
   正常范围 < 30%。> 60% 是高度可疑信号，因为欺诈团伙常在夜间操作。"

```text
### 2.2 切片策略（比向量模型更重要）


```text
错误做法: 每 500 字切一刀
  文档: "特征分为三类: 申请画像、行为衍生、还款表现。申请画像包括..."
  一刀切在 "申请画像包括" 后面 → 丢失了具体特征列表

正确做法: 按语义边界切
  YAML: 每个顶级 key 一个 chunk（一个表定义 = 一个片段）
  SQL:  每个 CREATE TABLE 一个 chunk（一张表的完整 DDL）
  MD:   每个 ## 标题一个 chunk（一个章节一个片段）

为什么？检索时返回的是"完整片段"，不是"半句话"

```text

---

---

---

### L025
**分类：** AI应用开发
**题目：** 请讲讲★ 参考答案中的LangGraph：多步骤 AI 工作流（40min）
**参考答案：** ### 3.1 信贷审批的状态机


```text
rule_check ──REJECT──→ rejection_letter(LLM) ──→ END
    │
    └──PASS──→ model_score ──APPROVE──→ disburse ──→ END
                    │
                    ├──REJECT──→ rejection_letter(LLM)
                    └──MANUAL_REVIEW──→ request_docs(LLM) ──→ END
                                            ↑
                                    用户上传材料后恢复

```text
### 3.2 为什么用 LangGraph 而不是手写 if-else


```text
手写 if-else 的问题:
  改流程 = 改代码 = 改 if-else 分支 = 容易出错
  异步操作(等用户上传材料) → 状态需要自己持久化
  流程可视化 → 要另外画图

LangGraph:
  加一个节点 = graph.add_node("new_step", new_step_fn)
  异步状态 = checkpointer 自动处理
  可视化 = graph.get_graph().draw_mermaid_png()

```text

---

---

---

### L026
**分类：** AI应用开发
**题目：** 请讲讲★ 参考答案中的动手练习（1.5h）
**参考答案：** ### 练习 1：实现 NL2SQL 的 validate_sql()（30min）


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

```text
### 练习 2：设计 RAG 的切片策略（30min）


```text
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

```text
### 练习 3：画出审批工作流的状态图（20min）


```text
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

```text

---

---

---

### L027
**分类：** AI应用开发
**题目：** 请讲讲可解释性 + 综合项目：智能客服质检系统中的SHAP 可解释性（1h）
**参考答案：** ### 1.1 为什么需要 SHAP？


```text
用户问: "为什么拒绝我的贷款？"

不好的回答: "模型评分低于阈值"  ← 等于没说
好的回答: "主要原因——历史逾期2次(影响最大)，近7天申请3次(次要)，深夜操作占比40%(偏高等)"
           ← SHAP 值告诉你的

```text
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

```text
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

```text

---

---

---

### L028
**分类：** AI应用开发
**题目：** 请讲讲可解释性 + 综合项目：智能客服质检系统中的综合项目：智能客服质检系统（3h）
**参考答案：** ### 2.1 业务理解


```text
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

```text
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

```text
**任务 2: PIT 样本构建（20min)**


```python
# 质检的"时间泄漏"风险:
# 特征: 对话结束时的所有信息（包括用户评价！）
# 标签: 质检是否合格
# 如果特征里包含了用户评价 → 模型学会了"差评=不合格"→ 毫无意义

# 正确做法: 特征只用对话结束时的客观信息（不含用户评价）
# 标签用后续的专家抽检结果

```text
**任务 3: 规则+模型融合（30min）**


```text
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

```text
**任务 4: 监控+熔断（15min）**


```text
质检模型监控指标:
  - 不合格率日环比 > 50% → 告警（可能是模型偏差或客服整体质量崩溃）
  - 人工复核率 > 30% → 模型区分力不足
  - 平均评分日环比 > 0.2 → 分布漂移

熔断: 不合格率突增 80% → 暂停自动质检，全部转人工

```text
**任务 5: LLM 应用设计（30min）**


```text
NL2SQL: 运营主管问"本周哪个客服的投诉率最高？"
  → 查询 ads_customer_service_daily 表

RAG: 客服问"用户说货没到，我应该怎么处理？"
  → 知识库: 客服FAQ + 退换货政策 + 物流异常SOP
  → 检索最相关的处理流程
  → 生成建议话术

LangGraph: 申诉工作流
  客服被扣绩效 → 提交申诉 → 主管审核 → AI 辅助判责(LLM分析对话记录)
  → 判定: 维持/撤销

```text
**任务 6: 可解释性（15min）**


```text
客服: "为什么我的对话被判不合格？"

系统输出:
  评分: 0.32/1.0 → 不合格

  SHAP 主要贡献:
  1. keyword_compliance_hits=3 → +0.18（说了 3 个违规词: "保证""绝对""最"）
  2. customer_anger_score=0.78 → +0.12（用户情绪非常愤怒）
  3. conversation_turns=25 → +0.08（对话轮次过长）
  4. has_apology=False → +0.05（没有道歉）
  5. historical_quality_score=0.85 → -0.06（历史表现良好，拉低了不合格概率）

```text

---

---

---

### L029
**分类：** AI应用开发
**题目：** 请讲讲可解释性 + 综合项目：智能客服质检系统中的自评表（30min）
**参考答案：** | 能力 | Day 1 自评 | Day 7 自评 | 提升 | 面试怎么说 |
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

---

### L030
**分类：** AI应用开发
**题目：** 请讲讲可解释性 + 综合项目：智能客服质检系统中的一周回顾
**参考答案：** 两个 7 天计划到此结束。回顾一下你完成的所有产出物：


```text
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

```text
这些产出物就是你面试时可以说的"项目经验"——不只是"我做过信贷风控"，而是"我能把信贷风控中的方法论应用到任何业务"。

---

---

### L031
**分类：** Agent面试题
**题目：** LLM 和 Agent 有什么区别？
**参考答案：** 🌟Agent 和 workflow 有什么区别？
🌟Agent 有什么工作模式？
🌟function call 是什么？
🌟mcp 是协议什么？
🌟skills 是什么？
🌟function call 、mcp、skills 有什么区别？
🌟什么是 A2A 协议？
今天这篇文章，我就用最通俗易懂的方式，把 Agent 相关的**核心概念**一次性给你讲清楚。这些也是面试中经常会被问到的问题，搞懂了不仅能应付面试，更能帮你真正理解 AI 技术的主旋律。
废话不多说，直接开始。（PS：依然还是万字长文图解，可以收藏起来，慢慢看）
LLM 和 Agent 有什么区别？
要搞懂 Agent，咱们得先从 LLM 聊起，因为 Agent 本质上就是在 LLM 的基础上进化出来的。
什么是 LLM？
LLM，全称 Large Language Model，翻译过来就是大语言模型。
你可以把它想象成一个读了互联网上几乎所有文字的超级学霸。它通过学习海量的文本数据，掌握了人类语言的各种规律和知识。我们平时用的 ChatGPT、Claude、DeepSeek、文心一言，底层都是大语言模型。
LLM 的工作原理说白了就是「预测下一个字」。你给它一段话，它会根据学到的语言规律，一个字一个字地往后接。
听起来简单，但因为它学的数据量实在太大了，这种「接龙」的效果好到令人吃惊，它能写文章、写代码、做翻译、回答各种专业问题。
LLM 有什么弊端？
虽然 LLM 非常聪明，但你仔细想想会发现，它其实有点像一个"有嘴没手"的顾问。
第一个弊端是只会「说」不会「做」。你让 LLM「帮我订一张机票」，它会详细告诉你怎么订，但它真没法替你去携程下单。你让它「帮我把这个 Bug 修了」，它能给你改好的代码，但它没法自己打开编辑器去改文件、跑测试。说白了，LLM 的能力被困在对话框里了，它没法跟外部世界互动，没法操作任何系统。
第二个弊端是没有「记忆」。你跟 ChatGPT 聊了一下午，聊了很多你的个人情况和项目背景。结果第二天开一个新对话，它完全不记得你是谁了。因为 LLM 的记忆只限于当前这轮对话的上下文窗口，对话一结束，一切归零。
第三个弊端是不会用「工具」。你问 LLM 今天上海天气怎么样，它只能根据训练数据里的旧知识来猜，而不是像你一样打开天气 App 查实时数据。LLM 本身不能上网搜索、不能查数据库、不能调 API，所有回答都来自它「脑子里」已有的知识，而这些知识不仅有截止日期，还可能是错的，也就是常说的「幻觉」问题。
第四个弊端是不会「规划」。如果你给 LLM 一个复杂任务，比如「帮我做一份竞品分析报告」，它只能一次性生成一大段文字。它不会像人一样先想想应该先搜集哪些信息、分析哪些维度、用什么框架来组织，然后一步一步去执行。LLM 是「被动响应型」的，你问一句它答一句，没法自主拆解任务、制定计划、分步执行。
那 Agent 是什么？
讲完弊端，你可能已经在想：有没有一种方式，能让 LLM 不仅会「说」，还能「做」呢？这就是 Agent 要解决的问题。
Agent，翻译过来叫智能体。简单来说：Agent 就是 LLM 在循环中自主使用工具的系统。
这句话有三个关键词，「LLM」说明 Agent 的核心大脑还是大模型，「工具」说明它能调用外部能力，「循环」说明它不是一问一答就结束，而是会不断地思考、行动、观察结果、再思考，直到任务完成。
打个比方，如果 LLM 是一个只会给你建议的顾问，你问他「怎么装修房子」，他能讲一大堆方案，但绝不会亲自动手。
那 Agent 就是一个能动手干活的项目经理，你说「帮我把房子装修好」，他会自己去找装修队、买材料、盯进度、解决问题，直到装修完成。
Agent 怎么解决 LLM 的弊端？
其实理解了上面的比喻，答案就很清楚了。
针对"只会说不会做"，Agent 引入了工具调用能力，可以调用搜索引擎、数据库、API、代码执行器等各种外部工具来真正执行操作。
针对"没有记忆"，Agent 配备了记忆系统，包括记住当前任务上下文的短期记忆，和存储在外部数据库中、可以跨对话保留的长期记忆。
针对"不会用工具"，业界推出了 MCP 等标准化协议来统一工具接入方式，后面会详细讲。
针对"不会规划"，Agent 具备了任务拆解和规划能力，能把一个大目标分解成多个小步骤，然后逐步执行。
Agent 的核心组成
所以一个完整的 Agent 其实就是四个模块的组合。
第一个是大脑，也就是 LLM，负责理解意图、推理判断、决定下一步行动。
第二个是规划模块，负责把复杂任务拆解成可执行的步骤。
第三个是记忆模块，负责存储和检索信息，让 Agent 能在长时间任务中保持连贯。
第四个是工具模块，是 Agent 的「手和脚」，让它能跟外部世界互动。
用一个实际例子来感受。
假设你对 Agent 说：「帮我查一下下周三上海的天气，如果不下雨就在日历上安排一个户外团建。」
如果是 LLM，它只会告诉你「你可以通过天气 App 查看天气，然后在日历上创建事件」。
而 Agent 会直接调用天气 API 查到下周三多云 25°C 无降雨，然后自动调用日历 API 创建团建事件，最后告诉你「已安排好了」。LLM 告诉你「怎么做」，Agent 直接帮你「做完了」。这就是本质区别。

---

---

### L032
**分类：** Agent面试题
**题目：** Agent 和 Workflow 有什么区别？
**参考答案：** 搞懂了 LLM 和 Agent 的区别之后，你可能还会碰到另一个容易搞混的概念，Workflow（工作流）。
很多人把 Agent 和 Workflow 混为一谈，但它们的设计理念其实完全不同。
先用一个场景来感受区别
假设有一个任务：处理客户的退款申请。Workflow 的做法是这样的，开发者提前写好整个流程：
```text
- 第一步接收申请
- 第二步调用 LLM 提取关键信息
- 第三步查数据库获取订单详情
- 第四步调用 LLM 判断是否符合退款政策
- 第五步执行退款或生成拒绝邮件，第六步发送通知。
```text
每一步做什么、接下来走哪条路，全都是提前在代码里写死的，LLM 只是在某些步骤中被召唤出来做理解和判断。
而 Agent 的做法完全不同。它收到「处理这个退款申请」的任务后，自己来决定怎么做，先看看申请写了什么，然后觉得需要查一下订单信息，发现情况有点特殊就去搜索退款政策文档，推理判断后决定执行退款，最后给客户发邮件通知。
整个过程中，每一步做什么都是 Agent 自己决定的，而不是代码预先规定的。
两者的定义
Workflow 是指 LLM 和工具通过预定义的代码路径进行编排的系统，而 Agent 是指 LLM 动态主导自身流程与工具调用的系统，由 LLM 自主决定如何完成任务。
翻译成大白话就是：Workflow 是「我（开发者）告诉你每一步该做什么」，Agent 是「我告诉你目标，你自己决定怎么做」。
你可以这样类比：Workflow 就像一条工厂流水线，每个工位做什么、零件从哪来到哪去，全都是提前设计好的。工人（LLM）只需要在自己的工位上完成指定动作。
而 Agent 更像一个自主工作的项目经理，老板只告诉他"把这件事搞定"，然后他自己去调研、制定计划、协调资源、推进执行。
核心区别在哪？
两者最核心的区别在于「谁在控制流程」。
Workflow 的控制权在代码手里，流程是确定的、可预测的、可复现的，但灵活性比较差。Agent 的控制权在 LLM 手里，行为是动态的、灵活的、能适应变化的，但相应地也带来了不确定性。
从成本角度看，Workflow 因为流程固定，token 消耗比较省，大约是 Agent 的四分之一。Agent 因为需要反复推理决策，token 消耗要高得多。
从可靠性看，Workflow 行为可预测，出了问题容易定位；Agent 决策路径不确定，调试起来更困难。
什么时候用 Workflow，什么时候用 Agent？
Anthropic 给了一个非常实用的建议：从最简单的方案开始，只在明确需要时才增加复杂度。
如果任务步骤是固定的、可以提前规划好的，或者对可靠性要求很高（比如金融交易、医疗系统），那就用 Workflow。如果任务是开放式的、无法预知所有步骤，或者需要灵活应对各种意外情况，那就用 Agent。
不过在实际生产环境中，最常见的其实是混合架构，Workflow 和 Agent 的结合。正如 LangChain 说的："大多数生产中的 Agent 系统其实是 Workflow 和 Agent 的组合。"
比如一个智能客服系统，整体流程用 Workflow 控制（接收工单→分类→处理→回复），但在"处理"环节遇到复杂问题时，会启动一个 Agent 来自主分析和解决。
所以不要把两者对立起来，它们更像是工具箱里的锤子和螺丝刀，不是竞争关系，而是配合关系。

---

---

### L033
**分类：** Agent面试题
**题目：** Agent 有什么工作模式？
**参考答案：** 🌟function call 是什么？
🌟mcp 是协议什么？
🌟skills 是什么？
🌟function call 、mcp、skills 有什么区别？
🌟什么是 A2A 协议？
今天这篇文章，我就用最通俗易懂的方式，把 Agent 相关的**核心概念**一次性给你讲清楚。这些也是面试中经常会被问到的问题，搞懂了不仅能应付面试，更能帮你真正理解 AI 技术的主旋律。
废话不多说，直接开始。（PS：依然还是万字长文图解，可以收藏起来，慢慢看）
LLM 和 Agent 有什么区别？
要搞懂 Agent，咱们得先从 LLM 聊起，因为 Agent 本质上就是在 LLM 的基础上进化出来的。
什么是 LLM？
LLM，全称 Large Language Model，翻译过来就是大语言模型。
你可以把它想象成一个读了互联网上几乎所有文字的超级学霸。它通过学习海量的文本数据，掌握了人类语言的各种规律和知识。我们平时用的 ChatGPT、Claude、DeepSeek、文心一言，底层都是大语言模型。
LLM 的工作原理说白了就是「预测下一个字」。你给它一段话，它会根据学到的语言规律，一个字一个字地往后接。
听起来简单，但因为它学的数据量实在太大了，这种「接龙」的效果好到令人吃惊，它能写文章、写代码、做翻译、回答各种专业问题。
LLM 有什么弊端？
虽然 LLM 非常聪明，但你仔细想想会发现，它其实有点像一个"有嘴没手"的顾问。
第一个弊端是只会「说」不会「做」。你让 LLM「帮我订一张机票」，它会详细告诉你怎么订，但它真没法替你去携程下单。你让它「帮我把这个 Bug 修了」，它能给你改好的代码，但它没法自己打开编辑器去改文件、跑测试。说白了，LLM 的能力被困在对话框里了，它没法跟外部世界互动，没法操作任何系统。
第二个弊端是没有「记忆」。你跟 ChatGPT 聊了一下午，聊了很多你的个人情况和项目背景。结果第二天开一个新对话，它完全不记得你是谁了。因为 LLM 的记忆只限于当前这轮对话的上下文窗口，对话一结束，一切归零。
第三个弊端是不会用「工具」。你问 LLM 今天上海天气怎么样，它只能根据训练数据里的旧知识来猜，而不是像你一样打开天气 App 查实时数据。LLM 本身不能上网搜索、不能查数据库、不能调 API，所有回答都来自它「脑子里」已有的知识，而这些知识不仅有截止日期，还可能是错的，也就是常说的「幻觉」问题。
第四个弊端是不会「规划」。如果你给 LLM 一个复杂任务，比如「帮我做一份竞品分析报告」，它只能一次性生成一大段文字。它不会像人一样先想想应该先搜集哪些信息、分析哪些维度、用什么框架来组织，然后一步一步去执行。LLM 是「被动响应型」的，你问一句它答一句，没法自主拆解任务、制定计划、分步执行。
那 Agent 是什么？
讲完弊端，你可能已经在想：有没有一种方式，能让 LLM 不仅会「说」，还能「做」呢？这就是 Agent 要解决的问题。
Agent，翻译过来叫智能体。简单来说：Agent 就是 LLM 在循环中自主使用工具的系统。
这句话有三个关键词，「LLM」说明 Agent 的核心大脑还是大模型，「工具」说明它能调用外部能力，「循环」说明它不是一问一答就结束，而是会不断地思考、行动、观察结果、再思考，直到任务完成。
打个比方，如果 LLM 是一个只会给你建议的顾问，你问他「怎么装修房子」，他能讲一大堆方案，但绝不会亲自动手。
那 Agent 就是一个能动手干活的项目经理，你说「帮我把房子装修好」，他会自己去找装修队、买材料、盯进度、解决问题，直到装修完成。
Agent 怎么解决 LLM 的弊端？
其实理解了上面的比喻，答案就很清楚了。
针对"只会说不会做"，Agent 引入了工具调用能力，可以调用搜索引擎、数据库、API、代码执行器等各种外部工具来真正执行操作。
针对"没有记忆"，Agent 配备了记忆系统，包括记住当前任务上下文的短期记忆，和存储在外部数据库中、可以跨对话保留的长期记忆。
针对"不会用工具"，业界推出了 MCP 等标准化协议来统一工具接入方式，后面会详细讲。
针对"不会规划"，Agent 具备了任务拆解和规划能力，能把一个大目标分解成多个小步骤，然后逐步执行。
Agent 的核心组成
所以一个完整的 Agent 其实就是四个模块的组合。
第一个是大脑，也就是 LLM，负责理解意图、推理判断、决定下一步行动。
第二个是规划模块，负责把复杂任务拆解成可执行的步骤。
第三个是记忆模块，负责存储和检索信息，让 Agent 能在长时间任务中保持连贯。
第四个是工具模块，是 Agent 的「手和脚」，让它能跟外部世界互动。
用一个实际例子来感受。
假设你对 Agent 说：「帮我查一下下周三上海的天气，如果不下雨就在日历上安排一个户外团建。」
如果是 LLM，它只会告诉你「你可以通过天气 App 查看天气，然后在日历上创建事件」。
而 Agent 会直接调用天气 API 查到下周三多云 25°C 无降雨，然后自动调用日历 API 创建团建事件，最后告诉你「已安排好了」。LLM 告诉你「怎么做」，Agent 直接帮你「做完了」。这就是本质区别。
Agent 和 Workflow 有什么区别？
搞懂了 LLM 和 Agent 的区别之后，你可能还会碰到另一个容易搞混的概念，Workflow（工作流）。
很多人把 Agent 和 Workflow 混为一谈，但它们的设计理念其实完全不同。
先用一个场景来感受区别
假设有一个任务：处理客户的退款申请。Workflow 的做法是这样的，开发者提前写好整个流程：
```text
- 第一步接收申请
- 第二步调用 LLM 提取关键信息
- 第三步查数据库获取订单详情
- 第四步调用 LLM 判断是否符合退款政策
- 第五步执行退款或生成拒绝邮件，第六步发送通知。
```text
每一步做什么、接下来走哪条路，全都是提前在代码里写死的，LLM 只是在某些步骤中被召唤出来做理解和判断。
而 Agent 的做法完全不同。它收到「处理这个退款申请」的任务后，自己来决定怎么做，先看看申请写了什么，然后觉得需要查一下订单信息，发现情况有点特殊就去搜索退款政策文档，推理判断后决定执行退款，最后给客户发邮件通知。
整个过程中，每一步做什么都是 Agent 自己决定的，而不是代码预先规定的。
两者的定义
Workflow 是指 LLM 和工具通过预定义的代码路径进行编排的系统，而 Agent 是指 LLM 动态主导自身流程与工具调用的系统，由 LLM 自主决定如何完成任务。
翻译成大白话就是：Workflow 是「我（开发者）告诉你每一步该做什么」，Agent 是「我告诉你目标，你自己决定怎么做」。
你可以这样类比：Workflow 就像一条工厂流水线，每个工位做什么、零件从哪来到哪去，全都是提前设计好的。工人（LLM）只需要在自己的工位上完成指定动作。
而 Agent 更像一个自主工作的项目经理，老板只告诉他"把这件事搞定"，然后他自己去调研、制定计划、协调资源、推进执行。
核心区别在哪？
两者最核心的区别在于「谁在控制流程」。
Workflow 的控制权在代码手里，流程是确定的、可预测的、可复现的，但灵活性比较差。Agent 的控制权在 LLM 手里，行为是动态的、灵活的、能适应变化的，但相应地也带来了不确定性。
从成本角度看，Workflow 因为流程固定，token 消耗比较省，大约是 Agent 的四分之一。Agent 因为需要反复推理决策，token 消耗要高得多。
从可靠性看，Workflow 行为可预测，出了问题容易定位；Agent 决策路径不确定，调试起来更困难。
什么时候用 Workflow，什么时候用 Agent？
Anthropic 给了一个非常实用的建议：从最简单的方案开始，只在明确需要时才增加复杂度。
如果任务步骤是固定的、可以提前规划好的，或者对可靠性要求很高（比如金融交易、医疗系统），那就用 Workflow。如果任务是开放式的、无法预知所有步骤，或者需要灵活应对各种意外情况，那就用 Agent。
不过在实际生产环境中，最常见的其实是混合架构，Workflow 和 Agent 的结合。正如 LangChain 说的："大多数生产中的 Agent 系统其实是 Workflow 和 Agent 的组合。"
比如一个智能客服系统，整体流程用 Workflow 控制（接收工单→分类→处理→回复），但在"处理"环节遇到复杂问题时，会启动一个 Agent 来自主分析和解决。
所以不要把两者对立起来，它们更像是工具箱里的锤子和螺丝刀，不是竞争关系，而是配合关系。
Agent 有什么工作模式？
了解了 Agent 是什么之后，下一个问题就是：Agent 到底是怎么「干活」的？就像人干活有不同的方式，有人喜欢边做边想，有人喜欢先列计划再动手，有人喜欢团队协作，Agent 干活也有不同的工作模式。
模式一：ReAct（边想边做）
ReAct 是目前最经典、最基础的 Agent 工作模式，名字来源于 Reasoning + Acting 的缩写，也就是「推理 + 行动」。几乎所有主流的 Agent 框架底层都在用它。
它的核心思想非常简单：Agent 在思考和行动之间不断交替。具体来说就是一个三步循环，先是思考（Thought），分析当前情况决定下一步做什么；然后是行动（Action），调用一个工具来执行；接着是观察（Observation），查看工具返回的结果。然后回到思考，如此循环，直到任务完成。
打个生活化的比方。想象你要收拾行李准备出差，你会先想「我要去上海三天，先看看天气怎么样」，然后打开手机查天气预报，发现会下雨气温 15-20°C，接着想「得带伞和外套」，于是去找出来放进行李箱，再想「还得确认酒店」，打开 App 检查预订信息... 这就是 ReAct 的精髓，每一步都先想后做，做完看结果，再决定下一步。
ReAct 的优点是透明可审计（每一步思考过程都看得见）、灵活适应（遇到意外能随时调整）、通用性强。但它的缺点也很明显：token 消耗大，因为每一步都要完整推理一次；有时会陷入循环，反复执行相同动作走不出来。
模式二：Plan-and-Execute（先想好再做）
如果说 ReAct 是「边想边做」，Plan-and-Execute 就是「先想好再做」。
它把 Agent 的工作分成两个阶段：第一阶段是规划，Agent 先把完整的执行计划想清楚；第二阶段是执行，按计划逐步完成，不用每步都重新思考全局。
用出差的例子来对比，ReAct 是「查天气→想想带什么→找衣服→想想还缺什么→查酒店→想想还要准备什么...」，每一步都重新审视全局。而 Plan-and-Execute 是先列一个清单（查天气、准备衣物、确认酒店、准备证件、叫车），然后逐项打勾执行。
这种模式最大的优势是省钱。规划只做一次，执行阶段不用反复推理，token 消耗大约是 ReAct 的五分之一。
但缺点是不够灵活，如果执行到第 3 步发现情况变了，原来的计划可能就不适用了。所以也有这么个做法是在执行过程中加入「重新规划检查点」，每隔几步检查一下计划是否还靠谱。
模式三：Reflection（做完再检查）
反思模式的核心思想是 Agent 完成任务后不急着交付，而是先自我检查一遍，就像你写完文章不会直接发出去，而是再通读一遍、改一改、润色一下。
实现方式通常有两种。
一种是自我反思，同一个 Agent 完成任务后切换到「审查者」角色来审视自己的输出，发现问题就修改，然后再审查，直到满意。
另一种是双 Agent 对话，一个 Agent 负责生成，另一个负责评审，两者来回迭代直到评审方满意，就像代码的 Code Review 过程。这种模式特别适合对质量要求高的场景，比如代码生成、法律文书、学术论文等。
模式四：Multi-Agent（团队协作）
当任务太复杂、一个 Agent 搞不定的时候怎么办？
答案是派一个团队上。Multi-Agent 模式让多个专业化的 Agent 各司其职，比如一个负责规划、一个负责搜集信息、一个负责写代码、一个负责测试，通过协作来完成复杂任务。
这就像一个项目团队，有产品经理、研究员、开发者、测试员，各自做自己擅长的事。目前主流的多 Agent 框架包括 LangGraph、CrewAI、OpenAI Agents SDK 和微软的 AutoGen 等。
不过 Anthropic 提醒过：不要过早引入多 Agent 架构。很多时候，一个强大的单 Agent 就够用了。只有任务确实需要拆分成多个并行子任务时，多 Agent 才值得引入。
最后**总结**一下：这几种模式不是互斥的，实际中往往是组合使用的。一个多 Agent 系统中，每个 Agent 内部可能用的是 ReAct 模式，整体协作用的是 Multi-Agent 模式，最后还有一个 Reflection 环节来检查质量。
选择哪种模式，关键看你的任务特点和对灵活性、成本、质量的优先级排序。

---

---

### L034
**分类：** Agent面试题
**题目：** Function Call 是什么？
**参考答案：** 前面我们聊 Agent 的时候反复提到一个词，「工具调用」。Agent 能查天气、能搜索信息、能操作数据库，这些能力是怎么实现的？
答案就是 Function Call（函数调用）。
从「只会说话」到「能做事情」
2023 年之前，大语言模型只能做一件事：生成文本。你问它问题，它给你一段文字回答，仅此而已。它说的再好听，也只是「说」，不能「做」。
Function Call 的出现彻底改变了这个局面。它是 OpenAI 在 2023 年 6 月率先推出的一种能力，简单来说就是让 LLM 不仅能生成文字，还能告诉外部程序「我想调用某个函数，参数是这些」。
打个比方。在没有 Function Call 之前，LLM 就像一个只能写字的人，你问他天气，他只能根据记忆回答「上海通常三月份比较潮湿」。
有了 Function Call 之后，这个人学会了「打电话」，你问他天气，他会拿起电话拨给天气台（调用天气 API），听到对方报的实时数据后再告诉你「今天上海 22°C，多云」。
Function Call 的工作原理
Function Call 的工作流程分四步。
第一步，定义函数。开发者预先告诉 LLM「你手边有哪些工具可以用」，用 JSON 格式描述每个函数的名字、功能说明和参数。比如你告诉它有一个 get_weather 函数，接收一个城市名参数，返回天气信息。
```text
{
"tools": [
{
"type": "function",
"function": {
"name": "get_weather",
"description": "获取指定城市的实时天气",
"parameters": {
"type": "object",
"properties": {
"city": {
"type": "string",
"description": "城市名称，比如：上海"
}
},
"required": ["city"]
}
}
}
]
}
```text
第二步，模型判断。用户提问后，LLM 分析用户的意图，自己判断「要回答这个问题，我需要调用哪个函数」。如果用户问「上海今天天气如何」，LLM 会决定调用 get_weather，并生成参数 {"city": "上海"}。
```text
{
"tool_calls": [
{
"type": "function",
"function": {
"name": "get_weather",
"arguments": "{\"city\": \"上海\"}"
}
}
]
}
```text
第三步，执行函数。注意，这一步非常关键，LLM 自己并不执行函数。它只是输出了「我想调用这个函数，参数是这些」的结构化指令。真正执行函数的是你的应用程序。你的代码拿到 LLM 返回的调用指令后，解析出 city=上海，去实际调用天气 API，拿到结果比如 22度，多云。
第四步，生成回答。你的代码把拿到的真实温度数据再次发给 LLM。LLM 这次有了客观数据支撑，就会用非常自然的人类语言回复你：今天上海天气是多云，气温大约 22 摄氏度。
为什么 Function Call 这么重要？
你可能会觉得，这不就是「让 LLM 调 API」吗？有什么了不起的？
关键在于，Function Call 解决了两个核心问题。
第一个是**"什么时候调用"的判断问题**，LLM 能根据用户的自然语言意图，自动判断需不需要调用工具、调用哪个工具。你不需要写复杂的条件判断逻辑，LLM 自己会推理。
第二个是**"传什么参数"的提取问题**，LLM 能从用户的自然语言中提取出结构化的参数。用户说"帮我查一下北京后天的天气"，LLM 能自动提取出 city=北京 和 date=后天。
这两个能力加在一起，就把 LLM 从一个「只会聊天的文本生成器」变成了一个「能理解意图并驱动外部系统的决策引擎」。
而这正是 Agent 的基石。可以说，Function Call 就是 Agent 能力的最底层技术基础，没有 Function Call，Agent 就无法调用工具，也就没法真正「做事」。
目前几乎所有主流大模型都支持 Function Call，包括 OpenAI 的 GPT 系列、Anthropic 的 Claude 系列、Google 的 Gemini 系列，以及各种开源模型如 Llama 等。虽然各家的 API 格式略有不同，但核心原理是一样的。
Function Call 和 Agent 的关系
最后说一下两者的关系。
Function Call 是一次性的「单步调用」，LLM 判断需要调用一个函数，调用完就结束了。而 Agent 是「循环调用」，Agent 在一个循环中反复使用 Function Call，每次调用后观察结果，再决定下一步要不要继续调用其他函数。
所以 Function Call 是 Agent 的「原子操作」，Agent 是 Function Call 的「高级编排」。一个 Agent 完成一个复杂任务，可能需要连续进行十几次 Function Call。

---

---

### L035
**分类：** Agent面试题
**题目：** MCP 是什么协议？
**参考答案：** 前面讲了 Function Call 让 LLM 能调用工具。但随着 Agent 越来越强大，需要连接的工具和服务越来越多，一个新问题浮出水面了，集成太麻烦了。
Function Call 的集成困境
想象一下，你开发了一个 Agent，需要它能连 Slack 发消息、查 Google Drive 的文档、读 GitHub 的代码、查 Postgres 数据库。
用 Function Call 的方式，你需要为每一个服务单独写适配代码，为 Slack 写一套函数定义和调用逻辑、为 Google Drive 写一套、为 GitHub 写一套、为数据库又写一套。
如果你有 N 个 AI 应用，要对接 M 个外部服务，就需要写 N × M 个定制集成。这在实际中完全不可扩展。更头疼的是，每个 LLM 厂商的 Function Call 格式还不完全一样，OpenAI 用 tool_calls，Anthropic 用 tool_use content block，参数结构也有差异。
MCP 的诞生
为了解决这个问题，Anthropic 在 2024 年 11 月开源了 MCP（Model Context Protocol，模型上下文协议）。你可以把 MCP 理解为「AI 界的 USB-C 接口」。
以前，不同的手机、电脑、设备各自用不同的充电线和接口，非常混乱。
USB-C 统一了这一切，一根线就能充电、传数据、接显示器。MCP 做的是同样的事情：它提供了一个统一的标准，让任何 AI 应用都能用同一种方式连接任何外部工具和数据源。
MCP 是怎么工作的？
MCP 的架构很清晰，主要有三个角色。
首先是 MCP Host（宿主），就是你使用的 AI 应用，比如 Claude Desktop、Cursor 编辑器、你自己开发的 Agent 应用。它是整个交互的发起方。
然后是 MCP Client（客户端），它住在 Host 里面，负责跟 MCP Server 通信。你可以把它理解为"翻译官"，Host 想要什么能力，Client 就去跟对应的 Server 沟通。
最后是 MCP Server（服务端），它负责对外暴露具体的工具能力和数据资源。比如有一个 GitHub MCP Server，它能提供"搜索代码""创建 Issue""查看 PR"等工具。一个 Slack MCP Server 能提供"发送消息""搜索频道"等工具。
整个流程就是：用户在 AI 应用中提问 → AI 应用（Host）通过 MCP Client 发现有哪些可用工具 → AI 决定调用某个工具 → MCP Client 向对应的 MCP Server 发送请求 → Server 执行操作返回结果 → AI 基于结果生成回答。
MCP 解决了什么问题？
最核心的就是把 N × M 的集成问题变成了 N + M 的问题。
以前每个 AI 应用要跟每个服务单独对接，现在每个 AI 应用只要支持 MCP 协议（实现一次 Client），每个服务只要提供一个 MCP Server（实现一次 Server），双方就能自动对接。
新增一个服务不需要改任何 AI 应用的代码，新增一个 AI 应用也不需要改任何服务的代码。
而且 MCP Server 暴露的工具是可发现的，AI 应用启动时能自动查询有哪些 MCP Server 可用、每个 Server 提供哪些工具、每个工具的参数是什么。
这意味着 Agent 可以在运行时动态发现新的能力，而不是只能用开发者写死的那些函数。

---

---

### L036
**分类：** Agent面试题
**题目：** Skills 是什么？
**参考答案：** 前面讲了 Function Call 让 Agent 能调用函数，MCP 让 Agent 用统一标准连接工具。但你有没有想过一个问题：Agent 知道怎么调用工具了，但它知道在什么场景下该用什么方法来解决问题吗？
打个比方。你给一个新来的实习生一把锤子、一把螺丝刀、一个扳手（这些是工具），但他可能还是不知道"修一把椅子应该先拧螺丝还是先敲钉子、用什么顺序和方法"。他缺的不是工具，而是经验和方法论，也就是"怎么做"的知识。
这就是 Skills（技能） 要解决的问题。
Skills 是什么？
Skills 是一种自然语言指令文件，通常是 Markdown 格式，用来教 Agent"在什么场景下、按照什么方法、遵循什么规范来完成特定任务"。
在 Claude Code、Cursor 等 AI 工具中，Skills 通常以 SKILL.md 文件的形式存在。
Skills 的结构很简单：顶部有一段 YAML 格式的元数据，声明这个 Skill 什么时候应该被激活（比如"当用户要求代码审查时"）；下面是具体的行为指令，用自然语言写成。
```text

---

name: Code_Review_Expert
description: 当用户要求进行代码审查时，自动触发此技能。
triggers:
- "帮我 review 一下这段代码"
- "代码审查"

---

# 身份设定
你是一个拥有 10 年开发经验的资深后端架构师，你极其看重代码的可读性、性能和安全性。
# 审查工作流
当你进行代码审查时，你必须严格按照以下步骤进行排查：
1. 看结构：检查代码是否符合单一职责原则，有没有超过 100 行的超长方法。
2. 查漏洞：重点检查是否存在 SQL 注入风险、越权访问风险或空指针异常风险。
3. 审性能：是否有在 for 循环里查数据库的愚蠢操作？是否有流对象没有及时 close 释放？
4. 给方案：你绝对不能只挑毛病，必须针对每个问题给出具体的修改建议，并且附带优化后的代码片段。
# 输出规范
语气要专业、极其直接，不要说废话。直接输出一份 Markdown 格式的审查报告，分点列出问题和修改方案。
```text
打个更直观的比方
如果说 MCP 给了 Agent 一个装满工具的厨房，有刀、有锅、有烤箱、有各种调料。
那 Skills 就是一本菜谱，告诉 Agent"做红烧肉要先焯水再炒糖色，加水炖 40 分钟，火候要先大后小"。
厨房（MCP）解决的是"能做什么"的问题，菜谱（Skills）解决的是"该怎么做"的问题。一个完整的 Agent 两者都需要。
Skills 的工作方式
Skills 的工作方式跟 Function Call 和 MCP 有本质不同。
Function Call 和 MCP 都是让 Agent "执行外部操作"，调用 API、查询数据库、发送消息，这些操作发生在 Agent 外部。
而 Skill 不只是告诉 Agent 怎么想，它还能指导 Agent 怎么做，一个 Skill 可以在 SKILL.md 文件中通过 allowed-tools 字段声明它需要使用哪些工具，也可以打包可执行的脚本文件，甚至可以指导 Agent 去调用 MCP 工具或发起Function Call
具体来说，当 Agent 启动时，它会扫描可用的 Skills 列表。当用户提出请求时，Agent 判断有没有匹配的 Skill。如果有，Agent 就把这个 Skill 的内容加载到上下文中，然后按照 Skill 中的指令来思考和行动。
这就像给 Agent 「临时注入了一段专业经验」。没加载 Skill 之前，Agent 只有通用能力；加载了特定 Skill 之后，Agent 在这个领域就变成了专家。
Skills 有什么价值？
Skills 的核心价值在于将专业知识和最佳实践编码成可复用的模块。
举几个例子：
一个"代码审查"Skill 可以定义审查的标准流程、关注点（安全性、性能、可读性）、输出格式；
一个"SQL 优化"Skill 可以编码 DBA 的优化经验，先看执行计划、关注全表扫描、检查索引使用等；
一个"客服回复"Skill 可以定义品牌话术风格、常见问题处理流程、升级规则等。
这些经验以前都在人的脑子里，现在可以写成 Skill 文件让 Agent 使用。而且 Skills 可以共享和复用，你写了一个好的 Skill，团队里所有人的 Agent 都能用上。

---

---

### L037
**分类：** Agent面试题
**题目：** Function Call、MCP、Skills 有什么区别？
**参考答案：** 好了，前面分别讲了 Function Call、MCP 和 Skills，你可能已经有点绕了，它们不都是"让 Agent 更强"的手段吗？到底有什么区别？
咱们用一个统一的比喻来把它们串起来，你就彻底明白了。
一个统一的比喻
想象 Agent 是一个新入职的员工。**Function Call 就是"打电话的能力"**，这个员工学会了怎么拿起电话、拨号、跟对方沟通。这是最基础的能力，没有这个能力他就没法跟外部世界互动。
**MCP 就是"公司的通讯录和电话系统"**，它统一管理所有外部联系方式（供应商、合作伙伴、服务商），员工不需要自己记住每个人的电话号码和通话方式，直接查通讯录就行。新增一个联系人只要加到通讯录里，所有员工都能用。
**Skills 就是"岗位培训手册"**，它告诉员工"遇到客户投诉应该按什么流程处理""做报表应该用什么模板和方法""跟供应商谈判要注意哪些要点"。它教的是做事的方法和规范，而不是打电话的技术。
三者的本质区别
如果用更技术的语言来说，三者的区别体现在几个维度上。
从解决的问题来看，Function Call 解决的是"LLM 怎么跟外部函数交互"这个最基础的问题。MCP 解决的是"怎么用统一标准管理大量工具"的集成问题。Skills 解决的是"Agent 怎么获得领域专业知识"的知识问题。
从运行位置来看，Function Call 的函数在你的应用程序中执行。MCP 的工具在外部的 MCP Server 中执行。Skills 完全在 Agent 的上下文窗口内生效，不涉及任何外部调用。
从技术本质来看，Function Call 是一种 API 协议，LLM 输出结构化的调用请求，应用程序执行后返回结果。MCP 是一种通信标准，定义了 Client 和 Server 之间如何发现和调用工具。Skills 是一种提示词扩展，用自然语言编写的行为指令，加载到 Agent 的上下文中。
从标准化程度来看，Function Call 在各 LLM 厂商之间格式不统一（OpenAI 和 Anthropic 的格式就不一样）。MCP 是统一的开放标准，跨厂商通用。Skills 目前还没有统一标准，各个 Agent 平台有自己的 Skill 格式。
三者是什么关系？
理解了区别之后，更重要的是理解三者的协作关系，它们不是竞争关系，而是分层互补的。
Function Call 是底层基础。MCP 建立在 Function Call 之上，提供了标准化的包装。当你的 Agent 通过 MCP 调用一个工具时，底层其实还是在做 Function Call，只不过格式和通信方式被 MCP 统一了。
Skills 则在一个完全不同的维度上工作，它不参与工具调用的过程，而是指导 Agent"什么时候该调用工具""用什么策略来完成任务"。
用做饭来**总结**：Function Call 是"会使用厨具的能力"（会开火、会切菜），MCP 是"一个设备齐全且标准化的厨房"（所有厨具放在该放的地方，用统一的方式使用），Skills 是"菜谱和厨艺经验"（知道做什么菜、怎么做、火候多大）。三者结合，才能做出一桌好菜。

---

---

### L038
**分类：** Agent面试题
**题目：** 什么是 A2A 协议？
**参考答案：** 今天这篇文章，我就用最通俗易懂的方式，把 Agent 相关的**核心概念**一次性给你讲清楚。这些也是面试中经常会被问到的问题，搞懂了不仅能应付面试，更能帮你真正理解 AI 技术的主旋律。
废话不多说，直接开始。（PS：依然还是万字长文图解，可以收藏起来，慢慢看）
LLM 和 Agent 有什么区别？
要搞懂 Agent，咱们得先从 LLM 聊起，因为 Agent 本质上就是在 LLM 的基础上进化出来的。
什么是 LLM？
LLM，全称 Large Language Model，翻译过来就是大语言模型。
你可以把它想象成一个读了互联网上几乎所有文字的超级学霸。它通过学习海量的文本数据，掌握了人类语言的各种规律和知识。我们平时用的 ChatGPT、Claude、DeepSeek、文心一言，底层都是大语言模型。
LLM 的工作原理说白了就是「预测下一个字」。你给它一段话，它会根据学到的语言规律，一个字一个字地往后接。
听起来简单，但因为它学的数据量实在太大了，这种「接龙」的效果好到令人吃惊，它能写文章、写代码、做翻译、回答各种专业问题。
LLM 有什么弊端？
虽然 LLM 非常聪明，但你仔细想想会发现，它其实有点像一个"有嘴没手"的顾问。
第一个弊端是只会「说」不会「做」。你让 LLM「帮我订一张机票」，它会详细告诉你怎么订，但它真没法替你去携程下单。你让它「帮我把这个 Bug 修了」，它能给你改好的代码，但它没法自己打开编辑器去改文件、跑测试。说白了，LLM 的能力被困在对话框里了，它没法跟外部世界互动，没法操作任何系统。
第二个弊端是没有「记忆」。你跟 ChatGPT 聊了一下午，聊了很多你的个人情况和项目背景。结果第二天开一个新对话，它完全不记得你是谁了。因为 LLM 的记忆只限于当前这轮对话的上下文窗口，对话一结束，一切归零。
第三个弊端是不会用「工具」。你问 LLM 今天上海天气怎么样，它只能根据训练数据里的旧知识来猜，而不是像你一样打开天气 App 查实时数据。LLM 本身不能上网搜索、不能查数据库、不能调 API，所有回答都来自它「脑子里」已有的知识，而这些知识不仅有截止日期，还可能是错的，也就是常说的「幻觉」问题。
第四个弊端是不会「规划」。如果你给 LLM 一个复杂任务，比如「帮我做一份竞品分析报告」，它只能一次性生成一大段文字。它不会像人一样先想想应该先搜集哪些信息、分析哪些维度、用什么框架来组织，然后一步一步去执行。LLM 是「被动响应型」的，你问一句它答一句，没法自主拆解任务、制定计划、分步执行。
那 Agent 是什么？
讲完弊端，你可能已经在想：有没有一种方式，能让 LLM 不仅会「说」，还能「做」呢？这就是 Agent 要解决的问题。
Agent，翻译过来叫智能体。简单来说：Agent 就是 LLM 在循环中自主使用工具的系统。
这句话有三个关键词，「LLM」说明 Agent 的核心大脑还是大模型，「工具」说明它能调用外部能力，「循环」说明它不是一问一答就结束，而是会不断地思考、行动、观察结果、再思考，直到任务完成。
打个比方，如果 LLM 是一个只会给你建议的顾问，你问他「怎么装修房子」，他能讲一大堆方案，但绝不会亲自动手。
那 Agent 就是一个能动手干活的项目经理，你说「帮我把房子装修好」，他会自己去找装修队、买材料、盯进度、解决问题，直到装修完成。
Agent 怎么解决 LLM 的弊端？
其实理解了上面的比喻，答案就很清楚了。
针对"只会说不会做"，Agent 引入了工具调用能力，可以调用搜索引擎、数据库、API、代码执行器等各种外部工具来真正执行操作。
针对"没有记忆"，Agent 配备了记忆系统，包括记住当前任务上下文的短期记忆，和存储在外部数据库中、可以跨对话保留的长期记忆。
针对"不会用工具"，业界推出了 MCP 等标准化协议来统一工具接入方式，后面会详细讲。
针对"不会规划"，Agent 具备了任务拆解和规划能力，能把一个大目标分解成多个小步骤，然后逐步执行。
Agent 的核心组成
所以一个完整的 Agent 其实就是四个模块的组合。
第一个是大脑，也就是 LLM，负责理解意图、推理判断、决定下一步行动。
第二个是规划模块，负责把复杂任务拆解成可执行的步骤。
第三个是记忆模块，负责存储和检索信息，让 Agent 能在长时间任务中保持连贯。
第四个是工具模块，是 Agent 的「手和脚」，让它能跟外部世界互动。
用一个实际例子来感受。
假设你对 Agent 说：「帮我查一下下周三上海的天气，如果不下雨就在日历上安排一个户外团建。」
如果是 LLM，它只会告诉你「你可以通过天气 App 查看天气，然后在日历上创建事件」。
而 Agent 会直接调用天气 API 查到下周三多云 25°C 无降雨，然后自动调用日历 API 创建团建事件，最后告诉你「已安排好了」。LLM 告诉你「怎么做」，Agent 直接帮你「做完了」。这就是本质区别。
Agent 和 Workflow 有什么区别？
搞懂了 LLM 和 Agent 的区别之后，你可能还会碰到另一个容易搞混的概念，Workflow（工作流）。
很多人把 Agent 和 Workflow 混为一谈，但它们的设计理念其实完全不同。
先用一个场景来感受区别
假设有一个任务：处理客户的退款申请。Workflow 的做法是这样的，开发者提前写好整个流程：
```text
- 第一步接收申请
- 第二步调用 LLM 提取关键信息
- 第三步查数据库获取订单详情
- 第四步调用 LLM 判断是否符合退款政策
- 第五步执行退款或生成拒绝邮件，第六步发送通知。
```text
每一步做什么、接下来走哪条路，全都是提前在代码里写死的，LLM 只是在某些步骤中被召唤出来做理解和判断。
而 Agent 的做法完全不同。它收到「处理这个退款申请」的任务后，自己来决定怎么做，先看看申请写了什么，然后觉得需要查一下订单信息，发现情况有点特殊就去搜索退款政策文档，推理判断后决定执行退款，最后给客户发邮件通知。
整个过程中，每一步做什么都是 Agent 自己决定的，而不是代码预先规定的。
两者的定义
Workflow 是指 LLM 和工具通过预定义的代码路径进行编排的系统，而 Agent 是指 LLM 动态主导自身流程与工具调用的系统，由 LLM 自主决定如何完成任务。
翻译成大白话就是：Workflow 是「我（开发者）告诉你每一步该做什么」，Agent 是「我告诉你目标，你自己决定怎么做」。
你可以这样类比：Workflow 就像一条工厂流水线，每个工位做什么、零件从哪来到哪去，全都是提前设计好的。工人（LLM）只需要在自己的工位上完成指定动作。
而 Agent 更像一个自主工作的项目经理，老板只告诉他"把这件事搞定"，然后他自己去调研、制定计划、协调资源、推进执行。
核心区别在哪？
两者最核心的区别在于「谁在控制流程」。
Workflow 的控制权在代码手里，流程是确定的、可预测的、可复现的，但灵活性比较差。Agent 的控制权在 LLM 手里，行为是动态的、灵活的、能适应变化的，但相应地也带来了不确定性。
从成本角度看，Workflow 因为流程固定，token 消耗比较省，大约是 Agent 的四分之一。Agent 因为需要反复推理决策，token 消耗要高得多。
从可靠性看，Workflow 行为可预测，出了问题容易定位；Agent 决策路径不确定，调试起来更困难。
什么时候用 Workflow，什么时候用 Agent？
Anthropic 给了一个非常实用的建议：从最简单的方案开始，只在明确需要时才增加复杂度。
如果任务步骤是固定的、可以提前规划好的，或者对可靠性要求很高（比如金融交易、医疗系统），那就用 Workflow。如果任务是开放式的、无法预知所有步骤，或者需要灵活应对各种意外情况，那就用 Agent。
不过在实际生产环境中，最常见的其实是混合架构，Workflow 和 Agent 的结合。正如 LangChain 说的："大多数生产中的 Agent 系统其实是 Workflow 和 Agent 的组合。"
比如一个智能客服系统，整体流程用 Workflow 控制（接收工单→分类→处理→回复），但在"处理"环节遇到复杂问题时，会启动一个 Agent 来自主分析和解决。
所以不要把两者对立起来，它们更像是工具箱里的锤子和螺丝刀，不是竞争关系，而是配合关系。
Agent 有什么工作模式？
了解了 Agent 是什么之后，下一个问题就是：Agent 到底是怎么「干活」的？就像人干活有不同的方式，有人喜欢边做边想，有人喜欢先列计划再动手，有人喜欢团队协作，Agent 干活也有不同的工作模式。
模式一：ReAct（边想边做）
ReAct 是目前最经典、最基础的 Agent 工作模式，名字来源于 Reasoning + Acting 的缩写，也就是「推理 + 行动」。几乎所有主流的 Agent 框架底层都在用它。
它的核心思想非常简单：Agent 在思考和行动之间不断交替。具体来说就是一个三步循环，先是思考（Thought），分析当前情况决定下一步做什么；然后是行动（Action），调用一个工具来执行；接着是观察（Observation），查看工具返回的结果。然后回到思考，如此循环，直到任务完成。
打个生活化的比方。想象你要收拾行李准备出差，你会先想「我要去上海三天，先看看天气怎么样」，然后打开手机查天气预报，发现会下雨气温 15-20°C，接着想「得带伞和外套」，于是去找出来放进行李箱，再想「还得确认酒店」，打开 App 检查预订信息... 这就是 ReAct 的精髓，每一步都先想后做，做完看结果，再决定下一步。
ReAct 的优点是透明可审计（每一步思考过程都看得见）、灵活适应（遇到意外能随时调整）、通用性强。但它的缺点也很明显：token 消耗大，因为每一步都要完整推理一次；有时会陷入循环，反复执行相同动作走不出来。
模式二：Plan-and-Execute（先想好再做）
如果说 ReAct 是「边想边做」，Plan-and-Execute 就是「先想好再做」。
它把 Agent 的工作分成两个阶段：第一阶段是规划，Agent 先把完整的执行计划想清楚；第二阶段是执行，按计划逐步完成，不用每步都重新思考全局。
用出差的例子来对比，ReAct 是「查天气→想想带什么→找衣服→想想还缺什么→查酒店→想想还要准备什么...」，每一步都重新审视全局。而 Plan-and-Execute 是先列一个清单（查天气、准备衣物、确认酒店、准备证件、叫车），然后逐项打勾执行。
这种模式最大的优势是省钱。规划只做一次，执行阶段不用反复推理，token 消耗大约是 ReAct 的五分之一。
但缺点是不够灵活，如果执行到第 3 步发现情况变了，原来的计划可能就不适用了。所以也有这么个做法是在执行过程中加入「重新规划检查点」，每隔几步检查一下计划是否还靠谱。
模式三：Reflection（做完再检查）
反思模式的核心思想是 Agent 完成任务后不急着交付，而是先自我检查一遍，就像你写完文章不会直接发出去，而是再通读一遍、改一改、润色一下。
实现方式通常有两种。
一种是自我反思，同一个 Agent 完成任务后切换到「审查者」角色来审视自己的输出，发现问题就修改，然后再审查，直到满意。
另一种是双 Agent 对话，一个 Agent 负责生成，另一个负责评审，两者来回迭代直到评审方满意，就像代码的 Code Review 过程。这种模式特别适合对质量要求高的场景，比如代码生成、法律文书、学术论文等。
模式四：Multi-Agent（团队协作）
当任务太复杂、一个 Agent 搞不定的时候怎么办？
答案是派一个团队上。Multi-Agent 模式让多个专业化的 Agent 各司其职，比如一个负责规划、一个负责搜集信息、一个负责写代码、一个负责测试，通过协作来完成复杂任务。
这就像一个项目团队，有产品经理、研究员、开发者、测试员，各自做自己擅长的事。目前主流的多 Agent 框架包括 LangGraph、CrewAI、OpenAI Agents SDK 和微软的 AutoGen 等。
不过 Anthropic 提醒过：不要过早引入多 Agent 架构。很多时候，一个强大的单 Agent 就够用了。只有任务确实需要拆分成多个并行子任务时，多 Agent 才值得引入。
最后

---

---

### L039
**分类：** LLM与AI工程
**题目：** RAG 解决了什么问题？（20min）
**参考答案：** ### 1.1 LLM 的三个"不知道"


```text
问题 1: "什么是 night_ops_ratio_30d？"
  LLM 知识截止在训练数据 — 不知道你这个项目的特定概念

问题 2: "截至昨天，各渠道通过率是多少？"
  LLM 不知道实时数据 — 知识库是静态的

问题 3: "user_000042 为什么被拒？"
  LLM 没有企业内部数据的访问权限 — 这是隐私数据

```text
### 1.2 RAG 的解决方案


```text
用户提问
  │
  ▼
┌─────────────────┐
│  1. 检索阶段      │  ← 从知识库中找出最相关的文档片段
│  向量搜索          │
│  Top-K 检索        │
└────────┬────────┘
         │  "相关文档片段"
         ▼
┌─────────────────┐
│  2. 增强阶段      │  ← 把检索结果 + 用户问题 拼成 Prompt
│  Prompt 构造       │
│  Context 注入      │
└────────┬────────┘
         │  "完整 Prompt"
         ▼
┌─────────────────┐
│  3. 生成阶段      │  ← LLM 基于 Context 回答问题
│  LLM 回答         │
│  引用来源          │
└─────────────────┘

```text

---

---

---

### L040
**分类：** LLM与AI工程
**题目：** 请讲讲RAG 全链路详解：从文档到问答中的RAG 的核心步骤（1.5h）
**参考答案：** ### 2.1 文档切片（Chunking）— 最重要但最容易被忽略


```python
# 为什么切片策略比向量模型更重要？

# 错误做法: 按固定长度切（500字一刀）
# 正文: "特征分为三类: 申请画像、行为衍生、还款表现。
#        申请画像包括 apply_amount_avg, monthly_income..."
# 切片1: "特征分为三类: 申请画像、行为衍生、还款表现。申请画像包括"
# 切片2: "apply_amount_avg, monthly_income..."
# ❌ 检索到切片2 → LLM 不知道这是"申请画像"的一部分 → 回答不完整

# 正确做法: 按语义边界切
# YAML: 每个顶级 key 一个 chunk
# SQL:  每个 CREATE TABLE 一个 chunk
# MD:   每个 ## 标题一个 chunk

```text
**不同文档类型的切片策略**：


```python
def chunk_document(file_path: str) -> list[dict]:
    """根据文件类型选择不同的切片策略"""
    if file_path.endswith('.yaml'):
        # YAML: 按顶级 key 切
        with open(file_path) as f:
            data = yaml.safe_load(f)
        return [
            {"text": yaml.dump({k: v}), "metadata": {"key": k, "source": file_path}}
            for k, v in data.items()
        ]

    elif file_path.endswith('.sql'):
        # SQL: 按 CREATE TABLE 切
        with open(file_path) as f:
            content = f.read()
        stmts = [s.strip() for s in content.split(';') if 'CREATE TABLE' in s]
        return [
            {"text": s, "metadata": {"type": "ddl", "source": file_path}}
            for s in stmts
        ]

    elif file_path.endswith('.md'):
        # Markdown: 按 ## 标题切
        with open(file_path) as f:
            content = f.read()
        chunks = re.split(r'\n## ', content)
        return [
            {"text": f"## {chunk}", "metadata": {"source": file_path}}
            for chunk in chunks if chunk.strip()
        ]

    else:
        # 其他: 按段落切（每段至少 100 字）
        ...

```text
### 2.2 向量化（Embedding）


```python
def embed_chunks(chunks: list[dict], embedding_model: str = "text-embedding-3-small"):
    """
    将文本片段转为向量。

    为什么向量？因为文本不能直接做相似度搜索。
    向量化的目标是: 语义相近的文本 → 向量距离近 → 检索准确

    三种选择:
    1. OpenAI text-embedding-3-small  — 性价比最高, 1536 维
    2. BAAI/bge-large-zh              — 中文场景最强开源
    3. text-embedding-3-large         — 精度最高, 3072 维
    """
    import openai

    texts = [chunk["text"] for chunk in chunks]
    response = openai.embeddings.create(
        model=embedding_model,
        input=texts
    )
    embeddings = [item.embedding for item in response.data]

    # 每个 chunk 带上 embedding 和 metadata
    for i, chunk in enumerate(chunks):
        chunk["embedding"] = embeddings[i]

    return chunks

```text
### 2.3 向量检索（Similarity Search）


```python
import numpy as np

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度 — 衡量两个向量的方向一致性"""
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search(query: str, chunk_embeddings: list[dict],
           query_embedding_model: str = "text-embedding-3-small", k: int = 3):
    """
    检索最相关的 K 个文档片段。

    Step 1: 用户问题 → 向量
    Step 2: 向量 vs 所有 chunk → 算相似度
    Step 3: 排序 → 取 Top-K

    为什么用余弦相似度不是欧氏距离？
    余弦: 只关心方向 — 适合检索语义相似的文本
    欧氏: 关心距离 — 不适合高维向量（维度灾难）
    """
    # Step 1: 用户问题向量化
    query_vector = embed_chunks([{"text": query}])

    # Step 2: 算相似度
    results = []
    for chunk in chunk_embeddings:
        score = cosine_similarity(query_vector, chunk["embedding"])
        results.append({"text": chunk["text"], "score": score,
                        "metadata": chunk.get("metadata", {})})

    # Step 3: 取 Top-K
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]

```text
### 2.4 Prompt 构造 + LLM 回答


```python
def build_rag_prompt(query: str, retrieved_chunks: list[dict]) -> str:
    """构造 RAG 的 Prompt — 把检索结果作为 Context 注入"""
    context = "\n\n".join(
        f"[来源: {chunk['metadata'].get('source', 'unknown')}]\n{chunk['text']}"
        for chunk in retrieved_chunks
    )

    return f"""请根据以下文档内容回答问题。如果文档中没有相关信息，请明确说"未找到相关信息"。

---

---

### L041
**分类：** LLM与AI工程
**题目：** 请讲讲RAG 全链路详解：从文档到问答中的要求
**参考答案：** 1. 基于参考文档回答，不要自行编造
2. 引用具体来源（文件名）
3. 如果文档内容不足以回答，说出来"""


def rag_answer(query: str, chunk_embeddings: list[dict]):
    """完整的 RAG 流程: 检索 → 增强 → 生成"""
    # Step 1: 检索 Top-3
    top_chunks = search(query, chunk_embeddings, k=3)

    # Step 2: 构造 Prompt
    prompt = build_rag_prompt(query, top_chunks)

    # Step 3: LLM 生成
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0  # RAG 场景不需要"创意"，需要"精确"
    )

    return response.choices[0].message.content

```text
### 2.5 重排序（Re-ranking）— 进阶优化


```python
# 为什么需要重排序？
# 向量检索的 Top-K 可能有"语义相似但不回答问题"的 chunk
# 重排序用更强的模型（Cross-Encoder）重新打分

def rerank(query: str, candidates: list[dict]) -> list[dict]:
    """
    用 Cross-Encoder 重排序。

    对比:
    向量检索（Bi-Encoder）: 快但浅 — 一次 embedding 全部存储
    重排序（Cross-Encoder）: 慢但准 — 每对(query, chunk)一起过模型
    """
    from sentence_transformers import CrossEncoder

    model = CrossEncoder('BAAI/bge-reranker-v2-m3')

    pairs = [(query, c["text"]) for c in candidates]
    scores = model.predict(pairs)

    for i, c in enumerate(candidates):
        c["rerank_score"] = float(scores[i])

    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    return candidates

```text

---

---

---

### L042
**分类：** LLM与AI工程
**题目：** 请讲讲RAG 全链路详解：从文档到问答中的动手练习：构建一个最小 RAG 系统（1.5h）
**参考答案：** ```python
"""
练习目标: 为项目的 Schema 文档构建 RAG 查询系统。

知识库: config/schemas/dws_wide_table.yaml
         config/rules/credit_policy.yaml
问题: "night_ops_ratio_30d 超过多少算异常？"

要求:
1. 实现文档切片（按 YAML 顶级 key 切）
2. 实现向量化（可以用 OpenAI API 或 sentence-transformers 本地模型）
3. 实现向量检索（余弦相似度，Top-3）
4. 实现 Prompt 构造 + LLM 回答
5. 验证回答质量
"""

import yaml
import numpy as np

# 这里简化: 用简单的关键词匹配替代向量检索（不需要 API key）
class MiniRAG:
    """最小 RAG 系统 — 用关键词匹配替代向量检索"""

    def __init__(self, docs_dir: str):
        self.chunks = []
        self._load_docs(docs_dir)

    def _load_docs(self, docs_dir):
        """加载 YAML 文档，按顶级 key 切分"""
        from pathlib import Path
        for yaml_file in Path(docs_dir).glob("*.yaml"):
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            for key, value in data.items():
                self.chunks.append({
                    "text": yaml.dump({key: value}),
                    "metadata": {"source": str(yaml_file), "key": key}
                })

    def search(self, query: str, k: int = 3) -> list[dict]:
        """用关键词匹配检索（生产中用向量检索）"""
        query_words = set(query.lower().split())
        scored = []
        for chunk in self.chunks:
            text_lower = chunk["text"].lower()
            # 计算关键词命中数量
            hits = sum(1 for w in query_words if w in text_lower)
            scored.append({"text": chunk["text"], "score": hits,
                           "metadata": chunk["metadata"]})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    def answer(self, query: str) -> str:
        # 1. 检索
        top = self.search(query)

        # 2. 构造 Prompt
        context = "\n\n".join(c["text"] for c in top)
        prompt = f"根据以下文档回答:\n{context}\n\n问题: {query}"

        # 3. 如果是生产环境，这里调用 LLM
        # 演示: 返回检索到的文档作为模拟回答
        return f"检索到 {len(top)} 个相关文档片段:\n\n" + context


# 测试
rag = MiniRAG("credit_risk_control_system/config/schemas")
result = rag.answer("什么是 night_ops_ratio_30d？")
print(result)

```text

---

---

---

### L043
**分类：** LLM与AI工程
**题目：** 请讲讲RAG 全链路详解：从文档到问答中的RAG 的常见陷阱
**参考答案：** | 陷阱 | 表现 | 解决方案 |
|------|------|---------|
| 检索了但没用 | LLM 忽略检索结果 | 在 Prompt 里强调"根据文档回答" |
| 切片太碎 | 丢失上下文 | 按语义边界切，500-1000 字 |
| Top-K 太大 | Context 太长，模型丢失重点 | K=3-5，结合 rerank |
| 向量不匹配 | query 和文档语义不对齐 | 用相同的 embedding 模型 |
| 知识库过时 | LLM 回答过时信息 | 定期重建索引 |

---

---

### L044
**分类：** LLM与AI工程
**题目：** 请讲讲feature_service 和 rule_engine 作为依赖注入中的FastAPI 的核心特性
**参考答案：** ### 1. 极致的性能
FastAPI 底层基于 **Starlette**（Web 框架）和 **Pydantic**（数据校验）。
它的异步能力（async/await）使其性能与 Node.js 和 Go 相当，远超传统 Flask/Django。
在信贷风控这种需要 50ms 级低延迟推理的场景中，异步特性可以保证在等待 Redis 特征查询或远程模型调用时，不阻塞其他请求。

### 2. 自动生成交互式文档
只要定义了 Pydantic 模型和路由，FastAPI 就会自动生成 **Swagger UI** 和 **ReDoc** 两份交互式 API 文档。
开发人员、测试人员、甚至业务方都可以直接在网页上测试接口，极大降低沟通成本。

### 3. 基于类型提示的数据校验
通过 Python 的类型注解（Type Hints），FastAPI 可以在请求进来时自动校验参数类型、范围、格式，并将请求体自动解析为 Pydantic 对象。
这不仅减少了手动写校验代码的繁琐，还提供了编辑器自动补全和静态检查。

### 4. 依赖注入系统
FastAPI 内置了强大的依赖注入机制，可以将数据库连接、模型加载、特征服务客户端等公共依赖，以声明式的方式注入到路由函数中，代码解耦且易于测试。

### 5. 原生支持 WebSocket、后台任务、中间件
这使得它可以胜任实时数据推送、异步日志上报等需求。

---

---

---

### L045
**分类：** LLM与AI工程
**题目：** 请讲讲feature_service 和 rule_engine 作为依赖注入中的在 AI/ML 系统中的具体作用
**参考答案：** 结合我们之前的信贷风控架构，FastAPI 被用来构建**模型推理服务**和**决策网关**：

### 1. 模型推理 API
它将训练好的模型（评分卡、XGBoost、PyTorch）封装为 RESTful 接口：

```python
from fastapi import FastAPI
from pydantic import BaseModel
import joblib

app = FastAPI()
model = joblib.load("scorecard.pkl")

class LoanRequest(BaseModel):
    age: int
    income: float
    credit_score: int
    # ... 其它特征字段

@app.post("/predict")
async def predict(request: LoanRequest):
    features = [[request.age, request.income, request.credit_score]]
    score = model.predict(features)[0]
    return {"score": float(score), "decision": "PASS" if score > 600 else "REJECT"}

```text
当上游业务系统发起 HTTP 请求时，FastAPI 自动校验字段类型、缺失值，省去大量手工判断。

### 2. 集成特征获取与规则引擎
实际生产推理往往需要先获取在线特征，再过黑名单，然后调用模型。这些逻辑可以通过 FastAPI 的依赖注入优雅组织：

```python
from fastapi import Depends
# feature_service 和 rule_engine 作为依赖注入
@app.post("/credit/apply")
async def apply(
    req: ApplyRequest,
    features = Depends(feature_service),
    rules = Depends(rule_engine)
):
    # 1. 黑名单检查
    if rules.check_blacklist(req.user_id):
        return {"decision": "REJECT", "reason": "命中黑名单"}
    # 2. 获取特征并打分
    feats = await features.get_online(req.user_id)
    score = model.predict(feats)
    # 3. 返回决策
    ...

```text
### 3. 高性能异步处理
在线推理时，服务往往要并发请求多个服务（如 Redis 查用户画像、HTTP 调三方征信），
使用 `async/await` 可以让这些 I/O 操作并发执行，大幅降低单次请求的总耗时。

### 4. 接口文档与团队协作
信贷风控涉及数据、算法、后端、产品等多个角色。
FastAPI 自动生成的文档就是一份“活的接口规范”，所有人都能直观看到需要传哪些参数、参数含义、返回格式，且可以在文档页直接调试。

---

---

---

### L046
**分类：** LLM与AI工程
**题目：** 为什么选 FastAPI 而不是 Flask？
**参考答案：** | 维度 | FastAPI | Flask |
|------|---------|-------|
| 异步支持 | 原生 async/await，性能高 | 需额外扩展（gevent/asyncio） |
| 数据校验 | 自动基于 Pydantic，类型安全 | 需手动写校验逻辑或插件 |
| API 文档 | 自动生成 Swagger/ReDoc | 需额外安装 flasgger 等 |
| 性能 | 接近 NodeJS/Go | 同步模型下并发能力受限 |
| 生态 | 完美兼容 Starlette 生态，与 Pydantic、SQLAlchemy 无缝集成 | 庞大但逐渐老旧 |

生产级 AI 应用对**低延迟、高并发、严格的输入输出定义**要求很高，FastAPI 在这些方面是当前 Python 生态的最优解。

---

**一句话**总结**：FastAPI 是现代 Python 构建高性能、类型安全 API 的事实标准，
它在 AI 系统中充当推理网关，通过异步能力、自动校验和文档生成，将模型服务化过程变得极其高效和可靠。**

---

---

### L047
**分类：** LLM与AI工程
**题目：** 什么是向量数据库？（20min）
**参考答案：** ### 1.1 关系型数据库 vs 向量数据库


```text
关系型数据库 (MySQL/PostgreSQL):
  数据: 结构化数据（行 + 列）
  查询: "SELECT * FROM users WHERE age > 18"
  比较: 精确匹配 / 范围查询

向量数据库 (Milvus/Qdrant/Chroma):
  数据: 向量（float 数组，如 [0.1, 0.2, -0.05, ..., 0.8]）
  查询: "找到和这个向量最相似的 10 个向量"
  比较: 余弦相似度 / 欧氏距离 / 内积

```text
### 1.2 向量数据库解决什么问题？


```text
传统搜索的问题:
  用户搜 "深夜操作多的用户" → MySQL 不知道你在说什么
  SQL 只能处理精确匹配: "WHERE night_ops_ratio > 0.6"

向量搜索:
  "深夜操作多的用户" → embedding → [0.3, 0.1, ...]
  → 在向量库中找相似的文档 → 找到 night_ops_ratio_30d 的定义

核心: 把"语义"变成"向量距离" — 语义相近 → 向量距离近

```text

---

---

---

### L048
**分类：** LLM与AI工程
**题目：** 请说说主流向量数据库对比（15min）
**参考答案：** | 数据库 | 部署方式 | 性能 | 适用场景 | 学习成本 |
|--------|---------|------|---------|:-------:|
| **Chroma** | 本地文件 | 入门级 | 开发/原型验证 | ⭐ |
| **Milvus** | 分布式 | ⭐⭐⭐⭐⭐ | 生产环境/百万级+ | ⭐⭐⭐⭐ |
| **Qdrant** | Docker单机/集群 | ⭐⭐⭐⭐ | 中大规模生产 | ⭐⭐ |
| **Weaviate** | Docker | ⭐⭐⭐ | 集成度高的场景 | ⭐⭐⭐ |
| **FAISS (Facebook)** | Python库 | ⭐⭐⭐⭐⭐ | 离线大规模搜索 | ⭐⭐⭐ |
| **Pinecone** | 云托管 | ⭐⭐⭐⭐ | 不想运维的团队 | ⭐ |

---

---

---

### L049
**分类：** LLM与AI工程
**题目：** 请详细讲解**核心概念**与原理（40min）
**参考答案：** ### 3.1 Embedding 维度


```python
# 不同模型的输出维度对比

模型                    输出维度    一个 100 万条记录的索引
OpenAI text-embedding-3-small   1536    约 6 GB
OpenAI text-embedding-3-large   3072    约 12 GB
BAAI/bge-large-zh               1024    约 4 GB
BERT base                       768     约 3 GB

# 维度越高 → 表达力越强 → 存储和计算越大 → 检索越慢
# 1536 维是当前性价比最高的选择

```text
### 3.2 索引算法


```python
# 精确搜索 vs ANN（近似最近邻）

# 精确搜索（暴力搜索）:
#   O(n) — 每条查询扫描所有 100 万条向量，耗时 ~500ms
#   100% 准确，但太慢

# ANN搜索 (Approximate Nearest Neighbor):
#   O(log n) — 用索引结构加速，耗时 ~5ms
#   99% 准确（可以接受的小误差），快 100 倍

# 常用 ANN 算法:
# IVF (Inverted File Index) — 分桶搜索
# HNSW (Hierarchical Navigable Small World) — 图搜索，最推荐
# PQ (Product Quantization) — 压缩向量，减少存储

```text
### 3.3 HNSW 算法原理（面试常问）


```text
HNSW 像一个"高速公路系统":
Level 3: 只有主要城市之间有高速公路（概括信息）
Level 2: 更多城市 + 高速公路 + 省道
Level 1: 全部道路，精确到街道（详细信息）

搜索过程:
  1. 从 Level 3（概要）开始 → 找到最近的大城市
  2. 下到 Level 2 → 在区域内搜索
  3. 下到 Level 1 → 精确搜索

效果: 100 万条向量，5ms 内找到最近邻

```text

---

---

---

### L050
**分类：** LLM与AI工程
**题目：** 请举例说明动手实战：用 Chroma 搭建 RAG 知识库（1h）如何实现？
**参考答案：** ### 4.1 安装与初始化


```bash
pip install chromadb sentence-transformers

```text
### 4.2 完整代码


```python
import chromadb
from sentence_transformers import SentenceTransformer
import yaml
from pathlib import Path

class LocalKnowledgeBase:
    """基于 Chroma 的本地知识库"""

    def __init__(self, persist_dir: str = "./knowledge_base"):
        # 使用本地 embedding 模型（不需要 API key）
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

        # 持久化存储 — 下次启动不需要重建
        self.client = chromadb.PersistentClient(path=persist_dir)

        # 创建 collection（类似 MySQL 中的表）
        self.collection = self.client.get_or_create_collection(
            name="credit_risk_docs",
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )

    # ═══ 写入: 文档 → 切片 → embedding → 存储 ═══
    def add_yaml_file(self, file_path: str):
        """
        添加 YAML 文件到知识库。

        切片策略: 按顶级 key 切（每张表/每条规则一个 chunk）
        metadata 包含: 源文件、chunk 名称
        """
        with open(file_path) as f:
            data = yaml.safe_load(f)

        for key, value in data.items():
            text = yaml.dump({key: value})
            embedding = self.embedder.encode(text).tolist()

            self.collection.add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[{"source": str(file_path), "key": key}],
                ids=[f"{Path(file_path).stem}__{key}"]
            )

        print(f"  已添加 {len(data)} 个 chunk 到知识库: {file_path}")

    # ═══ 读取: 问题 → embedding → 向量检索 → Top-K ═══
    def search(self, query: str, k: int = 5) -> list[dict]:
        """
        向量检索 — 核心操作

        query_embedding: 用户的自然语言问题 → embedding
        n_results: 返回多少个最相关的文档片段
        """
        query_embedding = self.embedder.encode(query).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )

        # 格式化返回
        formatted = []
        for i in range(len(results['ids'][0])):
            formatted.append({
                "text": results['documents'][0][i],
                "score": 1 - results['distances'][0][i],  # 余弦距离 → 相似度
                "metadata": results['metadatas'][0][i],
            })
        return formatted


# ═══════════════════════════════════════════
# 使用示例
# ═══════════════════════════════════════════

def build_project_knowledge_base():
    """为项目构建完整的向量知识库"""
    kb = LocalKnowledgeBase()

    # 添加 Schema 文档
    schemas_dir = Path("config/schemas")
    for yaml_file in schemas_dir.glob("*.yaml"):
        kb.add_yaml_file(yaml_file)

    # 添加规则文档
    kb.add_yaml_file("config/rules/credit_policy.yaml")

    return kb


def demo_query():
    kb = build_project_knowledge_base()

    queries = [
        "night_ops_ratio_30d 超过多少算异常？",
        "什么情况下会被拒绝贷款？",
        "on_time_rate 新用户默认值是多少？",
    ]

    for q in queries:
        print(f"\n🔍 查询: {q}")
        results = kb.search(q, k=2)
        for r in results:
            print(f"  [相似度 {r['score']:.3f}] {r['text'][:80]}...")


if __name__ == "__main__":
    demo_query()

```text
### 4.3 查询结果示例


```text
🔍 查询: night_ops_ratio_30d 超过多少算异常？
  [相似度 0.89] type: DOUBLE | 范围: [0.0, 1.0] | >60%→高度可疑
  [相似度 0.72] aggregation: mean(event_time.hour IN [22,23,0,1,2,3,4,5])

🔍 查询: 什么情况下会被拒绝贷款？
  [相似度 0.83] id: BLACKLIST_HIT | condition: user_id_in_blacklist == True
  [相似度 0.76] id: FRAUD_SCORE_HIGH | condition: fraud_score > 0.8

```text

---

---

---

### L051
**分类：** LLM与AI工程
**题目：** 请讲讲向量数据库：从概念到实战中的进阶：Milvus 生产部署
**参考答案：** ### 5.1 Docker 部署


```bash
# docker-compose.yml
version: '3.5'
services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000

  minio:
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin

  milvus:
    image: milvusdb/milvus:v2.4.0
    depends_on: [etcd, minio]
    ports:
      - "19530:19530"

```text
### 5.2 连接 Milvus


```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

# 连接
connections.connect(host="localhost", port="19530")

# 定义 schema
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
]
schema = CollectionSchema(fields, description="知识库")

# 创建 collection
collection = Collection(name="knowledge_base", schema=schema)

# 创建索引（HNSW）
index_params = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {"M": 16, "efConstruction": 200}
}
collection.create_index(field_name="embedding", index_params=index_params)

```text

---

---

---

### L052
**分类：** LLM与AI工程
**题目：** 面试官问：常见问题你会怎么回答？
**参考答案：** ### Q1: 向量数据库能替代 MySQL 吗？


```text
不能。它们解决不同的问题:

MySQL: "user_000042 的 on_time_rate 是多少？" → 精确查询 ✅
向量库: "和'深夜高风险'这个概念最相似的文档是？" → 语义搜索 ✅

通常一起用:
  Step 1: 向量库做语义检索（找到相关的知识）
  Step 2: MySQL 做精确查询（找到具体的数据值）
  Step 3: LLM 综合回答

```text
### Q2: 100 万条向量查询需要多快？


```text
硬件: 32GB RAM, 8 核 CPU
算法: HNSW
时间: ~10ms

对比:
  精确搜索: ~500ms（慢 50 倍）
  IVF (100桶): ~30ms
  HNSW: ~5-10ms（最快，推荐）

```text
### Q3: 什么时候需要升级到 Milvus？


```text
Chroma 适合: < 10 万条，单机开发验证
Milvus 适合: > 100 万条，分布式生产
Qdrant 适合: 想用 Docker 解决的中等规模

```text

---

---

### L053
**分类：** LLM与AI工程
**题目：** 请说说主流 LLM API 对比（15min）
**参考答案：** ### 1.1 国内可用的大模型

| 模型 | API 地址 | 价格（百万 token） | 优势 | 场景 |
|------|---------|:---------------:|------|------|
| **DeepSeek V4** | api.deepseek.com | 输入 0.5元 / 输出 2元 | ⭐ 性价比极高，中文强 | 日常开发 |
| **通义千问 Qwen** | dashscope.aliyun.com | 输入 0.8元 / 输出 2元 | 阿里系集成好 | 企业场景 |
| **GLM-4** | open.bigmodel.cn | 输入 0.1元 / 输出 0.1元 | 最便宜，中文好 | 批量任务 |
| **Claude 3.5** | api.anthropic.com | 输入 3元 / 输出 15元 | 推理最强 | 复杂任务 |
| **GPT-4o** | api.openai.com | 输入 5元 / 输出 20元 | 综合最强 | 关键决策 |
| **DeepSeek R1** | api.deepseek.com | 输入 1元 / 输出 4元 | 推理链超强 | 工程分析 |

---

---

---

### L054
**分类：** LLM与AI工程
**题目：** 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的API 调用的四种模式（1h）
**参考答案：** ### 模式 1：基础 Prompt 调用


```python
from openai import OpenAI

# DeepSeek 兼容 OpenAI SDK
client = OpenAI(
    api_key="sk-your-key",
    base_url="https://api.deepseek.com"  # 改 base_url 即可切换模型
)

def chat(prompt: str, model: str = "deepseek-chat",
         temperature: float = 0.0) -> str:
    """
    temperature = 0.0 → 确定性输出（适合代码生成、SQL生成）
    temperature = 0.7 → 创意性输出（适合文案、头脑风暴）
    temperature = 1.0 → 高度随机（适合创意写作）
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一位 SQL 专家。"},  # System Prompt
            {"role": "user", "content": prompt},                    # User Message
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content

```text
### 模式 2：流式输出（Streaming）


```python
def chat_stream(prompt: str):
    """
    流式输出: 一个字一个字显示，而不是等全部生成完。

    适用于: 需要实时显示回复的场景（对话机器人、代码生成）
    不适用于: 需要完整结果再做后续处理的场景
    """
    stream = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        stream=True,  # ← 流式模式
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
            # 每次 yield 一小段文本，前端可以实时渲染

# 使用
for text in chat_stream("写一段 SQL 查询最近 7 天的通过率"):
    print(text, end="", flush=True)

```text
### 模式 3：多轮对话


```python
def multi_turn_chat():
    """
    多轮对话: 保留历史消息，让 LLM 理解上下文。

    关键: messages 列表每次增加一条 user 和 assistant 消息
    注意: 消息数越多 → token 消耗越大 → 注意窗口长度
    """
    messages = [
        {"role": "system",
         "content": "你是风控数据仓库的 AI 助手。"}
    ]

    print("开始对话（输入 'q' 退出）")
    while True:
        user_input = input("\n你: ")
        if user_input.lower() == 'q':
            break

        # 添加用户消息
        messages.append({"role": "user", "content": user_input})

        # 调用 LLM
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.0,
        )

        reply = response.choices[0].message.content
        print(f"AI: {reply}")

        # 添加助手回复（用于下一轮对话的上下文）
        messages.append({"role": "assistant", "content": reply})

        # ★ 重要: 控制消息数量
        if len(messages) > 20:  # 超过 10 轮对话
            # 丢弃最早的消息，但保留 system prompt
            messages = [messages[0]] + messages[-19:]

```text
### 模式 4：Function Calling


```python
# ★ Function Calling = 让 LLM 可以调用你的代码函数
# 这是 Agent 架构的基础 — LLM 通过 Function Calling 操作外部系统

# Step 1: 定义工具函数
def query_data_warehouse(sql: str) -> str:
    """执行 SQL 查询，返回结果。这是调用数据仓库的准入门"""
    import sqlite3
    # 这里是演示，实际连接数据仓库
    conn = sqlite3.connect(":memory:")
    try:
        cursor = conn.execute(sql)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        return f"列名: {columns}\n数据: {results[:10]}"
    except Exception as e:
        return f"SQL 错误: {e}"

def get_user_profile(user_id: str) -> str:
    """获取用户基本信息"""
    return f"用户 {user_id}: 30岁, 月收入 8000, 信用评分 672"


# Step 2: 定义函数 Schema（告诉 LLM 有哪些函数可用）
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_data_warehouse",
            "description": "执行 SQL 查询数据仓库",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL 查询语句"
                    }
                },
                "required": ["sql"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": "获取用户基本信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户 ID"
                    }
                },
                "required": ["user_id"]
            }
        }
    }
]

# Step 3: 请求 LLM 决定是否调用函数
def agent(query: str) -> str:
    """
    Function Calling 流程:
    1. 把用户问题 + tools 定义发给 LLM
    2. LLM 判断: 需要调用函数吗？
    3. 如果要 → LLM 返回函数名 + 参数
    4. 执行函数 → 结果返回 LLM → LLM 综合回答
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": query}],
        tools=tools,           # ← 告诉 LLM 有哪些工具
        tool_choice="auto",    # ← 让 LLM 自己决定是否调用
    )

    message = response.choices[0].message

    # LLM 决定调用函数
    if message.tool_calls:
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            # 执行函数
            if func_name == "query_data_warehouse":
                result = query_data_warehouse(**func_args)
            elif func_name == "get_user_profile":
                result = get_user_profile(**func_args)

            # 把函数结果发给 LLM，让它综合回答
            second_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": query},
                    message,
                    {"role": "tool", "content": result,
                     "tool_call_id": tool_call.id}
                ],
                tools=tools,
            )
            return second_response.choices[0].message.content

    # LLM 没有调用函数，直接回答
    return message.content


# 测试
print(agent("查询 2026-07-01 各渠道通过率"))
print(agent("帮我查一下 user_000042 的基本信息"))

```text

---

---

---

### L055
**分类：** LLM与AI工程
**题目：** 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的输出
**参考答案：** 只输出 SQL 代码，不要任何解释。"""

```text
### 3.2 Few-shot Prompt（少样本学习）


```python
# 给 2-3 个例子比单纯描述好 10 倍
FEW_SHOT_PROMPT = """将自然语言转为 SQL。

例子 1:
  问题: "上周哪个渠道通过率最高？"
  SQL: SELECT channel, AVG(approval_rate) as rate
       FROM ads.ads_model_monitor_daily
       WHERE dt >= '2026-06-30' AND dt <= '2026-07-06'
       GROUP BY channel ORDER BY rate DESC LIMIT 1;

例子 2:
  问题: "近 7 天平均评分是多少？"
  SQL: SELECT AVG(avg_score) FROM ads.ads_model_monitor_daily
       WHERE dt >= '2026-07-02';

现在轮到你了:
  问题: "昨天的总申请数是多少？"
  SQL: """

```text

---

---

---

### L056
**分类：** LLM与AI工程
**题目：** 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的Token 管理与成本控制
**参考答案：** ```python
# Token 计数 — 每条消息的 token 数 = 输入 token + 输出 token

def estimate_cost(prompt_tokens: int, response_tokens: int,
                  model: str = "deepseek-chat") -> float:
    """估算单次 API 调用的成本"""
    prices = {
        "deepseek-chat": {"input": 0.5, "output": 2},   # 元/百万 token
        "gpt-4o":        {"input": 5, "output": 20},
        "claude-3":      {"input": 3, "output": 15},
    }

    p = prices[model]
    input_cost = prompt_tokens / 1_000_000 * p["input"]
    output_cost = response_tokens / 1_000_000 * p["output"]
    return input_cost + output_cost

# 典型 token 消耗（中文）:
# 100 字 ≈ 130 token
# 1 轮对话 ≈ 500-1000 input token
# 1 条 SQL 生成 ≈ 50-100 output token
# 1 天 1000 次 NL2SQL 调用 ≈ 1-2 元（DeepSeek）

```text

---

---

---

### L057
**分类：** LLM与AI工程
**题目：** 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的动手练习
**参考答案：** ```python
"""
练习 1: 实现一个多轮对话的"风控分析师 AI 助手"

要求:
1. 支持连续提问（多轮对话）
2. 当用户问"查数据"时，调用函数生成 SQL 并执行
3. 当用户问"什么是 XXX"时，检索 RAG 知识库
4. 控制上下文长度不超过 10 轮

练习 2: 设计一个 NL2SQL 的 System Prompt

场景: 电商数据仓库
  表: ads.ads_daily_gmv (dt, channel, gmv, order_cnt)
  表: ads.ads_product_rank (dt, product_id, sales, category)

要求: 让用户问"昨天的 GMV""最畅销品类"等，LLM 生成正确的 SQL
"""

```text

---

---

---

### L058
**分类：** LLM与AI工程
**题目：** 面试官问：常见问题你会怎么回答？
**参考答案：** ### Q1: temperature 不同值的效果？


```text
temperature=0.0 → 每次输出完全一样（确定性的）→ SQL 生成 ✅
temperature=0.3 → 稍有变化 → 客服回复 ✅
temperature=0.7 → 富有创意 → 文案生成 ✅
temperature=1.0 → 高度随机 → 创作 ✅

```text
### Q2: System Prompt 和 User Message 有什么区别？


```text
System Prompt:  指导 LLM 行为的"指令" — 通常不被用户看到
User Message:  用户的实际问题

相当于: System = "你是一个 SQL 专家"（角色设定）
         User = "上周通过率是多少？"（具体任务）

好的 System Prompt 是 RAG 和 NL2SQL 成功的一半。

```text

---

---

### L059
**分类：** LLM与AI工程
**题目：** 什么是微调？（20min）
**参考答案：** ### 1.1 预训练 vs 微调


```text
预训练（Pre-training）:
  用海量数据（万亿 token）训练基础能力
  "学会了语法、推理、知识"
  成本: 数百万美元, 需要数千张 GPU
  只有大公司能做

微调（Fine-tuning）:
  用少量领域数据（几千条）调整模型行为
  "学会了信贷风控的术语和规则"
  成本: 几十元, 只需要 1 张消费级 GPU
  个人开发者也能做

```text
### 1.2 什么场景需要微调？


```text
场景 A: 你的项目用 LLM 做如下事 → 需要微调
  - 生成特定格式的 SQL（你的数仓有自己的列名和命名规范）
  - 识别你项目中的特定概念（night_ops_ratio, on_time_rate）
  - 模仿特定的文风（审批拒绝通知函）

场景 B: 你的项目用 RAG 就够了 → 不需要微调
  - LLM 只需回答知识库中已有的内容
  - 不需要控制输出格式
  - 不需要学习新的概念（知识库里都有）

```text
**总结：RAG 解决"知道什么"，微调解决"怎么回答"**。

---

---

---

### L060
**分类：** LLM与AI工程
**题目：** 请讲讲PyTorch 微调：从原理到 LoRA中的PyTorch 基础：训练三板斧（40min）
**参考答案：** ```python
import torch
import torch.nn as nn
import torch.optim as optim

# ═══════════════════════════════════════════
# 一个完整的 PyTorch 训练循环
# ═══════════════════════════════════════════

# Step 1: 定义模型
model = nn.Sequential(
    nn.Linear(10, 64),   # 输入 10 维 → 隐藏层 64 维
    nn.ReLU(),            # 激活函数（引入非线性）
    nn.Linear(64, 2),     # 隐藏层 64 维 → 输出 2 维（二分类）
)
# 参数总量: 10×64 + 64 + 64×2 + 2 = 642 + 128 + 2 = 834 个参数

# Step 2: 定义损失函数和优化器
criterion = nn.CrossEntropyLoss()    # 分类任务的标准损失
optimizer = optim.Adam(model.parameters(), lr=0.001)  # Adam 自适应学习率

# Step 3: 训练循环
def train_one_epoch(model, dataloader, criterion, optimizer):
    model.train()  # 切换到训练模式
    total_loss = 0

    for batch_x, batch_y in dataloader:
        # 前向传播: 计算预测值
        outputs = model(batch_x)           # 模型推断
        loss = criterion(outputs, batch_y)  # 计算损失

        # 反向传播: 计算梯度并更新参数
        optimizer.zero_grad()  # 清零梯度
        loss.backward()         # 计算梯度
        optimizer.step()        # 更新参数

        total_loss += loss.item()

    return total_loss / len(dataloader)

# Step 4: 评估
def evaluate(model, dataloader):
    model.eval()  # 切换到评估模式
    correct = 0
    total = 0

    with torch.no_grad():  # 评估时不需要梯度计算（省显存）
        for batch_x, batch_y in dataloader:
            outputs = model(batch_x)
            _, predicted = torch.max(outputs, 1)
            total += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()

    return correct / total

```text

---

---

---

### L061
**分类：** LLM与AI工程
**题目：** 请讲讲PyTorch 微调：从原理到 LoRA中的LoRA：高效微调（1h）
**参考答案：** ### 3.1 为什么需要 LoRA？


```text
全量微调的问题:
  一个大模型有 70 亿参数（7B）
  每次微调都要更新全部 70 亿参数
  -> 需要巨大显存（24GB+）
  -> 存储多个微调版本（每个版本 14GB）

LoRA 的核心思想:
  不更新原来的 70 亿参数（冻结掉）
  在旁边加一个小型"适配器"（几百万参数）
  只更新适配器

效果:
  微调效果 ≈ 全量微调
  显存需求: 24GB → 8GB
  模型体积: 14GB → 20MB
  切换任务: 只需要换 20MB 的适配器文件

```text
### 3.2 LoRA 原理


```text
原始:
  W (70亿参数矩阵)
  y = W × x  (全量更新)

LoRA:
  W_frozen (70亿参数, 冻结不动)
  + A × B (几十万参数, 可训练)

  y = W_frozen × x + (A × B) × x

  A 的维度: d_in × r
  B 的维度: r × d_out
  r = 8（极小的中间维度）

  为什么 A×B 能模拟大矩阵变化？
  因为参数更新通常是"低秩"的（变化量可以压缩到很小的维度）

```text
### 3.3 使用 HuggingFace PEFT 实现 LoRA 微调


```python
# ── 安装 ──
# pip install transformers peft datasets accelerate bitsandbytes

import torch
from transformers import (
    AutoTokenizer, AutoModelForCausalLM,
    TrainingArguments, Trainer
)
from peft import (
    get_peft_model, LoraConfig, TaskType,
    prepare_model_for_kbit_training
)

# ═══════════════════════════════════════════
# Step 1: 加载基础模型
# ═══════════════════════════════════════════

model_name = "Qwen/Qwen2.5-1.5B-Instruct"  # 1.5B 参数, 消费级显卡能跑

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,   # 半精度 — 省一半显存
    device_map="auto",            # 自动分配 GPU/CPU
)

# ═══════════════════════════════════════════
# Step 2: 配置 LoRA
# ═══════════════════════════════════════════

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,          # 因果语言模型
    r=8,                                       # LoRA 秩（越小越省，越弱）
    lora_alpha=32,                             # 缩放系数
    lora_dropout=0.1,                          # Dropout（防过拟合）
    target_modules=["q_proj", "v_proj"],        # 只微调注意力层的 Q 和 V 矩阵
)

# 冻结原始参数，添加 LoRA 适配器
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# 输出: trainable params: 2.1M || all params: 1.5B || trainable%: 0.14
# 说明: 只更新 0.14% 的参数（210 万 / 15 亿）

# ═══════════════════════════════════════════
# Step 3: 准备训练数据
# ═══════════════════════════════════════════

# 训练数据格式: 指令 + 输入 + 输出
train_data = [
    {
        "instruction": "根据自然语言问题生成 SQL 查询",
        "input": "上周各渠道通过率是多少？",
        "output": "SELECT channel, AVG(approval_rate) FROM ads_model_monitor_daily WHERE dt >= '2026-06-30' AND dt <= '2026-07-06' GROUP BY channel;"
    },
    {
        "instruction": "根据自然语言问题生成 SQL 查询",
        "input": "近7天平均评分是多少？",
        "output": "SELECT AVG(avg_score) FROM ads_model_monitor_daily WHERE dt >= '2026-07-02';"
    },
    # ... 至少 100-500 条这样的数据
]


def format_example(example):
    """构造 Prompt 格式"""
    prompt = f"""指令: {example['instruction']}
输入: {example['input']}
输出: {example['output']}"""
    return tokenizer(prompt, truncation=True, max_length=512,
                     padding="max_length")


# ═══════════════════════════════════════════
# Step 4: 配置训练参数并训练
# ═══════════════════════════════════════════

training_args = TrainingArguments(
    output_dir="./lora_sql_output",           # 模型保存路径
    num_train_epochs=3,                       # 训练轮数
    per_device_train_batch_size=4,            # 批大小（GPU显存决定）
    gradient_accumulation_steps=4,            # 梯度累积（等效 batch=16）
    learning_rate=2e-4,                      # LoRA 学习率（比全量微调大）
    warmup_steps=100,                        # 预热步数
    logging_steps=50,                        # 日志间隔
    save_strategy="epoch",                   # 每轮保存
    fp16=True,                                # 混合精度（省显存）
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
)

# 开始训练
trainer.train()

# ═══════════════════════════════════════════
# Step 5: 保存和推理
# ═══════════════════════════════════════════

# 保存 LoRA 适配器（只有 20MB）
model.save_pretrained("./lora_sql_adapter")

# 推理测试
def generate_sql(question: str) -> str:
    prompt = f"""指令: 根据自然语言问题生成 SQL 查询
输入: {question}
输出:"""

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_new_tokens=128,
        temperature=0.0,     # SQL 不需要创意
        do_sample=False,      # 贪婪解码，确保确定性
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

print(generate_sql("昨天申请总数是多少？"))

```text

---

---

---

### L062
**分类：** LLM与AI工程
**题目：** 请说说LoRA 参数选择指南
**参考答案：** ```text
r（秩）:
  r=4  → 最快，效果最差 → 简单的格式转换
  r=8  → 推荐，效果不错 → 通用场景
  r=16 → 较慢，效果更好 → 需要学习复杂模式
  r=64 → 接近全量微调 → 数据量大（>1000 条）时用

lora_alpha（缩放）:
  建议: lora_alpha = 2 × r
  r=8 → alpha=16
  r=16 → alpha=32

target_modules（微调哪些层）:
  推荐: ["q_proj", "v_proj"]（最小的改动）
  进阶: ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
  → 模块越多，效果越好，显存需求越大

```text

---

---

---

### L063
**分类：** LLM与AI工程
**题目：** 请讲讲PyTorch 微调：从原理到 LoRA中的动手练习
**参考答案：** ```python
"""
练习 1: 用 LoRA 微调一个小模型生成 SQL

步骤:
1. 使用 Qwen2.5-0.5B（0.5B 参数，单 CPU 也能跑）
2. 准备 50 条 NL2SQL 训练数据（参考项目的表结构）
3. 配置 LoRA (r=8)
4. 训练 3 轮
5. 对比微调前后的 SQL 生成质量

练习 2: 判断你的项目需要微调还是 RAG

填写下表:
| 场景 | 用 RAG 还是微调？ | 理由 |
|------|----------------|------|
| LLM 需要知道你项目特有的概念 | | |
| LLM 需要控制输出格式（JSON/SQL） | | |
| 知识库会频繁更新 | | |
| 回答需要非常精确（不能有幻觉） | | |
"""

```text

---

---

---

### L064
**分类：** LLM与AI工程
**题目：** 面试官问：常见问题你会怎么回答？
**参考答案：** ### Q1: 微调后模型会忘记原来的能力吗？


```text
会，这叫"灾难性遗忘"。

解决方案:
1. 混合训练: 在领域数据中混入 20% 通用数据
2. LoRA: 灾难性遗忘比全量微调轻很多（原始参数没变）
3. 学习率不要太大: 2e-4 是 LoRA 的安全值

```text
### Q2: 消费级显卡（RTX 3060 12GB）能微调多大的模型？


```text
Qwen2.5-1.5B  ← ✅ 12GB 显存足够
Qwen2.5-3B    ← ✅ 需要量化 + LoRA
Qwen2.5-7B    ← ⚠️ 需要量化 + LoRA + 梯度累积
LLaMA-13B     ← ❌ 显存不够

建议从 1.5B 开始尝试，跑通流程后再上更大的模型。

```text

---

---

### L065
**分类：** LLM与AI工程
**题目：** 为什么需要 LangChain（20min）
**参考答案：** ### 1.1 没有框架时的问题


```python
# 手写代码调 LLM — 看起来很简单，直到你需要:
# 1. 多轮对话维护上下文
# 2. 调用多个函数
# 3. 错误重试
# 4. 异步调用
# 5. 日志追踪

# 手写代码开始变得混乱...
def my_agent(query):
    response = llm(query)
    if has_tool_call(response):
        result = tool(response)
        response = llm(query + result)
    # 每次都重复这个模式
    # 没有标准的结构

```text
### 1.2 LangChain 解决了什么


```text
LangChain 提供:
1. 标准化接口 — 所有 LLM（OpenAI/DeepSeek/Claude）用同一套 API
2. 链式编程 — 像搭积木一样组合功能
3. 内置工具 — 向量检索、SQL查询、网页搜索等
4. 可观测性 — LangSmith 追踪执行路径

LangChain 不是必须的，但它是目前最主流的 LLM 应用框架（JD 出现率 71%）

```text

---

---

---

### L066
**分类：** LLM与AI工程
**题目：** 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangChain **核心概念**（40min）
**参考答案：** ### 2.1 Chat Models


```python
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatDeepSeek

# 统一接口: 不管用哪个 LLM，代码结构完全一样
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
    api_key="sk-xxx",
)

# 改成 DeepSeek: 只换类名和 base_url
llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0.0,
    api_key="sk-xxx",
    base_url="https://api.deepseek.com",
)

# 调用
response = llm.invoke("什么是 night_ops_ratio_30d？")
print(response.content)

```text
### 2.2 Prompt Templates


```python
from langchain.prompts import ChatPromptTemplate

# 比普通字符串拼接好的地方:
# 1. 自动变量注入
# 2. 支持 System/User/Assistant 多角色
# 3. 可以串联

# 基础模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个 SQL 专家。根据以下表结构生成 SQL: {schema}"),
    ("human", "{question}"),
])

# 使用: 自动填充变量
messages = prompt.invoke({
    "schema": "表 ads_model_monitor_daily: channel STRING, approval_rate DOUBLE",
    "question": "上周通过率最高的渠道是什么？",
})

```text
### 2.3 Chains（链）


```python
from langchain.chains import LLMChain

# Chain = Prompt + LLM 的组合
# 这是 LangChain 最基础的原子单位

llm = ChatDeepSeek(model="deepseek-chat", temperature=0.0)

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个 SQL 专家。表结构: {schema}"),
    ("human", "问题: {question}\n生成 SQL:"),
])

sql_chain = LLMChain(
    llm=llm,
    prompt=prompt,
)

# 调用 chain
result = sql_chain.invoke({
    "schema": "ads_model_monitor_daily(channel, approval_rate, dt)",
    "question": "上周哪个渠道通过率最高？",
})
print(result["text"])  # 输出: SELECT channel, AVG(approval_rate) ...


# Sequential Chain（串行链）— 一个链的输出是下一个链的输入
from langchain.chains import SequentialChain

# Chain 1: 生成 SQL
sql_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个 SQL 专家。"),
    ("human", "问题: {question}\n生成 SQL:"),
])
chain_sql = LLMChain(llm=llm, prompt=sql_prompt, output_key="sql")

# Chain 2: 解释 SQL
explain_prompt = ChatPromptTemplate.from_messages([
    ("human", "用中文解释这段 SQL 做了什么:\n{sql}"),
])
chain_explain = LLMChain(llm=llm, prompt=explain_prompt, output_key="explanation")

# 串起来: 用户问问题 → 生成 SQL → 解释 SQL
full_chain = SequentialChain(
    chains=[chain_sql, chain_explain],
    input_variables=["question"],
    output_variables=["sql", "explanation"],
)

result = full_chain.invoke({"question": "上周通过率最高渠道？"})
print(f"SQL: {result['sql']}")
print(f"解释: {result['explanation']}")

```text
### 2.4 Tools（工具调用）


```python
from langchain.tools import tool

# @tool 装饰器: 把 Python 函数变成 LLM 可调用的工具
@tool
def query_warehouse(sql: str) -> str:
    """
    执行 SQL 查询数据仓库。参数: sql — SQL 查询语句
    """
    # 这里是简化实现
    return f"已执行: {sql}"

# 多种内置工具
from langchain_community.tools import DuckDuckGoSearchRun

# 把工具绑定到 LLM
llm_with_tools = llm.bind_tools([query_warehouse, DuckDuckGoSearchRun()])

```text
### 2.5 Agents（智能体）


```python
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate

# Agent = LLM + Tools + 循环决策
# 1. LLM 决定是否调用工具
# 2. 如果调用，执行工具，结果返回给 LLM
# 3. LLM 根据结果决定下一步（继续调用还是直接回答）

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是风控数据仓库的 AI 助手。"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),  # ← 中间步骤
])

agent = create_tool_calling_agent(
    llm=llm_with_tools,
    tools=[query_warehouse],
    prompt=prompt,
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=[query_warehouse],
    verbose=True,  # ← 打印每一步
)

# 执行
agent_executor.invoke({
    "input": "查一下 2026-07-01 各渠道通过率"
})
# 输出:
# > 调用 query_warehouse(sql="SELECT channel, approval_rate ...")
# > 结果: [('APP_IOS', 0.723), ('APP_ANDROID', 0.651)]
# > 回答: APP_IOS 渠道通过率最高，为 72.3%...

```text

---

---

---

### L067
**分类：** LLM与AI工程
**题目：** 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangGraph：状态机工作流（1h）
**参考答案：** ### 3.1 Chain vs Graph 的区别


```text
Chain (串行): A → B → C → D
  固定的、线性的执行路径
  不能分支、不能循环、不能等待

Graph (有向图):
  A → [条件] → [B → C → D]
            → [E → F] → G → ...
  可以分支（条件路由）
  可以循环（状态机）
  可以等待人工输入（异步）

```text
**LangGraph 用 StateGraph 来定义有状态的工作流。**

### 3.2 **核心概念**


```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

# ═══════════════════════════════════════════
# 概念 1: State（状态）
#   TypedDict — 定义工作流中传递的数据结构
# ═══════════════════════════════════════════

class ApprovalState(TypedDict):
    """信贷审批工作流的状态 — 在各个节点之间传递"""
    user_id: str
    score: int
    decision: str      # APPROVE / REJECT / MANUAL_REVIEW
    reason: str
    rejected: bool


# ═══════════════════════════════════════════
# 概念 2: Nodes（节点）
#   每个节点是一个函数: 输入 State → 修改 State → 输出
# ═══════════════════════════════════════════

def rule_check(state: ApprovalState) -> ApprovalState:
    """节点1: 规则引擎检查"""
    print(f"[规则引擎] 检查 {state['user_id']}")
    state["rejected"] = False
    return state

def model_score(state: ApprovalState) -> ApprovalState:
    """节点2: 模型评分"""
    state["score"] = 672
    return state


# ═══════════════════════════════════════════
# 概念 3: Edges（边）
#   条件边: 根据 State 决定下一步
#   普通边: 固定走到下一个节点
# ═══════════════════════════════════════════

def route_after_rules(state: ApprovalState) -> Literal["rejected", "scoring"]:
    """
    条件边: 规则检查后决定去哪
    - 如果命中硬拒绝 → 去 rejection 节点
    - 否则 → 去模型评分节点
    """
    if state.get("rejected"):
        return "rejected"
    return "scoring"


# ═══════════════════════════════════════════
# 构建图
# ═══════════════════════════════════════════

workflow = StateGraph(ApprovalState)

# 注册节点
workflow.add_node("check", rule_check)
workflow.add_node("scoring", model_score)
workflow.add_node("rejection", lambda s: s)

# 设置入口
workflow.set_entry_point("check")

# 设置边
workflow.add_conditional_edges(
    "check",
    route_after_rules,
    {"rejected": "rejection", "scoring": "scoring"}
)
workflow.add_edge("scoring", END)
workflow.add_edge("rejection", END)

# 编译
app = workflow.compile()

```text
### 3.3 实战：信贷审批完整工作流


```python
"""
本例实现信贷审批的完整状态机:

rule_check ──REJECT──→ rejection_letter → END
    │
    └──PASS──→ model_score ──APPROVE──→ disburse → END
                    │
                    ├──MANUAL_REVIEW──→ request_docs → 【等待用户上传】→ model_score
                    └──REJECT──→ rejection_letter → END
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal
import json


# ── 状态定义 ──
class CreditState(TypedDict):
    user_id: str
    features: dict
    rule_hits: list[str]
    score: int
    decision: str
    reason: str
    required_docs: list[str]


# ── 节点函数 ──

def rule_check(state: CreditState) -> CreditState:
    """节点1: 规则引擎检查 — 需要实现短路逻辑"""
    hits = []
    if state["features"].get("in_blacklist"):
        hits.append("BLACKLIST_HIT")
        state["decision"] = "REJECT"
        state["reason"] = "命中黑名单"
    state["rule_hits"] = hits
    print(f"  [规则] 命中: {hits}")
    return state


def model_scoring(state: CreditState) -> CreditState:
    """节点2: 模型评分"""
    # 模拟 XGBoost 推理
    prob = 0.3  # 违约概率
    score = int(600 + 50 / 0.693 * (1 - prob) / prob)  # 简化评分公式
    state["score"] = score
    print(f"  [模型] 评分: {score}")
    return state


def request_docs(state: CreditState) -> CreditState:
    """节点3 (LLM): 生成需要补充的材料清单"""
    docs = {
        "收入不稳定": "收入证明、银行流水",
        "多头借贷": "现有贷款合同明细",
        "设备异常": "人脸识别视频验证",
    }
    # 根据规则命中情况生成
    state["required_docs"] = [docs.get(state["reason"], "身份证明")]
    print(f"  [LLM] 请补充材料: {state['required_docs']}")
    return state


def rejection_letter(state: CreditState) -> CreditState:
    """节点4 (LLM): 生成拒绝通知"""
    letter = f"""尊敬的{state['user_id']}:
    很抱歉，您的贷款申请未通过。
    原因: {state['reason']}
    您有权在 15 个工作日内申请人工复核。"""
    state["reason"] = letter
    print(f"  [LLM] 已生成拒绝函")
    return state


def disburse(state: CreditState) -> CreditState:
    """节点5: 放款"""
    print(f"  [放款] 已向 {state['user_id']} 放款 ¥5,000")
    return state


# ── 路由函数 ──

def route_after_rules(state) -> Literal["REJECT", "PROCEED"]:
    if state["decision"] == "REJECT":
        return "REJECT"
    return "PROCEED"


def route_after_scoring(state) -> Literal["APPROVE", "MANUAL_REVIEW", "REJECT"]:
    score = state["score"]
    if score >= 600:
        return "APPROVE"
    elif score >= 500:
        return "MANUAL_REVIEW"
    else:
        return "REJECT"


# ── 构建图 ──

def build_credit_workflow():
    graph = StateGraph(CreditState)

    graph.add_node("rule_check", rule_check)
    graph.add_node("model_scoring", model_scoring)
    graph.add_node("request_docs", request_docs)
    graph.add_node("rejection_letter", rejection_letter)
    graph.add_node("disburse", disburse)

    # 条件边: 规则引擎 → 拒绝/继续
    graph.add_conditional_edges(
        "rule_check",
        route_after_rules,
        {
            "REJECT": "rejection_letter",
            "PROCEED": "model_scoring"
        }
    )

    # 条件边: 模型评分 → 通过/人工/拒绝
    graph.add_conditional_edges(
        "model_scoring",
        route_after_scoring,
        {
            "APPROVE": "disburse",
            "MANUAL_REVIEW": "request_docs",
            "REJECT": "rejection_letter"
        }
    )

    graph.add_edge("disburse", END)
    graph.add_edge("rejection_letter", END)
    graph.add_edge("request_docs", END)  # 等待用户上传 — 异步恢复

    graph.set_entry_point("rule_check")
    return graph.compile()


# ── 执行 ──
workflow = build_credit_workflow()

# 场景 1: 正常用户
result = workflow.invoke({
    "user_id": "user_000042",
    "features": {"in_blacklist": False, "age": 30, "income": 8000},
    "rule_hits": [],
    "score": 0,
    "decision": "",
    "reason": "",
    "required_docs": [],
})
print(f"决策: {result['decision']}")

# 场景 2: 黑名单用户
result = workflow.invoke({
    "user_id": "user_000999",
    "features": {"in_blacklist": True, "age": 30, "income": 8000},
    "rule_hits": [],
    "score": 0,
    "decision": "",
    "reason": "",
    "required_docs": [],
})
print(f"决策: {result['decision']} — 原因: {result['reason'][:30]}...")

```text

---

---

---

### L068
**分类：** LLM与AI工程
**题目：** 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangGraph 的进阶功能
**参考答案：** ### 4.1 条件循环（human-in-the-loop）


```python
# 当用户补充材料时，工作流需要恢复
# LangGraph 的 checkpointer 可以自动保存状态

from langgraph.checkpoint.memory import MemorySaver

# 使用持久化存储
checkpointer = MemorySaver()

workflow = build_credit_workflow()
app = workflow.compile(checkpointer=checkpointer)

# 第一次执行: 暂停在 request_docs 等待用户上传
config = {"configurable": {"thread_id": "user_000042_session"}}
result = app.invoke(input_data, config=config)

# 用户上传材料后: 恢复执行
# update_state 从上次暂停处继续
app.update_state(config, {"required_docs": []})
result = app.invoke(None, config=config)

```text
### 4.2 可视化


```python
# 生成工作流图
from IPython.display import Image, display

display(Image(workflow.get_graph().draw_mermaid_png()))
# → 直接看到审批流程图

```text

---

---

---

### L069
**分类：** LLM与AI工程
**题目：** 请说说LangChain vs LangGraph 选择指南
**参考答案：** | 场景 | 用 LangChain | 用 LangGraph |
|------|:----------:|:----------:|
| 简单的 Prompt → LLM → 输出 | ✅ | ❌ 杀鸡用牛刀 |
| 多步链式调用（A→B→C） | ✅ | 也✅ |
| 有分支的路由（if-else 决策） | ❌ | ✅ |
| 循环直到条件满足 | ❌ | ✅ |
| 等待人工输入 | ❌ | ✅ |
| 复杂状态机 | ❌ | ✅ |


```text
一句话: 顺序执行用 Chain，条件分支用 Graph，人工干预用 Graph + Checkpointer。

```text

---

---

---

### L070
**分类：** LLM与AI工程
**题目：** 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的动手练习（1h）
**参考答案：** ```python
"""
练习 1: 用 LangChain 实现 NL2SQL Agent

要求:
1. 定义两个工具: query_warehouse(sql), get_schema(table_name)
2. Agent 先获取 Schema → 再生成 SQL → 执行 SQL → 返回结果
3. 支持"查一下 2026-07-01 各渠道通过率"这类问题

练习 2: 用 LangGraph 实现客服质检工作流

状态:
  Text → Classify → [投诉] → RouteToAgent → LLM生成摘要 → END
                    [简单问题] → AutoReply → END
                    [复杂问题] → Escalate → END
"""

```text

---

---

---

### L071
**分类：** LLM与AI工程
**题目：** 面试官问：常见问题你会怎么回答？
**参考答案：** ### Q1: LangChain 值得学吗？还是直接用 Python 调 API 更好？


```text
如果只是调 LLM API（NL2SQL、聊天）→ 直接调 API 更简单，不需要 LangChain
如果需要工具调用（Agent）→ LangChain 让代码结构更清晰
如果面试要求（JD 出现率 71%）→ 值得学

最佳实践: 学会 LanfgChain 的概念，小项目手写，大项目用框架。

```text
### Q2: LangGraph 和 FastAPI 的异步兼容吗？


```python
# LangGraph 原生支持 async
result = await app.ainvoke(input_data)

# 可以集成到 FastAPI
from fastapi import FastAPI

fastapi_app = FastAPI()
workflow = build_credit_workflow()

@fastapi_app.post("/credit/apply")
async def credit_apply(user_id: str):
    result = await workflow.ainvoke({
        "user_id": user_id,
        "features": {"in_blacklist": False},
    })
    return {"decision": result["decision"]}

```text

---

---

### L072
**分类：** 信贷风控建模
**题目：** 请讲讲XGBoost 训练 + 模型评估完整指南中的XGBoost **核心概念**（30min）
**参考答案：** ### 1.1 为什么用 XGBoost 而不是深度学习？


```text
数据量 < 10 万条 → XGBoost 效果 > 深度学习
数据量 > 100 万条 → 深度学习才有优势
信贷风控（几万条样本）→ XGBoost 是行业标准

核心优势:
1. 自带正则化 — 不容易过拟合
2. 处理缺失值 — 自动学习缺失值方向
3. 特征重要性 — 可解释性强
4. 训练速度快 — 不需要 GPU

```text
### 1.2 XGBoost 的核心参数


```python
# 项目中使用的参数 (src/models/trainer.py 第149-161行)

params = {
    'objective': 'binary:logistic',     # 二分类任务
    'eval_metric': 'auc',               # 评估指标
    'max_depth': 5,                     # 树深度 — 越大越容易过拟合
    'learning_rate': 0.05,              # 学习率 — 越小越需要更多树
    'n_estimators': 500,                # 树的数量
    'subsample': 0.8,                   # 行采样 — 防过拟合
    'colsample_bytree': 0.8,            # 列采样 — 防过拟合
    'min_child_weight': 10,             # 叶子节点最小权重 — 防过拟合
    'reg_alpha': 0.1,                   # L1 正则化
    'reg_lambda': 1.0,                  # L2 正则化
    'early_stopping_rounds': 50,        # 早停
    'scale_pos_weight': n_neg / n_pos,  # 样本不平衡处理
}

```text
**参数选择逻辑**：


```text
max_depth=5 而不是 10:
  树太深 → 模型记住噪声 → 过拟合
  树太浅 → 模型学不到模式 → 欠拟合
  5 是信贷风控的经验值

scale_pos_weight = 负样本数 / 正样本数:
  坏样本 10%，好样本 90% → weight = 9
  让模型更关注"少数派"（坏人）
  不设这个参数 → 模型会倾向于预测所有人都是好人（因为 90% 是对的）

```text

---

---

---

### L073
**分类：** 信贷风控建模
**题目：** 请详细讲解完整训练流程（1h）
**参考答案：** ### 2.1 项目中的训练代码

打开项目 `src/models/trainer.py` 第 126-224 行：


```python
class ModelTrainer:
    def train_xgboost(self, X_train, y_train, X_test, y_test, feature_names):

        # Step 1: 样本不平衡处理
        n_pos = (y_train == 1).sum()
        n_neg = (y_train == 0).sum()
        params['scale_pos_weight'] = n_neg / n_pos if n_pos > 0 else 1

        # Step 2: 训练
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train,
                  eval_set=[(X_test, y_test)],  # 用测试集做早停
                  verbose=False)

        # Step 3: 预测
        y_train_pred = model.predict_proba(X_train)[:, 1]
        y_test_pred = model.predict_proba(X_test)[:, 1]

        # Step 4: 评估
        report = self.evaluator.evaluate(
            y_train, y_train_pred, y_test, y_test_pred
        )

        return ModelWrapper(...), report

```text
**早停（Early Stopping）的工作原理**：


```text
训练第 1 轮: train AUC=0.65, test AUC=0.62
训练第 10 轮: train AUC=0.80, test AUC=0.74
训练第 50 轮: train AUC=0.95, test AUC=0.72  ← test AUC 开始下降
训练第 60 轮: train AUC=0.96, test AUC=0.71  ← 连续 10 轮没提升

early_stopping_rounds=10:
  发现 test AUC 连续 10 轮不增长 → 停止训练
  回滚到第 50 轮的模型（test AUC 最高那次）

```text
### 2.2 动手练习：手写完整训练流程


```python
import xgboost as xgb
import numpy as np
from sklearn.model_selection import train_test_split

# 生成模拟数据
np.random.seed(42)
n_samples = 5000
X = np.random.randn(n_samples, 10)
y = (X[:, 0] + X[:, 1] * 2 + np.random.randn(n_samples) * 0.5 > 0.5).astype(int)

# 切分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42
)

# ★ 参考答案
params = {
    'objective': 'binary:logistic',
    'eval_metric': 'auc',
    'max_depth': 5,
    'learning_rate': 0.05,
    'n_estimators': 500,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'random_state': 42,
}
n_pos = (y_train == 1).sum()
n_neg = (y_train == 0).sum()
params['scale_pos_weight'] = n_neg / n_pos if n_pos > 0 else 1

model = xgb.XGBClassifier(**params)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

y_train_pred = model.predict_proba(X_train)[:, 1]
y_test_pred = model.predict_proba(X_test)[:, 1]

from sklearn.metrics import roc_auc_score
print(f"AUC train: {roc_auc_score(y_train, y_train_pred):.4f}")
print(f"AUC test:  {roc_auc_score(y_test, y_test_pred):.4f}")

```text

---

---

---

### L074
**分类：** 信贷风控建模
**题目：** 请讲讲XGBoost 训练 + 模型评估完整指南中的模型评估指标体系（1h）
**参考答案：** ### 3.1 AUC — 排序能力


```python
def calculate_auc(y_true, y_pred):
    """
    AUC = 随机抽一个正样本一个负样本，模型把正样本排前面的概率。

    AUC = 0.5 → 和扔硬币一样
    AUC = 0.7 → 70% 的概率能把好坏分开
    AUC = 1.0 → 完美

    信贷标准: AUC >= 0.65 才能上线
    """
    from sklearn.metrics import roc_auc_score
    return roc_auc_score(y_true, y_pred)

```text
### 3.2 KS — 区分能力（必须能手写）


```python
def calculate_ks(y_true, y_pred):
    """
    KS = max(|好样本累积比例 - 坏样本累积比例|)

    为什么 KS 和 AUC 都要看？
    - AUC 衡量"整体"排序能力
    - KS 衡量"在最佳切分点"的区分能力
    - 高 AUC + 低 KS → 排序对但分不开（阈值附近模糊）

    信贷标准: KS >= 0.25
    """
    order = np.argsort(y_pred)[::-1]        # 按预测概率降序排
    y_sorted = y_true[order]

    n_pos = (y_true == 1).sum()
    n_neg = (y_true == 0).sum()

    cum_pos = np.cumsum(y_sorted == 1) / n_pos  # 坏样本累积
    cum_neg = np.cumsum(y_sorted == 0) / n_neg  # 好样本累积

    return float(np.max(np.abs(cum_pos - cum_neg)))

```text
### 3.3 PSI — 分布稳定性


```python
def calculate_psi(expected, actual, bins=10):
    """
    PSI = Σ (actual_i - expected_i) × ln(actual_i / expected_i)

    PSI < 0.1 → 稳定
    PSI 0.1-0.25 → 轻微漂移，关注
    PSI > 0.25 → 严重漂移，触发重训

    为什么用训练集的分位做分箱边界？
    → 保持分箱边界固定，才能比较"线上 vs 训练"的分布差异
    """
    boundaries = np.percentile(expected, np.linspace(0, 100, bins + 1))
    ep = np.histogram(expected, bins=boundaries)[0] / len(expected)
    ap = np.histogram(actual, bins=boundaries)[0] / len(actual)

    ep = np.clip(ep, 1e-6, 1)
    ap = np.clip(ap, 1e-6, 1)
    return float(np.sum((ap - ep) * np.log(ap / ep)))

```text
### 3.4 Lift 分析


```python
def calculate_lift(y_true, y_pred, bins=10):
    """
    Lift = 该分箱的坏账率 / 整体平均坏账率

    理想模型: 按预测概率降序分 10 箱
      Bin 0（最高危）: lift > 2.0  → 坏账率是平均的 2 倍
      Bin 9（最低危）: lift < 0.5  → 坏账率不到平均的一半

    如果 lift 曲线单调递减 → 模型排序正确
    如果 lift 曲线没有单调性 → 模型有问题
    """
    df = pd.DataFrame({'prob': y_pred, 'true': y_true})
    df = df.sort_values('prob', ascending=False)
    df['bin'] = pd.qcut(df['prob'], q=bins, labels=False)

    avg_bad_rate = y_true.mean()
    lift_table = df.groupby('bin').agg(
        bad_rate=('true', 'mean'),
        count=('true', 'count'),
    ).reset_index()
    lift_table['lift'] = lift_table['bad_rate'] / avg_bad_rate

    return lift_table

```text

---

---

---

### L075
**分类：** 信贷风控建模
**题目：** 请讲讲XGBoost 训练 + 模型评估完整指南中的动手练习：完整训练+评估（1.5h）
**参考答案：** ```python
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
import xgboost as xgb

# 生成模拟数据（5 个特征，其中 2 个有预测力）
np.random.seed(42)
n = 10000
X = pd.DataFrame({
    'feature_0': np.random.randn(n),
    'feature_1': np.random.randn(n),
    'feature_2': np.random.choice(['A', 'B', 'C'], n),
    'feature_3': np.random.randn(n),
    'feature_4': np.random.randn(n),
})
# label = feature_0 + feature_1*2 + 噪声
y = (X['feature_0'] + X['feature_1'] * 2 + np.random.randn(n) * 0.8 > 0).astype(int)

# 处理类别特征
X = pd.get_dummies(X, columns=['feature_2'])

# TODO: 完成以下步骤
# 1. 按 70/30 切分（注意保持标签分布一致 — stratify=y）
# 2. 训练 XGBoost（参考项目参数，含 scale_pos_weight 和 early_stopping）
# 3. 计算 train 和 test 的 AUC
# 4. 计算 KS
# 5. 计算 PSI
# 6. 绘制 Lift 表
# 7. 输出: 模型是否满足上线标准？

# ★ 参考答案
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

n_pos = (y_train == 1).sum()
params['scale_pos_weight'] = (y_train == 0).sum() / n_pos if n_pos > 0 else 1
model = xgb.XGBClassifier(**params)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

y_train_pred = model.predict_proba(X_train)[:, 1]
y_test_pred = model.predict_proba(X_test)[:, 1]

from sklearn.metrics import roc_auc_score
auc_train = roc_auc_score(y_train, y_train_pred)
auc_test = roc_auc_score(y_test, y_test_pred)

order = np.argsort(y_test_pred)[::-1]
y_sorted = y_test[order]
n_pos_test = (y_test == 1).sum()
cum_pos = np.cumsum(y_sorted == 1) / n_pos_test
cum_neg = np.cumsum(y_sorted == 0) / (y_test == 0).sum()
ks = float(np.max(np.abs(cum_pos - cum_neg)))

boundaries = np.percentile(y_train_pred, np.linspace(0, 100, 11))
ep = np.histogram(y_train_pred, bins=boundaries)[0] / len(y_train_pred)
ap = np.histogram(y_test_pred, bins=boundaries)[0] / len(y_test_pred)
ep = np.clip(ep, 1e-6, 1); ap = np.clip(ap, 1e-6, 1)
psi = float(np.sum((ap - ep) * np.log(ap / ep)))

print(f"AUC train: {auc_train:.4f}, AUC test: {auc_test:.4f}")
print(f"KS: {ks:.4f} {'✅' if ks >= 0.25 else '❌'} (需≥0.25)")
print(f"PSI: {psi:.4f} {'✅' if psi < 0.25 else '❌'} (需<0.25)")
print(f"Overfit gap: {auc_train - auc_test:.4f} {'✅' if auc_train - auc_test < 0.05 else '❌'} (需<0.05)")
print(f"上线: {'✅ 通过' if ks >= 0.25 and psi < 0.25 else '❌ 不达标'}")

```text

---

---

---

### L076
**分类：** 信贷风控建模
**题目：** 面试官问：常见问题你会怎么回答？
**参考答案：** ### Q1: 为什么 train AUC=0.99, test AUC=0.47？


```text
典型过拟合:
- 数据量太少 → 模型记住了噪声
- 树太深（max_depth=10）→ 模型过度拟合
- 缺少正则化（reg_alpha/reg_lambda=0）
- 没有早停

解决方案:
- 增加数据量
- 降低 max_depth（3-6）
- 增加正则化参数
- 开启 early_stopping
- 增加 subsample/colsample

```text
### Q2: scale_pos_weight 怎么算？


```text
正样本（坏人）: 100 条
负样本（好人）: 900 条
scale_pos_weight = 900 / 100 = 9.0

含义: 预测错一个坏人的惩罚是预测错一个好人的 9 倍
      模型会更努力地去识别坏人

注意: 如果设太大（比如 50），模型会把所有人都预测成坏人
      如果设太小（比如 1），模型会忽视坏人

```text
### Q3: 特征工程重要还是模型调参重要？


```text
结论: 特征工程 >>> 模型调参

有一个经典经验:
  好的特征 + 默认参数 → 效果很好
  差的特征 + 最优调参 → 效果很差

所以项目中的 DWS 宽表设计（17 个特征、WOE/IV 筛选）
比 XGBoost 的超参调优重要得多。

```text

---

---

### L077
**分类：** 信贷风控建模
**题目：** 为什么需要模型训练？
**参考答案：** **核心原因**：从历史数据中学习规律，量化用户的违约概率或响应概率，并把它固化为可自动执行的打分函数。  
在信贷场景中，模型的价值在于：

1. **量化风险**：回答“该用户未来30天逾期的概率是多少？”  
2. **自动化决策**：替代人工审批，实现毫秒级授信。  
3. **动态调整**：随着市场环境、用户客群的变化，模型需要持续更新，否则会衰减。  
4. **合规与解释**：必须能输出每个特征对决策的贡献（如 WOE、SHAP），以满足监管要求。

训练阶段的目的，就是找到一组**从历史数据中归纳出的、在未来依然成立的映射关系** 
\( f(X) \rightarrow y \)，其中 \( X \) 是审批时能拿到的特征，\( y \) 是还款表现（好/坏）。

---

---

---

### L078
**分类：** 信贷风控建模
**题目：** 模型训练怎么做：全流程拆解
**参考答案：** 以下是生产级训练的标准化步骤，每一步都服务于“防泄漏、保稳定、可追溯”的原则。

### 1. 样本定义与构建（最重要的一步）

**样本 = 特征矩阵 + 标签**，且严格满足时序约束。

#### 定义观察期与表现期
- **观察期**：收集特征的时间窗口。例如，以申请日为锚点，取申请日之前 30 天至 12 个月的特征。
- **表现期**：从申请日（或放款日）开始，往后追踪标签的时间窗口。例如，贷款是否在放款后 30 天内出现逾期（坏样本）或正常还款（好样本）。
- **标签时间戳**：表现期结束的那一天，作为标签的“事件时间”。

**例子**：  
申请日 = 2024-01-15，标签为“M3+ 逾期”，表现期 90 天。  
标签时间戳 = 2024-04-15。  
特征只能使用 ≤ 2024-01-15 的数据快照，绝不能使用 2024-01-16 之后的信息。

#### Point-in-Time (PIT) 拼接
使用 Feast 或手动 SQL 窗口函数，确保每个样本的特征取值是**标签时间点之前的最新值**，做到时序正确。

**代码示例（Spark SQL 伪代码）**：

```sql
SELECT 
    l.user_id, l.apply_id, l.label, l.label_time,
    f.total_orders_30d,
    f.avg_repay_amount,
    ...
FROM labels l
LEFT JOIN feature_view f
  ON l.user_id = f.user_id
  AND f.feature_timestamp <= l.label_time
  AND f.feature_timestamp > l.label_time - INTERVAL 90 DAYS  -- 仅取最近特征
WHERE l.label_time BETWEEN '2024-01-01' AND '2024-06-30'
QUALIFY ROW_NUMBER() OVER (PARTITION BY l.apply_id ORDER BY f.feature_timestamp DESC) = 1

```text
这样保证每个标签只匹配最近的一条历史特征，完全消除泄漏。

### 2. 特征工程与筛选

**特征必须满足：**
- 稳定性：通过 PSI 检验，特征分布不能随时间剧烈漂移。
- 可解释性：尽量使用业务含义清晰的变量（收入、负债比、多头借贷次数），避免太复杂的匿名特征。
- 低缺失率：缺失值超过 50% 的特征通常不采用，或单独分箱处理。

**常用特征类型举例：**
- 基础画像：年龄、性别、学历、婚姻状况、地域。
- 行为特征：近 7/30/90 天登录次数、夜间操作占比、申请被拒次数。
- 征信衍生：信用分、总负债余额、信用卡使用率、历史逾期次数（来自征信报告脱敏后的变量）。
- 设备指纹：设备越狱标志、模拟器标志、IP 归属地变化频次。

**特征分箱与 WOE 编码**（评分卡模型核心）：
对于逻辑回归评分卡，连续变量会被分箱，计算每个箱的 Weight of Evidence：
\[
WOE = \ln\left(\frac{\text{坏客户占比}}{\text{好客户占比}}\right)
\]
这使得模型输出具有极强的解释性，且能自动处理异常值和单调性。

### 3. 训练/验证/测试集划分（按时间）

**严禁随机分割**，必须按时间切分，模拟真实上线情况。

- **训练集**：2024年1月 - 2024年3月的样本。
- **验证集**：2024年4月样本（用于调参）。
- **测试集**：2024年5月样本（只评估一次，最终报告）。

这样划分后，如果测试集 AUC 远低于训练集，说明模型泛化差或时间漂移严重。

### 4. 模型选择与训练

**金融信贷常用模型：**

| 模型 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **逻辑回归（评分卡）** | 强可解释、稳定性好、符合监管 | 需要大量特征工程，非线性能力弱 | 主风控模型（A卡、B卡） |
| **XGBoost/LightGBM** | 非线性能力强、精度高、能自动学习交互 | 可解释性稍弱（需 SHAP 辅助），容易过拟合 | 反欺诈、精细化额度模型 |
| **决策规则（if-else）** | 极快、完全透明 | 覆盖度有限 | 黑名单、硬规则 |

**训练流程示例（XGBoost 代码）：**

```python
import xgboost as xgb
import mlflow

# 数据已按时间切分，且无泄漏
dtrain = xgb.DMatrix(X_train, label=y_train)
dvalid = xgb.DMatrix(X_valid, label=y_valid)

params = {
    'objective': 'binary:logistic',
    'eval_metric': 'auc',
    'max_depth': 5,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'min_child_weight': 10,
    'scale_pos_weight': neg_count / pos_count  # 处理样本不平衡
}

evals = [(dtrain, 'train'), (dvalid, 'eval')]
model = xgb.train(params, dtrain, num_boost_round=200,
                  evals=evals, early_stopping_rounds=20)

# 使用 MLflow 追踪
mlflow.log_params(params)
mlflow.log_metric('test_auc', test_auc)
mlflow.xgboost.log_model(model, 'model')

```text
### 5. 模型评估（不仅仅是 AUC）

评估必须在**测试集**上进行，重点关注以下指标：

- **区分度指标**：
  - **AUC**：通常 0.65-0.80 为健康，太高可能泄漏。
  - **KS**：衡量好坏人分布的最大间隔，通常要求 > 0.25。
  - **Gini** = 2*AUC - 1，用于报表。
- **稳定性指标**：
  - **PSI**：比较训练集与测试集（或最新线上数据）的分数分布，PSI < 0.1 为稳定，0.1-0.25 需注意，> 0.25 必须拒绝上线。
- **排序性指标**：
  - 按分数分箱（如等频分 10 箱），观察每个箱的坏账率是否单调递增，Lift 曲线是否理想。
- **校准性**：如果输出概率，检查 `probability calibration`，虽然风控中常用分数而非概率。

**例子：一个正常的评分卡模型评估结果**

```text
AUC: 0.72
KS: 0.31
PSI: 0.08
坏账率单调性：低分段(0-100)坏账率 35% → 高分段(900-1000)坏账率 1.2%

```text
这表示模型有良好的排序能力和稳定性，可以进入上线流程。

### 6. 模型解释（SHAP/评分卡得分）

**对于评分卡**，每个分箱都有对应的分数，可以直接解释每项特征贡献的分数。  
**对于 XGBoost**，使用 SHAP 计算特征重要性：

```python
import shap
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)
shap.summary_plot(shap_values, X_test)

```text
这能向业务方解释“为什么你的申请被拒绝”（如“多头借贷次数过高”贡献了 -30 分）。

### 7. 模型版本管理与上线

- 使用 **MLflow Model Registry** 将模型从 `Staging` 状态推进到 `Production`。
- 上线前必须通过**业务审批**，附上评估报告、PSI 对比、SHAP 摘要。
- 上线采用**A/B 测试**：先将 5% 流量导向新模型，观察通过率、逾期率无异常后，逐步放量至 100%。
- 同时保留旧模型版本，出现异常可一键回滚。

---

---

---

### L079
**分类：** 信贷风控建模
**题目：** 请举例说明更多实际例子如何实现？
**参考答案：** ### 例子1：评分卡模型（A卡）
**目标**：预测首次借款用户未来 90 天是否逾期。  
**样本**：过去 3 年的申请记录，以申请日为时间戳，标签为 90 天后的好坏标记。  
**特征**：从申请表、征信报告、设备指纹中抽取 60 个变量，经过分箱和 WOE 转换。  
**训练**：使用逐步回归的 Logistic Regression，确保所有变量系数方向符合业务逻辑。  
**评估**：AUC=0.76，KS=0.34，PSI 在近 6 个月保持 0.05。  
**上线**：部署为 API，每次审批请求时调用此模型输出信用分。

### 例子2：贷中额度调整模型（B卡）
**目标**：对已放款且还款 3 期以上的客户，预测未来 6 个月是否降额或提额。  
**样本**：还款满 3 期的时刻作为观察点，标签为该观察点后 6 个月内是否出现 M3+。  
**特征**：还款行为序列、额度使用率、外部征信最新数据。  
**模型**：LightGBM，因为特征交互复杂。  
**特殊点**：必须使用 **序列特征**（如近 3 期还款金额的均值和趋势），构造时需保证序列数据的截止时间在观察点之前。  
**评估**：AUC=0.81，KS=0.38，但 PSI 在某个新城市客群上达 0.22，进一步分析发现该地区收入波动大，单独为该区域建子模型。

### 例子3：反欺诈实时模型
**目标**：识别申请是否为欺诈（如伪冒申请、团伙攻击）。  
**样本**：历史欺诈案例（已确认） + 正常案例，标签为 0/1。  
**特征**：实时行为指标（申请页面停留时间、输入速度、修改次数）、设备关联网络特征。  
**模型**：XGBoost，但特征包含实时流特征，需要 Flink 提前算好写入 Redis。  
**挑战**：正负样本极度不均衡（欺诈率 < 0.1%），采用 SMOTE 或调整样本权重，并使用 Focal Loss 改进。  
**上线后监控**：每日欺诈捕获率和误杀率，一旦误杀率飙升立即切换规则。

---

---

---

### L080
**分类：** 信贷风控建模
**题目：** 请讲讲数据已按时间切分，且无泄漏中的训练完成后的持续迭代闭环
**参考答案：** 模型不是一次性项目，上线后还需持续监控和重训练：

1. **数据回流**：线上推理的特征快照、预测分数、最终还款标签，全部写入 Kafka → Iceberg，形成新的带标签样本。
2. **监控触发**：每月计算线上 PSI 和 KS，若 PSI > 0.25 或 KS 持续下降，触发自动重训练。
3. **重训练流程**：取最近两年的数据重新构建 PIT 样本，用同样的 Pipeline 训练新模型，与原模型对比，通过评估后上线。

---

**总结**：生产级模型训练是一个严谨的、从业务问题出发、以时序正确性为基石、以可解释和稳定性为约束的工程流程。
它要求你对样本构建、特征工程、模型原理、评估体系、上线规范都有深入的理解，而不仅仅是用 sklearn 调个参。


你提到的“数据范围”在信贷风控场景里，主要指的是**模型评估指标**、**特征质量指标**以及**系统监控阈值**。下面逐一解释它们的合理范围、过大或过小意味着什么，以及业内常用的判断依据。

---

### 一、模型区分度指标

#### 1. AUC（Area Under the ROC Curve）
- **范围**：0.5 ~ 1.0
- **合理区间**：0.65 ~ 0.80（信贷主模型）
- **解释**：
  - **< 0.6**：模型几乎没有区分能力，可能不如随机猜测。
  - **0.6 ~ 0.7**：勉强可用，需要更多特征工程。
  - **0.7 ~ 0.8**：良好，大多数生产级 A 卡在这个范围。
  - **> 0.8**：优秀，但要注意是否过度拟合或存在时间泄漏。
  - **> 0.95**：几乎肯定发生了**时间泄漏**或**标签直接作为特征**，必须立即排查。

#### 2. KS（Kolmogorov-Smirnov）值
- **范围**：0 ~ 1
- **合理区间**：0.25 ~ 0.50
- **解释**：
  - **< 0.2**：区分度不足，好坏人分数重叠严重。
  - **0.2 ~ 0.25**：一般，可上线但需谨慎。
  - **0.25 ~ 0.4**：良好，大多数风控模型的目标区间。
  - **0.4 ~ 0.5**：很强，但必须检查过拟合或数据穿越。
  - **> 0.5**：可能异常，需排查泄漏或数据错误。

#### 3. Gini 系数
- **范围**：0 ~ 1
- **与 AUC 的关系**：Gini = 2×AUC - 1
- **合理区间**：0.3 ~ 0.6（对应 AUC 0.65~0.80）
- **解释**：等同于 AUC 的线性变换，标准一致。

---

### 二、模型稳定性指标

#### 4. PSI（Population Stability Index）
- **范围**：0 ~ +∞
- **解释**：
  - **< 0.1**：稳定，模型分数分布几乎无变化，可以放心使用。
  - **0.1 ~ 0.25**：轻微偏移，需要关注，可能需要准备更新模型。
  - **> 0.25**：显著偏移，模型已经不能代表当前客群，**必须停止上线或触发重训练**。
- **过大（> 0.25）意味着**：线上进件人群的特征分布与建模样本发生了重大变化（如政策调整、新渠道涌入），继续使用会导致决策失效。

---

### 三、特征质量指标

#### 5. IV（Information Value）
- **范围**：0 ~ +∞
- **解释**：
  - **< 0.02**：几乎没有预测能力，可以考虑丢弃。
  - **0.02 ~ 0.1**：较弱，可保留作为辅助特征。
  - **0.1 ~ 0.3**：中等，有价值的特征。
  - **0.3 ~ 0.5**：强，核心特征。
  - **> 0.5**：极强，但需警惕是否与标签过强关联（如直接包含了未来信息），或者该特征本身就是标签的某种衍生物。
- **过小**：特征无用，增加噪音和计算成本。
- **过大**：极可能是泄漏或直接映射，需要人工审查。

#### 6. 特征缺失率
- **范围**：0% ~ 100%
- **合理区间**：通常要求 < 30%，核心特征最好 < 5%
- **解释**：
  - **缺失率 > 50%**：该特征基本失效，要么丢弃，要么单独处理（如建立缺失指示变量）。
  - **线上缺失率突然飙升**：数据源或采集链路故障，需立刻告警。

---

### 四、信用分与决策阈值

#### 7. 信用分
- **常见范围**：300 ~ 900（可自定义）
- **解释**：
  - 分数越低，风险越高。
  - 通常会设定**截断点（cutoff）**，例如：
    - **< 450**：自动拒绝（高风险）。
    - **450 ~ 650**：人工审核或降额通过。
    - **> 650**：自动通过。
  - 阈值取决于通过率与坏账率的平衡，通过**K-S 曲线**选择最优切点。

#### 8. 通过率与坏账率
- **通过率**：审批通过的申请占比。
- **坏账率**：通过客户中最终逾期的比例。
- **关系**：
  - 如果提高通过率，坏账率通常会上升；压低通过率，则收益下降。
  - 通过模型排序能力，可以在相同的通过率下获得更低的坏账率，或在相同的坏账率下通过更多优质客户。

---

### 五、系统监控指标

#### 9. 推理服务延迟（P99）
- **合理范围**：< 100ms（实时授信场景）
- **解释**：
  - **P99 > 200ms**：用户体验下降，可能因为特征获取超时或模型太大。
  - **P99 > 500ms**：严重的性能瓶颈，需要熔断或切换备用模型。

#### 10. 模型分数空值率
- **合理范围**：< 0.1%
- **过大**：特征服务故障或数据缺失，模型输出大量默认值，影响决策准确性。

---

**总结**：在信贷风控系统中，这些数值范围不仅是模型好坏的衡量尺，更是**自动监控、自动告警、自动重训练**的触发条件。
生产环境中我们会将这些阈值写入 Prometheus 告警规则和 Airflow 模型监控任务中，确保系统始终运行在健康区间内。

---

---

### L081
**分类：** 信贷风控建模
**题目：** 请讲讲补充/01_黑白名单建立.md中的黑名单的建立方式
**参考答案：** 黑名单的核心目标是**拦截已知的欺诈、逾期、恶意用户**。来源有四大类：

### 1. 内部积累的黑名单
- **历史逾期/坏账客户**：所有曾发生 M3+ 逾期、核销、代偿的用户，直接从还款表、贷后系统抽取。
- **确认的欺诈案例**：经反欺诈团队人工调查标记的欺诈申请（如伪冒身份、团伙攻击），存入黑名单库。
- **内部员工/测试账号**：防止内部账号误入生产流程。

**建立方法**：由离线 Spark 作业每日从数仓 DWS 层抽取，生成黑名单快照，推送到在线存储。

### 2. 外部征信/三方数据源
- **多头借贷黑名单**：对接第三方征信公司（如百行、朴道），获取近期频繁申请、多头严重用户列表。
- **法院失信/被执行名单**：通过公开接口查询。
- **设备指纹黑名单**：与设备指纹服务商合作，获取被标记的高风险设备 ID、IP 段。

**建立方法**：通过定时批量同步文件（SFTP + 解密）或实时 API 查询，关键字段经 ETL 清洗后入库。由于外部数据可能带有 PII，需在入库时即脱敏（如仅存哈希值）。

### 3. 实时规则产生的动态黑名单
- **短时高频申请**：Flink 实时计算同一设备/IP 在 5 分钟内申请次数 > 10 次，自动将其加入临时黑名单（有效期 24 小时）。
- **关联图谱异常**：基于图数据库（如 Neo4j）分析设备、手机号、银行卡的关联密度，发现团伙欺诈特征后，批量添加关联节点到黑名单。
- **规则触发**：命中某些高危规则（如信息不一致、人脸比对失败 3 次）直接拉黑。

**建立方法**：Flink 作业输出事件到 Kafka，由专门的“名单管理服务”消费并写入 Redis，设置 TTL。

### 4. 离线挖掘的黑名单
- 通过 Spark 分析历史数据，发现某些高风险特征组合（如特定年龄段 + 职业 + 地区的逾期率超过阈值），可生成基于特征的规则，也可将符合条件的存量用户直接列入关注名单，人工审核后转为黑名单。

---

---

---

### L082
**分类：** 信贷风控建模
**题目：** 请讲讲补充/01_黑白名单建立.md中的白名单的建立方式
**参考答案：** 白名单用于识别**极低风险、高价值用户**，给予免审、提额等特权。

### 1. 内部优质客户
- **历史还款记录优良**：在贷后 12 个月内无任何逾期，且正常结清多笔的老客户。
- **高净值/高收入人群**：基于收入证明、资产信息审核通过，且征信良好的用户。
- **内部员工/亲属**：走特殊通道，经审批加入。

**建立方法**：由离线 Spark 周期性（如 T+1）分析数仓 DWS 层的客户表现宽表，生成白名单，推送至在线存储。

### 2. 合作渠道预授信
- 与大型电商、运营商、银行合作，获取预先审批通过的优质名单（需合规授权）。
- 这些用户往往已通过对方风控筛选，风险极低。

**建立方法**：批量文件导入，经过必要映射（统一 user_id）后入白名单库。

### 3. 模型驱动的“高分免审”
- 对于模型评分极高（如 A 卡输出 > 950 分）且关键特征稳定（如信用分高、收入负债比低）的用户，可设定规则自动加入白名单，下次申请时直接通过。
- 这可以降低请求压力和成本，提升用户体验。

**建立方法**：在模型推理环节，若分数超过设定的高分阈值，异步发送消息触发白名单添加。

---

---

---

### L083
**分类：** 信贷风控建模
**题目：** 请举例说明技术实现细节如何实现？
**参考答案：** ### 1. 存储选型
- **Redis**：最适合存储黑白名单，支持 String/Hash 结构，O(1) 查询，可设置 TTL 用于临时名单。
  - Key 设计：
    - 黑名单：`bl:user:{user_id}` → `"1"` (或过期时间戳)
    - 基于设备：`bl:device:{device_id}` → `"1"`
    - 白名单：`wl:user:{user_id}` → `"grade:A"` (可带等级)
- **Bloom Filter**：当名单量极大（亿级）且内存有限时，可用 RedisBloom 模块，减少内存占用。但只能判断“可能存在”，适合黑名单初步过滤，命中后再查精确库。
- **HBase/Cassandra**：持久化名单库，做全量审计和回溯。

### 2. 查询接口
在推理网关中封装一个 `ListCheckService`：

```python
def check_blacklist(user_id, device_id, ip):
    if redis.exists(f"bl:user:{user_id}") or redis.exists(f"bl:device:{device_id}"):
        return "REJECT", "命中黑名单"
    return "PASS", None

def check_whitelist(user_id):
    grade = redis.get(f"wl:user:{user_id}")
    if grade:
        return "PASS", grade  # 可能跳过后续模型
    return None, None

```text
### 3. 同步管道
- **离线批量更新**：Spark 作业每天计算最新名单，通过 **Redis Pipeline** 批量写入，或使用 Feast 的 `materialize` 功能将名单作为特征推送到在线存储。
- **实时增量更新**：CDC 监听黑名单管理系统的 MySQL 表，或 Flink 消费 Kafka 中的动态名单事件，实时 `SET/DEL` Redis key。

### 4. 有效期与回撤
- 所有黑名单条目必须有 `expire_time`，临时名单过期自动消失。
- 提供**回撤机制**：若误杀用户，可通过运营后台手动从 Redis 中 `DEL` 该 key，并记录审计日志。

---

---

---

### L084
**分类：** 信贷风控建模
**题目：** 请详细讲解更新与监控机制
**参考答案：** - **定时重审**：每月离线作业分析白名单用户的后续表现，若出现逾期，立即剔除。
- **黑名单变动通知**：新增高风险名单时，需同步到风控引擎和人工审核队列。
- **命中率监控**：监控黑名单命中率、白名单通过率，若突然激增或骤降，可能是数据源异常或规则失效。
- **审计日志**：每次名单命中决策都需记录到 Kafka，关联请求 ID，用于后续分析和监管审查。

---

**总结**：黑白名单的建立是**数据驱动+规则驱动**的结合，技术上依赖 **离线挖掘、实时计算、高效存储和可靠同步**。它们是风控系统中成本最低、速度最快的决策层，直接决定了能否在海量申请下高效拦截风险、提升优质客户体验。

---

---

### L085
**分类：** 信贷风控建模
**题目：** 先说清三个概念分别是什么
**参考答案：** ### 1. XGBoost
**它是一个具体的算法/工具，属于机器学习的范畴。**
XGBoost（eXtreme Gradient Boosting）是一种**梯度提升树**算法，通过逐步构建多棵决策树，每棵新树都去拟合前序所有树的预测误差，从而得到一个高精度模型。它是传统机器学习中处理**结构化表格数据**的“最强单模型”之一。

- **本质**：集成学习 + 决策树 + 梯度优化。
- **输出**：确定性的预测分数（概率或类别），相同输入永远得到相同输出。
- **特点**：高精度、自动处理缺失值、支持正则化防过拟合、训练快。

### 2. 机器学习 (Machine Learning)
**它是一个更大的技术范畴，XGBoost 是它的一个具体实现。**
机器学习的核心思想是：**让计算机从数据中自动学习规律和模式，从而做出预测或决策，而无须显式地编程每一条规则。**
它包含很多种算法：
- **传统机器学习**：线性回归、逻辑回归、决策树、随机森林、SVM、朴素贝叶斯、XGBoost 等。
- **深度学习**：神经网络（CNN、RNN、Transformer 等），是机器学习的一个分支。

### 3. 深度学习 (Deep Learning)
**它是机器学习的一个子集，使用深层神经网络来学习数据的多层抽象表示。**
“深度”指的就是网络中堆叠了多个隐藏层（通常几十上百层），每层自动提取不同粒度的特征。它不再需要人工设计特征，可以从原始数据（像素、波形、文本序列）中端到端地学习。

---

---

---

### L086
**分类：** 信贷风控建模
**题目：** 请说说XGBoost 与机器学习的关系：局部 vs 整体
**参考答案：** 把机器学习想象成**交通工具**，深度学习是**飞机**，XGBoost 是**一辆性能极强的高铁**。

- **机器学习 = 所有交通工具**：包括自行车（规则）、汽车（逻辑回归）、高铁（XGBoost）、飞机（深度学习）。
- **XGBoost = 高铁**：在特定路线上（结构化数据）速度很快、效率高，但无法飞越大洋（无法直接处理图像、语音等原始信号）。
- **深度学习 = 飞机**：能跨越非结构化数据的海洋，但起降需要更长的跑道（大量数据、庞大算力、长训练时间）。

---

---

---

### L087
**分类：** 信贷风控建模
**题目：** 请说说机器学习和深度学习的核心区别
**参考答案：** 这是你真正需要掌握的关键对比，可以归纳为 6 个维度：

| 维度 | 传统机器学习 (含 XGBoost) | 深度学习 |
|------|---------------------------|----------|
| **特征工程** | 必须由领域专家**人工设计特征**（如收入负债比、近30天点击次数），特征质量决定模型上限 | **端到端自动学习特征**，无需人工设计。底层网络发现边缘，中层发现纹理，高层发现物体部件 |
| **数据需求** | 对数据量要求相对宽松，几千条数据即可训练出可用模型；对表格型、高维稀疏数据极擅长 | 极度依赖**海量数据**（百万级以上），数据少了很容易过拟合；擅长处理图像、语音、文本等连续信号 |
| **模型可解释性** | **天生强解释性**：可以精确知道每个特征对结果的贡献（特征重要性、SHAP 值、评分卡得分明细） | **“黑盒”**：即使通过 Grad-CAM、Attention 可视化，解释也是近似的，很难做到逐决策的精确归因 |
| **计算资源** | 通常 **CPU** 即可训练和推理，成本低，速度快。XGBoost 单机跑千万级数据也能在几分钟完成 | 依赖 **GPU/TPU** 集群，训练可能耗时数天甚至数周，推理也需要 GPU 来满足低延迟要求 |
| **数据形态** | 主要处理**结构化数据**（数据库中的表格、日志），字段有明确的物理含义 | 主要处理**非结构化数据**（图像、音频、视频、自然语言），原始数据是像素、波形、token 序列 |
| **决策边界** | 学习到的边界通常是**线性的或者由规则组合而成的较简单的非线性边界**（树模型的轴对齐分割） | 能学习到极度复杂、平滑的非线性边界，可以拟合几乎任意函数（万能逼近定理） |

---

---

---

### L088
**分类：** 信贷风控建模
**题目：** 结合多场景，看它们如何选型（附例子）
**参考答案：** ### 场景 1：金融信贷风控
- **用 XGBoost（传统 ML）**：输入是“年龄、收入、多头借贷次数”等 50 个结构化特征，训练 XGBoost 模型，AUC 0.78，用 SHAP 解释为什么拒贷（“多头借贷次数过高”贡献了 -30 分），监管满意，上线在 CPU 服务器上 5ms 推理。
- **不用深度学习**：数据是表格，几千个样本不足以训练神经网络，且无法向监管解释。深度学习在这个场景是“用牛刀杀鸡，且砍完之后无法证明牛刀没有乱砍”。

### 场景 2：CT 医学影像肺结节检测
- **用深度学习 (CNN/ResNet)**：输入是 512×512 像素的 CT 切片，没有现成的“结节边缘形态”这个特征，你无法手工定义。深度网络自动学习低层边缘、中层纹理、高层结节形态，检测 mAP 达到 0.95。
- **不用 XGBoost**：你要把每张 CT 转化为“结节面积、轮廓复杂度、灰度均值”等人工特征，不仅工程浩大，而且会丢失大量信息，效果远不如 CNN。

### 场景 3：电商推荐排序
- **二者结合（混合架构）**：底层用 **XGBoost** 处理稠密的特征表格（用户画像、物品属性、上下文），输出一个强基线；同时用**深度学习双塔模型**（用户塔和物品塔）将 user_id 和 item_id 映射为低维 embedding，捕捉高维稀疏 ID 的深层语义。最后将两个模型的预测分数加权融合，得到最佳效果。

### 场景 4：自然语言处理（情感分析）
- **用深度学习 (BERT/Transformer)**：评论文本是“这个手机屏幕很棒，但电池太差”，模型能自动理解“但”字的转折，准确判断出整体中性偏负。
- **用传统 ML**：你得把文本转换成 TF-IDF 或词袋向量，然后丢给逻辑回归，它会完全丢失语序和上下文，效果大打折扣。

---

---

---

### L089
**分类：** 信贷风控建模
**题目：** 请讲讲补充/02_XGBoost，机器学习和深度学习区别.md中的**总结**：一句话抓住精髓
**参考答案：** - **XGBoost**：是机器学习中的“表格数据杀手”，高效、确定、可解释，结构化数据的首选。
- **机器学习**：是从数据中自动发现映射关系 \( f(X) \to y \) 的所有方法的统称，包括决策树、SVM、神经网络。
- **深度学习**：是机器学习的“非线性特征学习利器”，通过深层神经网络征服图像、语音、文本等非结构化数据，代价是需要海量数据和巨大算力，且牺牲了可解释性。

**选择逻辑**：如果你手头的数据是 **Excel 表格**，就先用 XGBoost/逻辑回归；如果你要处理的是**图片、音频、长文本**，就得用深度学习；很多时候，**两者结合**（传统 ML 做特征工程 + 深度学习做特征表示）才能达到生产级最优。

---

---

### L090
**分类：** 信贷风控建模
**题目：** 请讲讲补充/02_abc 卡以及其他领域对应模型.md中的A/B/C 卡在信贷中的标准定义
**参考答案：** | 卡片 | 全称 | 使用时机 | 目标 |
|------|------|----------|------|
| **A 卡** | Application Scorecard（申请评分卡） | 用户申请时 | 预测放款后是否逾期，决定批不批、批多少 |
| **B 卡** | Behavior Scorecard（行为评分卡） | 放款后，贷中管理 | 根据还款/消费行为预测后续风险，决定提额、降额、催收 |
| **C 卡** | Collection Scorecard（催收评分卡） | 发生逾期后 | 预测催回可能性，决定催收策略（短信、电话、上门、法催） |

---

---

---

### L091
**分类：** 信贷风控建模
**题目：** 请讲讲补充/02_abc 卡以及其他领域对应模型.md中的其他行业中的对应模型（换了个名字）
**参考答案：** ### 1. 电商 / 本地生活（美团、淘宝）
- **相当于 A 卡**：**新客首单转化模型**。用户注册后，预测其首次下单的概率或潜在价值，决定是否发放新人优惠券、补贴多少。
- **相当于 B 卡**：**用户价值/流失预警模型**。根据历史浏览、购买、评价行为，判断用户是否即将流失，或是否值得进行交叉销售，从而触发优惠券推送或专属客服。
- **相当于 C 卡**：**流失召回模型**。用户已流失（N 天未访问），预测其被召回的概率，决定是否发送召回短信、Push，以及给予多大优惠。

### 2. 保险行业
- **相当于 A 卡**：**投保核保模型**。预测投保人未来出险的概率，决定是否承保、保费费率。
- **相当于 B 卡**：**保中风险预警模型**。监测被保险人行为（如车险的驾驶数据、健康险的运动数据），动态调整风险评级或保费。
- **相当于 C 卡**：**理赔反欺诈模型**。发生理赔时，判断是否为欺诈案件，决定是否启动调查。

### 3. 内容平台（抖音、B 站）
- **相当于 A 卡**：**冷启动内容推荐模型**。新视频/新用户，根据初始标签和历史数据，预测互动概率，决定第一波流量池大小。
- **相当于 B 卡**：**用户留存/互动预测模型**。根据近期观看时长、互动率，预测明日留存或付费意愿，调整推荐频次和内容质量。
- **相当于 C 卡**：**召回/续费模型**。对已不活跃或会员即将过期的用户，预测续费可能，决定召回策略。

### 4. 游戏行业
- **相当于 A 卡**：**新用户付费预测模型**。根据首日玩法、设备、渠道，预测其成为大 R（高付费用户）的概率，引导运营资源投放。
- **相当于 B 卡**：**用户流失预警模型**。根据登录频率、在线时长、社交互动，预测 7 天内流失风险，触发挽留礼包。
- **相当于 C 卡**：**流失用户回流模型**。已流失玩家，根据其历史充值、段位，预测回流概率，决定是否发送回归奖励。

---

---

---

### L092
**分类：** 信贷风控建模
**题目：** 为什么其他行业不叫 A/B/C 卡？
**参考答案：** 1. **行业术语习惯**：信贷称之“评分卡”，互联网更爱叫“XXX 预估模型”、“XXX 率预测”。
2. **决策复杂度**：信贷决策是强规则、强监管的，每个阶段泾渭分明。而互联网场景的模型往往作为推荐系统或策略系统的一个输入，决策链路更柔性和复杂，不一定会单独拆成“卡片”形态。
3. **传统积淀**：银行体系内部审计、合规、文档管理要求严格，这类术语一旦写进制度就很难改变。互联网公司变化快，命名更灵活。

**总结**：A/B/C 卡的**思想是通用的——把用户生命周期切成不同的阶段，在每个阶段用当时能拿到的所有信息，去预测该阶段最重要的目标。
** 只是信贷领域把这一套玩到了极致，并赋予了它约定俗成的名字。作为 AI 应用开发者，你应该透过名字看到其背后“分阶段建模”的设计思想，而不要被术语限制住。

---

---

### L093
**分类：** 信贷风控建模
**题目：** ML 系统是什么？
**参考答案：** 它是一个将 **数据、模型、代码、基础设施** 紧密结合的端到端流水线，负责完成从原始数据到最终业务决策，再到持续迭代的完整闭环。

在信贷场景下，ML 系统的核心是：


```text
用户行为/业务数据 → 实时+离线数仓 → 特征平台 → 模型训练 → 模型服务 → 业务决策 → 效果反馈
                                        ↑________________________↓
                                          (监控、重训练、回滚)

```text
一个成熟的 ML 系统远比 Jupyter Notebook 里调个参复杂得多，它必须解决工程化、可靠性、可解释性、合规性等一系列生产级问题。

---

---

---

### L094
**分类：** 信贷风控建模
**题目：** 请讲讲补充/02_ml 系统以及关键组成应用.md中的ML 系统的核心组成
**参考答案：** 基于我们之前的讨论，ML 系统由以下关键子系统组成：

| 子系统 | 我们项目中的对应组件 | 作用 |
|--------|-------------------|------|
| **数据管道** | Kafka、Flink、Spark、Iceberg | 实时/离线采集、清洗、存储海量数据，构成 ODS/DWD/DWS 分层数仓 |
| **特征平台** | Feast（离线+在线存储） | 定义、计算、管理、服务特征，保证训练与线上一致性，支持 PIT 拼接 |
| **模型训练管道** | Airflow/Kubeflow + MLflow | 自动化样本构建、模型训练、评估、注册，记录实验和版本 |
| **模型服务** | FastAPI/gRPC + Redis | 提供低延迟推理 API，集成特征获取、规则引擎、模型打分和决策逻辑 |
| **监控与反馈** | Prometheus + Grafana + 自动重训练 | 监控数据漂移、模型衰减、系统延迟，触发告警或自动迭代 |
| **治理与合规** | 权限、审计、PII 脱敏、可解释性 | 满足监管要求，保证决策可追溯、可解释（SHAP/评分卡） |

---

---

---

### L095
**分类：** 信贷风控建模
**题目：** ML 系统的作用（为什么需要它）
**参考答案：** ### 1. 把模型变成可用的产品
单次模型训练只是实验室产物，ML 系统将其封装为 **7×24 小时运行的服务**，能毫秒级响应业务请求，并通过灰度发布、A/B 测试安全上线。

### 2. 保证线上与线下的一致性
消除 **Training-Serving Skew**（训练与推理特征不一致）是核心难点。ML 系统通过特征平台统一管理离线训练和在线推理的特征逻辑，确保模型在线上使用的特征与训练时看到的特征口径完全一致。

### 3. 实现持续学习与快速迭代
市场客群在变，模型会衰减。ML 系统通过**闭环反馈**自动收集线上预测与真实标签，定期重训练，模型版本通过 MLflow 管理，可以快速回滚到历史稳定版本。

### 4. 满足金融级可靠性与合规
- **确定性决策**：使用传统 ML 引擎（评分卡、XGBoost），相同输入永远得到相同输出。
- **可解释性**：每笔决策都能输出特征贡献，向监管和客户解释拒绝原因。
- **安全与隐私**：全链路脱敏，禁止明文 PII，权限细粒度控制。

### 5. 打通多个团队协作
数据工程师维护数仓和管道，算法工程师专注特征和模型，开发工程师负责服务部署，运营人员监控业务指标。ML 系统提供了统一的平台和流程，让各角色高效协作。

---

---

---

### L096
**分类：** 信贷风控建模
**题目：** 请讲讲补充/02_ml 系统以及关键组成应用.md中的在信贷风控中的具体作用实例
**参考答案：** - **贷前审批 A 卡**：ML 系统接收申请，实时计算 500+ 特征，调用评分卡模型输出信用分，结合规则引擎和额度策略，在 50ms 内返回审批结果。
- **反欺诈**：流处理引擎从 Kafka 消费行为埋点，计算 5 分钟窗口内的点击频率、设备关联，XGBoost 模型给出欺诈概率，高危直接拒绝。
- **贷中监控 B 卡**：每天凌晨 Spark 批处理扫描存量客户，B 卡模型计算最新风险分，推送调额、降额、催收名单给业务系统。
- **模型迭代**：每月自动用最近两年数据构建 PIT 样本，训练新模型，若 PSI 稳定且 AUC 提升，自动推送至 Staging，人工确认后上线。

---

---

---

### L097
**分类：** 信贷风控建模
**题目：** 请讲讲补充/02_规则引擎，决策树，逻辑回归评分卡，信用分，XGBoost，高精度确定性树模型，A 卡，b 卡.md中的逐个详细解释
**参考答案：** ### 1. 规则引擎
**是什么**：一种执行确定性 if-then 规则的软件系统，规则以声明式的方式独立于应用代码维护。比如“年龄 < 18 直接拒绝”、“命中内部黑名单则拒绝”。  
**核心特征**：完全透明、即时生效、不依赖数据训练。  
**常见产品**：Drools、EasyRules，或自研 Python 规则引擎（如简单的函数调度）。

### 2. 决策树
**是什么**：一种基础机器学习模型，通过树状结构对数据进行分割，每个内部节点是一次特征判断，叶子节点给出预测类别或概率。  
**核心特征**：天生可解释，可以直接导出 if-else 规则集，作为简单有效的基线模型。  
**在信贷中的定位**：通常不用作主模型，而用于辅助特征筛选、提取规则，或作为可解释性要求极高场景下的备选。

### 3. 逻辑回归评分卡
**是什么**：将 **逻辑回归** 与 **WOE（证据权重）分箱** 结合的传统信贷建模方法。先将每个特征分箱并计算 WOE，
再用逻辑回归拟合，最后将概率线性转化为易于加总的信用分。  
**核心特征**：每个特征对最终得分的影响是线性可加的，可直接列出“评分明细”，是监管机构最认可的模型形式。  
**典型输出**：一张“评分卡”，告诉你“年龄 25-35 加 10 分，多头借贷次数 > 5 减 30 分”等等。

### 4. 信用分
**是什么**：一个标准化的数值，用来量化个人或企业的信用风险。分数越高，风险越低。  
**生成方式**：可以由评分卡直接计算，也可以由其他模型（如 XGBoost）输出的概率通过分数字典映射得到。  
**关键参数**：基分（base score）和 PDO（Point-to-Double Odds），比如“600 分表示 odds 为 1:1，每 20 分 odds 翻倍”。  
**作用**：为不同模型提供统一的尺度，便于设定阈值和业务沟通。

### 5. XGBoost
**是什么**：一个高效的梯度提升树（GBDT）算法实现，通过迭代训练多棵决策树来拟合残差，最终得到强模型。  
**核心特征**：精度极高，能够自动捕捉特征交互和非线性关系，但本身是“黑盒”，需要借助 SHAP 等工具解释。  
**在信贷中的定位**：常用于反欺诈模型、额度模型（B 卡），追求预测精度的场景。

### 6. 高精度确定性树模型
**这不是一个新概念，而是对 XGBoost、LightGBM 等集成树模型属性的描述**：  
- **高精度**：相比单棵决策树或逻辑回归，它们在大规模数据上表现更好。  
- **确定性**：模型结构和参数固定后，相同输入必然得到相同输出，与深度学习不同（不含随机 dropout）。  
因此，在要求确定性决策的金融系统中，这类模型依然符合要求，只要补充解释性即可。

### 7. A 卡（Application Scorecard）
**是什么**：申请评分卡，用于贷前审批环节。根据用户申请时提交的信息及第三方征信数据，预测其在未来一段时间（如 12 个月）内发生逾期的概率。  
**使用时机**：用户首次申请借款时。  
**模型输出**：信用分或违约概率，据此决定是否通过、授信额度及利率。

### 8. B 卡（Behavior Scorecard）
**是什么**：行为评分卡，用于贷中管理。针对已经放款的客户，利用其在平台上的还款行为、消费行为等动态数据，预测未来违约风险。  
**使用时机**：客户已有贷款，需判断是否提额、降额、交叉销售或提前催收。  
**数据特色**：包含时间序列行为（如还款准时率、额度使用趋势），对模型捕捉行为变化能力要求更高。

---

---

---

### L098
**分类：** 信贷风控建模
**题目：** 请讲讲补充/02_规则引擎，决策树，逻辑回归评分卡，信用分，XGBoost，高精度确定性树模型，A 卡，b 卡.md中的它们之间的联系
**参考答案：** 这些概念共同构成一个完整的 **信贷决策体系**，可以用如下层次梳理：

### 1. 从算法到模型
- **决策树** 是基本单元。
- **XGBoost（高精度确定性树模型）** 是决策树的集成，追求精度。
- **逻辑回归评分卡** 是另一种传统、可解释的方法，与树模型并列。
- 这两类模型都可以用来构建 **A卡** 或 **B卡**，只是业务阶段不同。

### 2. 从模型到分数
- 无论使用评分卡还是 XGBoost，最终都会转换成 **信用分** 统一呈现。
- 评分卡天然输出分数；XGBoost 输出的概率可以通过分数字典映射为信用分。

### 3. 从分数到决策
- **规则引擎** 坐在模型前面，执行“一票否决”或“直接通过”的硬性政策。
- 模型（A卡/B卡）输出信用分后，策略层再结合分数、收入、产品限额等决定最终额度和利率。

### 4. 整体决策流（联系链）

```text
贷款申请 
  → 规则引擎（黑名单、年龄等硬规则）→ 通过 
  → A卡模型（评分卡或XGBoost）→ 输出信用分 
  → 策略层（分数阈值 + 额度矩阵）→ 审批结果
放款后 
  → 行为数据采集 
  → B卡模型（可能是XGBoost）→ 输出动态风险分 
  → 触发调额、催收动作

```text

---

---

---

### L099
**分类：** 信贷风控建模
**题目：** 请讲讲补充/02_规则引擎，决策树，逻辑回归评分卡，信用分，XGBoost，高精度确定性树模型，A 卡，b 卡.md中的作用**总结**
**参考答案：** | 组件 | 核心作用 |
|------|----------|
| **规则引擎** | 实现零容忍政策、快速拦截已知风险，无法从数据自学，需人工维护 |
| **决策树** | 可作为可解释基线，或用于生成业务规则、辅助特征筛选 |
| **逻辑回归评分卡** | 强解释性、满足监管要求，适合主风控模型（A卡），输出标准信用分 |
| **信用分** | 提供统一风险度量衡，便于设定业务阈值和对外展示 |
| **XGBoost 高精度树模型** | 追求最大化预测精度，适合反欺诈、动态 B 卡等复杂场景，需配套 SHAP 解释 |
| **A 卡** | 贷前准入，控制坏账率，决定借不借、借多少 |
| **B 卡** | 贷中监控，动态调整信用，提升客户价值并减少损失 |

---

---

---

### L100
**分类：** 信贷风控建模
**题目：** 具体如何使用（结合生产项目）
**参考答案：** ### 1. 规则引擎的使用方式
在推理网关中用 Python 实现一套轻量规则调度器：

```python
def rule_engine(req):
    if req.age < 22:
        return "REJECT", "年龄不符"
    if blacklist_redis.exists(f"bl:{req.user_id}"):
        return "REJECT", "命中内部黑名单"
    return "PASS", None

```text
规则可以存储在数据库或配置文件中，支持热更新。

### 2. 评分卡模型的使用（A卡）
- 离线训练：完成 WOE 分箱 → 逻辑回归 → 评分转换，导出评分卡配置（JSON）。
- 在线推理：根据配置对实时请求的特征分箱，乘以系数，加总得到信用分。
- 评分明细示例：`{"收入": +15, "多头借贷": -20, "信用历史": +30}` → 总分 625。

### 3. XGBoost 的使用（反欺诈 / B卡）
- 离线训练：PIT 样本构建 → XGBoost 训练 → MLflow 注册。
- 在线加载：FastAPI 服务中加载模型文件，推理得到概率。
- 解释：在线用 SHAP 计算特征贡献，返回拒绝原因。
- B 卡场景：每日批处理方式扫描存量客户，输出最新风险分，写入数据库供业务系统使用。

### 4. A 卡与 B 卡的协同
- 客户申请时跑 A 卡，决定是否进件。
- 放款后，B 卡系统每日/周更新所有客户的 B 卡分数，如果 B 卡分低于阈值，自动冻结额度或转入人工催收队列。

### 5. 信用分的统一
无论底层模型是评分卡还是 XGBoost，最终都映射到同一个信用分尺度（如 300-900），保持前端和运营系统的一致性。

---

---

---

### L101
**分类：** 数据仓库
**题目：** 为什么需要分层？（30min）
**参考答案：** ### 1.1 不分层的问题

假设你把所有数据堆在一张表里：


```sql
-- 反模式：一张大表承载所有
CREATE TABLE all_data (
    user_id STRING,
    user_name STRING,       -- 明文姓名
    id_card STRING,          -- 明文身份证
    apply_amount DOUBLE,     -- 有些是 -1000（脏数据）
    product_type STRING,     -- 有些是 NULL
    event_type STRING,       -- 行为事件
    overdue_cnt INT,         -- 聚合后的逾期次数
    ...
);

```text
三个致命问题：

| 问题 | 后果 |
|------|------|
| 安全和合规 | 任何人查这张表都能看到明文身份证，违反个人信息保护法 |
| 数据质量 | 分析师不知道 apply_amount=-1000 是脏数据还是真实退款 |
| 复用性差 | 每次有新需求都要重新扫全表 → 10 亿行扫一次 5 分钟 |

### 1.2 分层的解决思路


```text
ODS: "我照镜子" — 源系统是什么样，我就是什么样
DWD: "我洗衣服" — 脏数据清洗掉，敏感信息遮挡住，但衣服还是那件衣服
DWS: "我分类叠衣服" — 按人按日期归拢，一件衣服变成统计数字
ADS: "我摆到衣柜里" — 每个抽屉对应一个用途（训练/报表/监控）

```text

---

---

---

### L102
**分类：** 数据仓库
**题目：** 请讲讲分层数据仓库架构设计与 DDL中的ODS 层：原始数据 1:1 镜像（1h）
**参考答案：** ### 2.1 核心原则

**ODS 不做任何处理**。四个原因：

1. **可追溯**：下游数据有问题 → 回到 ODS 查原始值
2. **可重放**：清洗规则变更 → 从 ODS 重新跑，不需要重新接入源系统
3. **可审计**：监管要求"保留原始记录 5 年"，ODS 就是原始记录
4. **解耦**：源系统改造不影响下游（ODS 做缓冲层）

### 2.2 实战：阅读项目代码

打开 `src/data/warehouse/ods_layer.py`：


```python
# 第 30-79 行 — 表元数据管理

@dataclass
class ODSTable:
    """每张 ODS 表的"身份证"

    三个核心字段：
    - source_system: 从哪来？（数据血缘的起点）
    - ingest_method: 怎么来的？（binlog 实时 / API log / SDK / 文件）
    - partition_key: 按什么分区？（决定查询性能）
    """
    name: str
    source_system: str
    ingest_method: str
    partition_key: str = "dt"
    description: str = ""


# ★ 为什么用独立的字典注册所有表？
ODS_TABLES = {
    "ods_application": ODSTable(
        name="ods_application",
        source_system="mysql_credit_core",  # ← 告诉所有人：这表来自 MySQL
        ingest_method="binlog",              # ← 告诉所有人：通过 binlog 同步
        description="用户贷款申请表",
    ),
    "ods_user_behavior": ODSTable(
        name="ods_user_behavior",
        source_system="sdk_analytics",       # ← 来自埋点 SDK
        ingest_method="sdk",
        description="用户行为埋点流",
    ),
}

```text
**为什么这么设计？**

- 用 `dataclass` 而不是 `dict`：IDE 自动补全 + 类型安全 + 不会被意外修改
- 单独定义 `ODS_TABLES`：新增表只需加一行，代码自动感知（`ODS_TABLES.values()` 遍历）
- `source_system` 是强制字段：强制开发者注明来源 → 数据血缘从这里开始

### 2.3 动手：看实际 ODS 数据


```bash
cd credit_risk_control_system
python3 -c "
import pandas as pd
df = pd.read_parquet('data/warehouse/ods/dt=2026-07-01/ods_application.parquet')
print('列名:', list(df.columns))
print('行数:', len(df))
print()
# 看一条原始数据
row = df.iloc[0]
print('user_name:', row['user_name'], '← 明文！必须在 DWD 脱敏')
print('id_card:', row['id_card'], '← 明文！')
print('apply_amount:', row['apply_amount'], '← 可能有负数')
print('product_type:', row['product_type'], '← 可能是 None')
"

```text
你应该看到：明文姓名、明文身份证、可能有 `None` 和异常值——这就是 ODS 层"不处理"的体现。

### 2.4 练习：手写电商 ODS 定义（30min）

在空白 `.py` 文件中完成以下代码：


```python
from dataclasses import dataclass

@dataclass
class ODSTable:
    name: str
    source_system: str
    ingest_method: str
    partition_key: str = "dt"
    description: str = ""

# ★ 参考答案
电商_ODS_TABLES = {
    "ods_order": ODSTable(
        name="ods_order",
        source_system="mysql_order_center",
        ingest_method="binlog",
        description="用户订单表（来自 MySQL 订单中心 Binlog）",
    ),
    "ods_user_track": ODSTable(
        name="ods_user_track",
        source_system="sdk_analytics",
        ingest_method="sdk",
        description="用户行为轨迹（埋点 SDK 实时上报）",
    ),
    "ods_inventory": ODSTable(
        name="ods_inventory",
        source_system="wms_system",
        ingest_method="api_log",
        description="库存表（WMS 仓库系统 API 同步）",
    ),
}

```text

---

---

---

### L103
**分类：** 数据仓库
**题目：** 请讲讲分层数据仓库架构设计与 DDL中的DWD 层：清洗不聚合（40min）
**参考答案：** ### 3.1 DWD 层对 ODS 做了什么

打开 `src/data/warehouse/dwd_layer.py`，看 `clean_application()` 方法的 6 个步骤：


```text
Step 1: 必填检查 → user_id 为空扣 30 分
Step 2: 金额修正 → 负数清零、空值填 0
Step 3: 标准化   → product_type: cash_loan → CASH_LOAN
Step 4: 脱敏     → 姓名: 黄敏 → 黄*
Step 5: 收入修正 → 空值填 0
Step 6: 隔离     → dq_score < 60 的不入下游

```text
**关键：DWD 层"清洗但不聚合"**

- ODS 一行 = DWD 一行（行数不变）
- 只是这一行的内容变干净了、变安全了
- 聚合是 DWS 层的事

### 3.2 阅读 DDL 对比

打开 `config/ddl/01_ods_tables.sql` 和 `config/ddl/02_dwd_tables.sql`，对比同一列的 COMMENT 变化：


```sql
-- ODS:
user_name STRING COMMENT '★ 用户真实姓名(明文PII)'

-- DWD:
user_name STRING COMMENT '★ 已脱敏: 黄敏→黄*'

```text
COMMENT 的变化 = 数据在层间流转的"日志"。

---

---

---

### L104
**分类：** 数据仓库
**题目：** 请讲讲分层数据仓库架构设计与 DDL中的DWS 层：聚合建模（30min）
**参考答案：** ### 4.1 粒度变化

这是最关键的概念。打开 `src/data/warehouse/dws_layer.py` 第 44 行：


```text
输入: DWD 明细（3 张表，不同粒度）
  dwd_application: 500 行（一行一个申请）
  dwd_behavior:    5000 行（一行一个行为事件）
  dwd_repayment:   500 行（一行一个还款记录）

输出: DWS 宽表（1 张表，统一粒度）
  user_risk_feature_wide: ~450 行（一行一个用户一天）

```text

```python
# 第 84-88 行 — 三路聚合再合并
wide_table = (
    profile_features                   # 申请表 → 6 个特征
    .merge(behavior_features,          # 行为表 → 6 个特征
           on='user_id', how='left')   # ★ left join: 保留新用户
    .merge(repayment_features,         # 还款表 → 5 个特征
           on='user_id', how='left')
)
wide_table[numeric_cols] = wide_table[numeric_cols].fillna(0)

```text
**为什么先聚合再 join，而不是先 join 再聚合？**


```text
先 join 再聚合（错误）:
  申请表 5行 × 行为表 100行 = 500行 → 聚合时 COUNT 被放大到 500

先聚合再 join（正确）:
  申请表 → 聚合 → 1行  \
  行为表 → 聚合 → 1行  → join → 1行（无膨胀）
  还款表 → 聚合 → 1行  /

```text
### 4.2 阅读 DDL

打开 `config/ddl/03_dws_wide_table.sql`，观察 COMMENT 怎么写：


```sql
night_ops_ratio_30d  DOUBLE COMMENT '★ 近30天深夜操作占比(22-05时)。风控强特征。>60%→高度可疑',
on_time_rate         DOUBLE COMMENT '★ 按时还款率=1-逾期次/总次。新用户=1.0。3笔2逾期→0.33→高风险',

```text
COMMENT 里写了三个信息：**含义 + 业务判断 + 风险方向**。这不是数据工程师一个人的事——是和业务方、AI 工程师一起确认的。

---

---

---

### L105
**分类：** 数据仓库
**题目：** 请讲讲分层数据仓库架构设计与 DDL中的ADS 层：数据产品（30min）
**参考答案：** 打开 `config/ddl/04_ads_tables.sql`，看三种数据产品的设计：


```text
ads_training_samples    → 消费者: XGBoost 模型训练   格式: Parquet
ads_model_monitor_daily → 消费者: Grafana 监控大盘   格式: CSV
ads_portfolio_analysis  → 消费者: 风控报表/BI        格式: JSON

```text
**核心原则：每个 ADS 表对应一个明确的消费者。不是"数据都有了你们自己查"，而是"你们要什么我给你们什么"。**

---

---

---

### L106
**分类：** 数据仓库
**题目：** 请讲讲分层数据仓库架构设计与 DDL中的DDL 写作规范（30min）
**参考答案：** ### 6.1 生产级 DDL 必须包含的元素


```sql
CREATE TABLE IF NOT EXISTS {layer}.{table_name} (
    col1  TYPE  COMMENT '含义。格式/阈值/风险方向',
    ...
    dt    STRING COMMENT '分区键 YYYY-MM-DD'
)
COMMENT '表的业务描述'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_system' = 'mysql_xxx',     -- 数据从哪个系统来
    'ingest_method' = 'binlog',        -- 怎么接入的
    'pii_columns' = 'col1,col2',       -- 哪些列是敏感信息
    'retention_days' = '90',           -- 保留多少天
    'data_owner' = '风控团队',         -- 谁对这表负责
    'update_frequency' = 'daily'       -- 多久更新一次
);

```text
### 6.2 练习：手写 DDL（30min）

为电商的 `dwd_order` 表写 DDL。要求包含：
- 至少 8 个业务字段
- 每个字段有 COMMENT
- TBLPROPERTIES 包含 source_system、retention_days
- 标注 PII 列


```sql
-- ★ 参考答案
CREATE TABLE IF NOT EXISTS dwd.dwd_order (
    order_id          STRING    COMMENT '订单ID。原始为空→MISSING',
    user_id           STRING    COMMENT '用户ID。必填字段',
    pay_amount        DOUBLE    COMMENT '支付金额(元)。已修正: 负数→0',
    shipping_address  STRING    COMMENT '★ 收货地址(已脱敏: 北京市朝阳区→北京市**区)',
    phone             STRING    COMMENT '★ 手机号(已脱敏: 138****0000)',
    status            STRING    COMMENT '订单状态(已标准化): PAID/SHIPPED/DELIVERED/RETURNED/UNKNOWN',
    category          STRING    COMMENT '商品品类: 电子/服装/食品/图书',
    province          STRING    COMMENT '省份(从address解析)。未知→UNKNOWN',
    order_time        TIMESTAMP COMMENT '下单时间',
    dq_score          INT       COMMENT '★ 数据质量评分 0-100。≥60通过',
    dt                STRING    COMMENT '分区键 — 下单日期 YYYY-MM-DD'
)
COMMENT '清洗后的电商订单明细 — dq_score<60隔离'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_table' = 'ods.ods_order',
    'transformation' = 'clean_order()',
    'pii_columns' = 'shipping_address,phone',
    'retention_days' = '365',
    'update_frequency' = 'daily'
);

```text

---

---

---

### L107
**分类：** 数据仓库
**题目：** 请讲讲分层数据仓库架构设计与 DDL中的今日检查清单
**参考答案：** - [ ] 能画出四层架构图，标注每层的粒度和职责
- [ ] 能解释 ODS 为什么不做清洗（三个理由）
- [ ] 能解释"先聚合再 join vs 先 join 再聚合"的区别
- [ ] 能写出带 COMMENT 和 TBLPROPERTIES 的生产级 DDL
- [ ] 完成了电商 ODS 表定义代码
- [ ] 完成了 dwd_order 的 DDL 编写

### 延伸思考

1. 如果公司只有 3 张源表，还需要四层吗？能不能合并 ODS+DWD 为一层？
2. DWS 层的 left join 在什么情况下会导致数据膨胀？（提示：一对多关系）

---

---

### L108
**分类：** 数据仓库
**题目：** 为什么简单的"通过/不通过"不够用？（20min）
**参考答案：** ### 1.1 两种世界观


```text
二元判定（简单但粗糙）:
  数据有一条空字段 → 整条丢弃 ❌
  问题: 丢了太多"部分可用"的数据

扣分制（精细但需要设计）:
  数据有一条空字段 → 扣分，达到隔离线才丢弃
  优势: 保留"大部分 OK，小部分有问题"的数据

```text
**实际案例对比**：


```text
用户 A: user_id=OK, apply_amount=OK, product_type=OK, phone=OK, occupation=空
  二元判定: "有空字段 → 丢弃" ❌
  扣分制:   扣 5 分 → dq_score=95 → 通过 ✓（phone 可用，只是职业未知）

用户 B: user_id=空, apply_amount=OK, product_type=OK
  二元判定: "有空字段 → 丢弃" ✓（确实该丢）
  扣分制:   扣 30 分 → dq_score=70 → 通过（但要注意）

用户 C: user_id=空, apply_amount=负数, product_type=空
  二元判定: "有空字段 → 丢弃" ✓
  扣分制:   扣 30+20+10=60 → dq_score=40 → 隔离 ✓（确实该丢）

```text

---

---

---

### L109
**分类：** 数据仓库
**题目：** 请举例说明项目中的扣分制实现（1h）如何实现？
**参考答案：** ### 2.1 完整阅读 `clean_application()`

打开 `src/data/warehouse/dwd_layer.py` 第 101-186 行。逐步骤理解：


```python
def clean_application(self, ods_df: pd.DataFrame) -> tuple[pd.DataFrame, DQReport]:
    df = ods_df.copy()
    df['dq_score'] = 100  # ★ 初始满分

    # Step 1: 必填检查 — 缺主键 → 扣 30 分
    # 为什么是 30？30 = 刚好让一条记录处于"及格线边缘"
    # 再有任何问题就隔离。只扣 10 分 → 太宽松，三个必填全空才隔离。
    for field in ['user_id', 'application_id', 'apply_amount']:
        mask = df[field].isna()
        df.loc[mask, 'dq_score'] -= 30

    # Step 2: 金额合法性 — 负数/空 → 扣 20 分
    # 为什么是 20？金额重要但不是"无它不可用"。
    # 单独金额异常(80分)不隔离，叠加其他问题会隔离。
    amount_mask = pd.to_numeric(df['apply_amount'], errors='coerce')
    df.loc[amount_mask <= 0, 'dq_score'] -= 20
    df['apply_amount'] = amount_mask.fillna(0).clip(lower=0)  # 修正

    # Step 3: 产品类型标准化 — 未知 → 扣 10 分
    # 为什么只扣 10？产品类型不是核心风控字段。
    # 缺失了标记 UNKNOWN 即可，不影响模型。
    df['product_type'] = df['product_type'].map(valid_products).fillna('UNKNOWN')

    # Step 4: PII 脱敏 ★
    df['user_name'] = df['user_name'].apply(masker.mask_name)
    df['id_card'] = df['id_card'].apply(masker.mask_id_card)

    # Step 5: 隔离 — dq_score < 60
    quarantine_mask = df['dq_score'] < 60
    df_clean = df[~quarantine_mask]

    # Step 6: 质量报告
    report = DQReport(
        total_rows=n_total,
        passed_rows=len(df_clean),
        quarantined_rows=len(df) - len(df_clean),
        null_rate_by_column={...},
        invalid_rate_by_column={...},
    )
    return df_clean, report

```text
### 2.2 扣分权重的设计逻辑

| 分值 | 含义 | 示例 | 设计理由 |
|------|------|------|---------|
| -30 | 致命缺陷 | user_id 为空 | 缺主键 → 记录几乎无用 |
| -20 | 严重缺陷 | 金额为负数 | 核心字段异常，但可修正 |
| -10 | 轻微缺陷 | 产品类型未知 | 非核心字段，标记即可 |
| -5 | 提示性 | 收入为 0 | 可能真实（学生/无业） |

**黄金规则**：一个致命缺陷(-30) + 一个严重缺陷(-20) + 一个轻微缺陷(-10) = dq_score=40 → 隔离。刚好让"有明显问题"的数据被隔离。

### 2.3 阅读 DQReport 结构

打开 `src/data/warehouse/dwd_layer.py` 第 33-42 行：


```python
@dataclass
class DQReport:
    table_name: str          # 哪张表
    total_rows: int          # 总行数 — 数据量监控
    passed_rows: int         # 通过数 — 可用率 = passed/total
    quarantined_rows: int    # 隔离数 — 隔离率突增 = 源系统异常
    null_rate_by_column: dict[str, float]      # 按列看空值
    invalid_rate_by_column: dict[str, float]   # 按列看异常

```text
**为什么这 5 个字段就够？**

- `total_rows`：数据量突然掉一半 → 源系统挂了
- `quarantined_rows/total_rows`：隔离率从 5% 突增到 30% → 源系统数据质量急剧恶化
- `null_rate_by_column`：某一列空值率突然升高 → 该字段的采集可能出了问题
- `invalid_rate_by_column`：区分"空"和"错"——空是缺失，错是有但不对

---

---

---

### L110
**分类：** 数据仓库
**题目：** 请讲讲数据质量体系 — 扣分制 vs 二元判定中的动手练习（1.5h）
**参考答案：** ### 练习 1：为电商订单写清洗函数（1h）


```python
import pandas as pd
import numpy as np

def clean_order(ods_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    为电商订单表写清洗逻辑。

    清洗规则：
    1. order_id/user_id 为空 → 扣 30 分（主键缺失）
    2. pay_amount <= 0 或 > 1000000 → 扣 20 分（异常金额）
    3. province 无法从 address 解析 → 扣 10 分
    4. 联系方式脱敏
    5. dq_score < 60 → 隔离
    """
    df = ods_df.copy()
    df['dq_score'] = 100

    # ★ 参考答案
    # 1. 必填检查
    df.loc[df['order_id'].isna(), 'dq_score'] -= 30
    df.loc[df['user_id'].isna(), 'dq_score'] -= 30
    # 2. 金额异常
    df.loc[df['pay_amount'] <= 0, 'dq_score'] -= 20
    df.loc[df['pay_amount'] > 1000000, 'dq_score'] -= 20
    # 3. 地址标准化（简化: 若 address 有值但无法解析 province 则扣分）
    df.loc[df['address'].notna(), 'dq_score'] -= 10  # 简化版
    # 4. 联系方式脱敏
    df['phone'] = df['phone'].fillna('MISSING').apply(
        lambda x: x[:3] + '****' + x[-4:] if x != 'MISSING' else x
    )
    # 5. 填充默认值
    df[['order_id', 'user_id']] = df[['order_id', 'user_id']].fillna('MISSING')
    df['pay_amount'] = df['pay_amount'].fillna(0).clip(lower=0)

    # 隔离
    df_clean = df[df['dq_score'] >= 60]
    df_quarantine = df[df['dq_score'] < 60]

    # 生成报告
    report = {
        "total": len(df),
        "passed": len(df_clean),
        "quarantined": len(df_quarantine),
    }
    return df_clean, report


# 测试
test_orders = pd.DataFrame({
    'order_id': ['O1', 'O2', None, 'O4'],
    'user_id': ['U1', None, 'U3', 'U4'],
    'pay_amount': [299, -50, 299, 2000000],
    'address': ['北京市朝阳区', '上海市', '广州市', None],
    'phone': ['13800001111', '13900002222', None, '13700004444'],
})
clean_df, report = clean_order(test_orders)
print(f"通过: {report['passed']}/{report['total']}")
print(f"隔离: {report['quarantined']}")
# 预期: O3 隔离 (user_id 空+phone 空, dq_score=100-30-0-0=70? 不对, 扣30=70≥60通过)
# 实际分析: O3: order_id 空(-30) → dq=70 ✓; O2: user_id 空(-30)+pay_amount=-50(-20) → dq=50 < 60❌隔离

```text
### 练习 2：设计扣分权重（30min）

针对以下"医疗检验结果表"，设计扣分规则：


```text
字段：patient_id, test_time, glucose(血糖), blood_pressure(血压), lab_tech(检验师)

问题场景：
A. patient_id 为空 → 扣 30 分（理由: 患者ID是主键，缺失=记录不可用，等同于信贷的user_id为空）
B. glucose = 0（不可能，活人血糖不会是 0）→ 扣 20 分（理由: 核心检验字段异常，
   但可修正为NULL标记"无效"，单独异常(80分)不隔离，叠加其他问题隔离）
C. lab_tech 为空 → 扣 5 分（理由: 检验师姓名对诊断分析不重要，不影响医学判断，
   只影响追溯和审计，单独缺失几乎不影响数据质量）

```text

---

---

---

### L111
**分类：** 数据仓库
**题目：** 请讲讲数据质量体系 — 扣分制 vs 二元判定中的跨业务思考（30min）
**参考答案：** ### 场景：物流数据"包裹重量为 0"


```text
包裹重量 = 0 有两种可能：
1. 真的没称重（数据缺失）→ 应该修正还是隔离？
2. 信封/文件类（实际重量接近 0）→ 0 是否合理？

作为数据仓库工程师，你需要判断：
- 这个字段对下游什么用途？（运费计算？→ 很关键。统计分析？→ 不太关键）
- 区分"数据缺失"和"数据为 0"的方法？（加一个 is_weighed 标记列）

```text

---

---

---

### L112
**分类：** 数据仓库
**题目：** 请讲讲数据质量体系 — 扣分制 vs 二元判定中的今日要点
**参考答案：** ```text
扣分制的三个核心决策:
  1. 扣分阈值: 致命(-30) / 严重(-20) / 轻微(-10) / 提示(-5)
  2. 隔离线: dq_score < 60 → 隔离（一个致命 + 一个严重 + 一个轻微 = 40 < 60）
  3. 质量报告: 不是打印日志，是结构化数据（DQReport）供监控系统消费

扣分权重不是拍脑袋:
  → 需要和下游消费者（AI工程师、BI分析师）沟通
  → 哪些字段缺失"还行"，哪些"绝对不能丢"

```text

---

---

---

### L113
**分类：** 数据仓库
**题目：** 请讲讲维度建模 + 宽表设计中的**核心概念**：粒度（30min）
**参考答案：** ### 1.1 粒度决定了宽表能回答什么问题


```text
粒度 A: 用户（每个用户一行）
  能回答: "张三这个人的信用评分是多少？"
  不能回答: "张三上个月和这个月的评分差了多少？"

粒度 B: 用户 × 日期（每人每天一行）
  能回答: "张三月度信用变化趋势"
  能回答: "张三今天的评分是多少"

粒度 C: 用户 × 申请（每人每次申请一行）
  能回答: "张三第3次申请和第5次申请有什么不同"
  不能回答: 粒度 B 能回答的聚合问题（需要二次聚合）

```text
**项目的选择：粒度 = 用户 × 日期**

为什么？信贷风控需要在**时间维度上观察用户变化**——一个人收入在涨还是在跌？逾期次数在增加还是在减少？

### 1.2 粒度选择的黄金法则


```text
选择能回答"最有价值的业务问题"的最粗粒度。

最粗 = 数据量可控，存储和查询成本低
有价值 = 能支撑核心分析场景

反例（太细）: 粒度 = 用户 × 分钟 → 数据量爆炸，但没有人需要分钟级信用评分
反例（太粗）: 粒度 = 城市 → 一个城市只有一行，无法做个人信用评估

```text

---

---

---

### L114
**分类：** 数据仓库
**题目：** 请讲讲维度建模 + 宽表设计中的项目宽表：从 3 张 DWD 到 1 张 DWS（1h）
**参考答案：** ### 2.1 三路聚合 → left join → fillna

打开 `src/data/warehouse/dws_layer.py` 第 44-99 行 `build_wide_table()`：


```python
def build_wide_table(self, dwd_application, dwd_behavior, dwd_repayment, dt):
    # Step 1: 三路分别聚合（各自压缩到用户粒度）
    profile_features = self._build_profile_features(dwd_application)    # → 6列
    behavior_features = self._build_behavior_features(dwd_behavior, dt)  # → 6列
    repayment_features = self._build_repayment_features(dwd_repayment)   # → 5列

    # Step 2: 三表 left join（保留新用户）
    wide_table = (
        profile_features
        .merge(behavior_features, on='user_id', how='left')    # ★ left
        .merge(repayment_features, on='user_id', how='left')   # ★ left
    )

    # Step 3: 缺失值填充
    wide_table[numeric_cols] = wide_table[numeric_cols].fillna(0)

    return wide_table  # 450行 × 19列

```text
### 2.2 为什么 left join 而不是 inner join？


```text
场景: 新用户 user_X，刚注册，只有申请记录
  dwd_application: user_X 有 1 行
  dwd_behavior:    user_X 无（从未打开过 App）
  dwd_repayment:   user_X 无（从未借过钱）

inner join:
  user_X → 被丢弃 ❌ → 训练集里没有新用户 → 模型不认识新用户

left join:
  user_X → 保留 ✓ → 行为特征=0, 还款特征=0 → 模型能学到"全0=新用户"

```text
### 2.3 聚合函数选择：为什么 income 取 MAX？

打开 `_build_profile_features()` 第 103-131 行：


```python
agg = app_df.groupby('user_id').agg(
    monthly_income=('monthly_income', 'max'),  # ← 为什么是 max？
)

# 场景: 用户填了 3 次申请，收入分别为 8000, 8000, 5000
# max = 8000 → "取用户最诚实的申报"（据说高的是真的）
# mean = 7000 → "被 5000 拉低了"
# min = 5000 → "用户可能想看起来穷一点"
# 选择 max = 偏保守的乐观估计（相信用户最高的那次申报）

```text

---

---

---

### L115
**分类：** 数据仓库
**题目：** 请讲讲维度建模 + 宽表设计中的动手练习（2.5h）
**参考答案：** ### 练习 1：先聚合再 Join vs 先 Join 再聚合（40min）

**为什么这是最重要的练习？** 面试必问。用数据证明"先聚合再 Join"和"先 Join 再聚合"的区别。


```python
import pandas as pd
import numpy as np

# ── 构造测试数据 ──
# 用户 u1: 有 3 笔订单（信贷的"申请记录"）、10 条行为日志
# 模拟"一个用户有多个记录，关联后会产生笛卡尔积"的问题

dwd_application = pd.DataFrame({
    'user_id': ['u1', 'u1', 'u1', 'u2', 'u2'],
    'apply_amount': [3000, 5000, 8000, 2000, 4000],
    'product': ['A', 'B', 'A', 'A', 'C'],
})

dwd_behavior = pd.DataFrame({
    'user_id': ['u1', 'u1', 'u1', 'u1', 'u1',
                'u1', 'u1', 'u1', 'u1', 'u1',  # u1 有 10 条行为
                'u2', 'u2', 'u2'],              # u2 有 3 条行为
    'event_type': ['page_view'] * 5 + ['click'] * 5 + ['page_view'] * 3,
})

# ★ 错误写法: 先 Join 再聚合
# 对每个用户: 3 条申请 × 10 条行为 = 30 行中间数据
merged_wrong = dwd_application.merge(dwd_behavior, on='user_id')
result_wrong = merged_wrong.groupby('user_id').agg(
    total_apply_amount=('apply_amount', 'sum'),
    behavior_cnt=('event_type', 'count'),
)
print("❌ 先 Join 再聚合:")
print(result_wrong)
print("  u1: apply_amount = ", 3000+5000+8000, "× 10 次 =", (3000+5000+8000)*10,
      "← 每行申请记录被重复了 10 次!")
print()

# ★ 正确写法: 先聚合再 Join
profile_agg = dwd_application.groupby('user_id').agg(
    apply_amount_sum=('apply_amount', 'sum'),
    total_orders=('product', 'count'),
)
behavior_agg = dwd_behavior.groupby('user_id').agg(
    behavior_cnt=('event_type', 'count'),
)
result_correct = profile_agg.merge(behavior_agg, on='user_id', how='left')
print("✅ 先聚合再 Join:")
print(result_correct)
print("  u1: apply_amount = 16000 (3 笔之和, 没有被放大)")
print()

# ── 对比关键数据 ──
print("=" * 60)
print("对比表:")
print(f"  方法        | u1 apply_amount | 是否正确")
print(f"  先Join再聚合 | 16000 × 10 = {result_wrong.loc['u1', 'total_apply_amount']:.0f} | ❌ 被放大")
print(f"  先聚合再Join | 16000          | ✅ 正确")

```text
**改写为你的项目宽表代码**：

打开 `src/data/warehouse/dws_layer.py` 第 84-88 行，确认项目使用"先聚合再 Join"模式：


```python
# 项目代码确认:
wide_table = (
    profile_features          # ← 已经 groupby 聚合过（每用户一行）
    .merge(behavior_features, on='user_id', how='left')   # ← 1:1 关联，无膨胀
    .merge(repayment_features, on='user_id', how='left')  # ← 1:1 关联，无膨胀
)

```text
📌 **关键理解**：`_build_profile_features` / `_build_behavior_features` / `_build_repayment_features`
这三个方法内部已经做了 `groupby('user_id')`，所以输出都是"每用户一行"→ merge 变成 1:1 关联，不会产生笛卡尔积。

---

### 练习 2：动手运行项目宽表，观察数据（30min）


```bash
# 在项目目录下执行
cd credit_risk_control_system

python3 -c "
import pandas as pd
from pathlib import Path

base = Path('data/warehouse')
dt = '2026-07-01'

# 查看 DWD 明细表: 行为日志
behavior = pd.read_parquet(base / 'dwd' / f'dt={dt}' / 'dwd_user_behavior.parquet')
print(f'DWD 行为日志: {len(behavior)} 行')

# 找一个人多的用户
top_user = behavior['user_id'].value_counts().index[0]
user_beh = behavior[behavior['user_id'] == top_user]
print(f'用户 {top_user}: {len(user_beh)} 条行为记录')

# 查看这个人对应的 DWS 宽表行
dws = pd.read_parquet(base / 'dws' / f'dt={dt}' / 'user_risk_feature_wide.parquet')
user_dws = dws[dws['user_id'] == top_user]
print(f'宽表: {len(user_dws)} 行')
print(f'特征: page_view_cnt_7d={int(user_dws[\"page_view_cnt_7d\"].values[0])}, apply_cnt_7d={int(user_dws[\"apply_cnt_7d\"].values[0])}')
"

```text
预期输出：


```text
DWD 行为日志: 5000 行
用户 user_000xxx: 16 条行为记录
宽表: 1 行
特征: page_view_cnt_7d=5, apply_cnt_7d=1

```text
📌 **关键验证**：该用户 16 条行为日志 → DWS 宽表只有 1 行（用户粒度）。16 → 1 就是聚合的压缩效果。

---

### 练习 3：为电商写用户消费画像宽表（1h）

✅ **这次带参考答案，先自己写，写完后对照检查。**


```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ══════════════════════════════════════
# 模拟电商数据
# ══════════════════════════════════════

np.random.seed(42)
ref_date = '2026-07-07'

# dwd_order: 订单明细 (用户×订单粒度)
dwd_order = pd.DataFrame({
    'user_id': ['u1', 'u1', 'u1', 'u2', 'u2', 'u3'],
    'order_id': ['o1', 'o2', 'o3', 'o4', 'o5', 'o6'],
    'pay_amount': [299, 599, 1299, 99, 199, None],  # u3 金额为空！
    'category': ['电子', '服装', '电子', '食品', '食品', '图书'],
    'status': ['paid', 'paid', 'returned', 'paid', 'paid', 'paid'],
    'order_time': pd.to_datetime([
        '2026-07-05 10:00', '2026-07-01 14:00', '2026-07-06 09:00',
        '2026-06-15 08:00', '2026-07-03 11:00', '2026-07-07 12:00',
    ]),
})

# dwd_cart: 购物车行为 (用户×行为粒度)
dwd_cart = pd.DataFrame({
    'user_id': ['u1', 'u1', 'u1', 'u1', 'u2', 'u2', 'u3', 'u3'],
    'item_id': ['i1', 'i2', 'i3', 'i4', 'i5', 'i6', 'i7', 'i8'],
    'action': ['add', 'add', 'add', 'remove', 'add', 'add', 'add', 'add'],
    'action_time': pd.to_datetime([
        '2026-07-01 10:00', '2026-07-02 14:00', '2026-07-06 09:00',
        '2026-07-06 10:00', '2026-06-20 08:00', '2026-07-05 11:00',
        '2026-07-02 08:00', '2026-07-07 12:00',
    ]),
})

# ─────────────────────────────────────
# ★ 你的任务: 完成以下函数
# ─────────────────────────────────────

def build_user_consumption_wide(dwd_order, dwd_cart, ref_date):
    """
    电商用户消费画像宽表。

    输入: dwd_order(用户×订单), dwd_cart(用户×行为)
    输出: 宽表(用户粒度)

    要求至少 8 个特征:
    [订单聚合]
    - avg_order_amount: 平均金额
    - order_cnt_30d: 近30天订单数
    - return_rate: 退货率 = 退货订单/总订单
    - favorite_category: 最爱品类 (购买最多的品类)

    [购物车聚合]
    - cart_add_cnt_7d: 近7天加购次数
    - cart_abandon_rate: 加购但未购买的比例 (参考: 没有购买的加购)
    - total_cart_items: 历史所有加购过的商品数

    [衍生]
    - conversion_rate: 购买数/加购数 (衡量从意愿到行动的转化)

    约束:
    1. 先分别 groupby 聚合
    2. left join 关联
    3. fillna(0) 处理缺失
    """
    ref = pd.to_datetime(ref_date)

    # ★ 1. 订单聚合 ← 从下面一行开始写
    order_agg = None
    order_agg = dwd_order.groupby('user_id').agg(
        avg_order_amount=('pay_amount', 'mean'),
        order_cnt_30d=('order_id', lambda x: ...),  # TODO: 过滤近30天
        return_rate=('status', lambda x: ...),       # TODO: 退货比例
        favorite_category=('category', lambda x: x.mode().iloc[0]
                          if len(x.mode()) > 0 else 'unknown'),
        total_spend=('pay_amount', 'sum'),
    ).reset_index()

    # ★ 2. 购物车聚合
    cart_agg = None
    # TODO: 实现购物车行为聚合

    # ★ 3. left join
    wide_table = order_agg.merge(cart_agg, on='user_id', how='left')

    # ★ 4. fillna
    numeric_cols = wide_table.select_dtypes(include=[np.number]).columns
    wide_table[numeric_cols] = wide_table[numeric_cols].fillna(0)

    return wide_table


# ─────────────────────────────────────
# 参考答案（写完后再看）
# ─────────────────────────────────────

def build_user_consumption_wide_answer(dwd_order, dwd_cart, ref_date):
    """参考答案 — 先自己写，写完后对照"""
    ref = pd.to_datetime(ref_date)
    in_30d = dwd_order['order_time'] >= ref - timedelta(days=30)

    # 1. 订单聚合
    order_agg = dwd_order.groupby('user_id').agg(
        avg_order_amount=('pay_amount', 'mean'),
        order_cnt_30d=('order_id', lambda x: (dwd_order.loc[x.index, 'order_time'] >= ref - timedelta(days=30)).sum()),
        return_rate=('status', lambda x: (x == 'returned').mean()),
        favorite_category=('category', lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'unknown'),
        total_spend=('pay_amount', lambda x: x.fillna(0).sum()),
    ).reset_index()

    # 2. 购物车聚合
    cart_agg = dwd_cart.groupby('user_id').agg(
        cart_add_cnt_7d=('action_time', lambda x: (x >= ref - timedelta(days=7)).sum()),
        total_cart_items=('item_id', 'nunique'),
        cart_abandon_rate=('action', lambda x: (x == 'remove').mean()),
    ).reset_index()

    # 3. left join
    wide = order_agg.merge(cart_agg, on='user_id', how='left')
    wide['conversion_rate'] = wide['order_cnt_30d'] / wide['cart_add_cnt_7d'].replace(0, 1)

    numeric_cols = wide.select_dtypes(include=[np.number]).columns
    wide[numeric_cols] = wide[numeric_cols].fillna(0)

    return wide


# ─────────────────────────────────────
# 执行验证
# ─────────────────────────────────────

result = build_user_consumption_wide_answer(dwd_order, dwd_cart, ref_date)
print("\n✅ 宽表结果:")
print(result[['user_id', 'avg_order_amount', 'order_cnt_30d',
              'return_rate', 'favorite_category', 'cart_add_cnt_7d']].to_string(index=False))

# 预期:
#   u1: avg=732.3, 订单3, 退货率33%, 最爱电子, 加购4
#   u2: avg=149,   订单2, 退货率0%,  最爱食品, 加购2
#   u3: avg=0,     订单1, 退货率0%,  最爱图书, 加购2

```text

---

### 练习 4：left join 数据膨胀实验（20min）


```python
# 这个练习演示: 如果不先聚合就 Join，数据会膨胀成什么样

import pandas as pd

# 构造一个用户有 5 个地址、3 个设备
user_profile = pd.DataFrame({
    'user_id': ['u1', 'u1', 'u1', 'u1', 'u1'],  # 5 条地址记录
    'address': ['北京', '上海', '广州', '深圳', '杭州'],
    'cnt': [1, 2, 3, 4, 5],
})
user_device = pd.DataFrame({
    'user_id': ['u1', 'u1', 'u1'],   # 3 条设备记录
    'device': ['iPhone', 'Android', 'iPad'],
    'cnt': [10, 20, 30],
})

# ═══ 错误: 直接 Join ═══
merged_bad = user_profile.merge(user_device, on='user_id', how='inner')
print(f"直接 Join: {len(merged_bad)} 行")  # 5×3 = 15 行！
print(merged_bad[['address', 'device']].head())

# ═══ 正确: 先聚合再 Join ═══
profile_agg = user_profile.groupby('user_id').agg(
    address_list=('address', lambda x: ','.join(x)),
    max_cnt=('cnt', 'max'),
).reset_index()

device_agg = user_device.groupby('user_id').agg(
    device_list=('device', lambda x: ','.join(x)),
    max_device_cnt=('cnt', 'max'),
).reset_index()

merged_good = profile_agg.merge(device_agg, on='user_id')
print(f"\n先聚合再 Join: {len(merged_good)} 行")  # 1 行 ✅
print(merged_good[['address_list', 'max_cnt', 'device_list']].to_string())

# 结论:
# 直接 Join: user_profile(5行) × user_device(3行) = 15 行
#    → cnt_x 被复制了 3 次 (1→1,2→2,3→3,4→4,5→5 各出现 3 遍)
#    → cnt_y 被复制了 5 次 (10,20,30 各出现 5 遍)
#    → 如果你对 cnt_x 取 sum, 得到 1+2+3+4+5 = 15 ≠ 正确值 15×3=45
# 先聚合再 Join: 每个表先压缩到 1 行 → Join → 1 行 ✅

```text

---

### 练习 5：选择正确的聚合函数（30min）


```python
# 完成下表 — 注意: 没有"标准答案"，选择取决于业务含义

选择题 = {
    "用户月收入(多次填写不同值)": {
        "选项": ["AVG", "MAX", "MIN", "LAST"],
        "你的选择": "?",
        "理由": "?",
        "参考答案": {
            "选择": "MAX",
            "理由": "信贷行业假设用户最高申报值最接近真实收入。用 AVG 会被低报的收入拉低估计，用 MIN 过度悲观。"
        }
    },
    "用户退货率": {
        "选项": ["AVG(status=='returned')",
                 "SUM(returned)/COUNT(total)",
                 "MAX(returned)"],
        "你的选择": "?",
        "理由": "?",
        "参考答案": {
            "选择": "SUM(returned)/COUNT(total)",
            "理由": "退货率 = 退货订单/总订单, 是比率不是平均值（用户有 10 个订单，3 个退货→率=0.3）"
        }
    },
    "用户最常浏览的品类": {
        "选项": ["MODE(众数)", "MAX(COUNT)", "FIRST"],
        "你的选择": "?",
        "理由": "?",
        "参考答案": {
            "选择": "MODE",
            "理由": "众数 = 出现次数最多的值，恰好是'最常浏览'的语义。FIRST 是随机第一条，无意义。"
        }
    },
    "用户最近一次登录时间": {
        "选项": ["MAX", "LAST", "FIRST"],
        "你的选择": "?",
        "理由": "?",
        "参考答案": {
            "选择": "MAX",
            "理由": "MAX(datetime) = 最大值 = 最近时间。LAST 依赖于数据排序，不稳定。"
        }
    },
    "用户历史总消费金额": {
        "选项": ["SUM", "AVG", "MAX"],
        "你的选择": "?",
        "理由": "?"
    },
    "用户使用的设备数": {
        "选项": ["COUNT", "COUNT DISTINCT", "NUNIQUE"],
        "你的选择": "?",
        "理由": "?"
    },
    "用户首次注册渠道": {
        "选项": ["FIRST", "MIN(时间)", "MODE"],
        "你的选择": "?",
        "理由": "?"
    },
}

```text

---

---

---

### L116
**分类：** 数据仓库
**题目：** 请讲讲维度建模 + 宽表设计中的跨业务思考（30min）
**参考答案：** ### 粒度设计练习

为以下业务选择宽表粒度：

| 业务 | 分析需求 | 建议粒度 | 理由 |
|------|---------|---------|------|
| 信贷风控 | 实时信用评估 | 用户×日期 | 每天评估一次，保留时间变化 |
| 电商大促监控 | 每小时 GMV | 小时级 | 需要秒级刷新，10分钟数据太粗 |
| 网约车司机管理 | 每周司机活跃度 | 司机×周 | 周度考核，不需要每天粒度 |
| 游戏玩家 | 每次登录后的行为分析 | 玩家×会话 | 关注每次登录的"单次行为序列" |

**扩展思考：存算分离对粒度的影响**


```text
传统数仓: 粒度越细 → 存储越大 → 成本越高 → 倾向于选粗粒度
湖仓一体(Iceberg): 存储成本低 → 粒度可以更细 → 保留更多可能性

问题: 如果存储不要钱，你应该选最细的粒度吗？
答案: 不一定。太细的粒度(如用户×秒)会让查询变得非常慢，
      即使存储成本可以忽略，查询性能也无法接受。
      所以粒度选择还要考虑查询模式。

```text

---

---

---

### L117
**分类：** 数据仓库
**题目：** 请讲讲数据血缘 + SchemaRegistry 元数据管理中的没有血缘的数仓 = 没有地图的城市（20min）
**参考答案：** ```text
场景：DWD 层的 apply_amount 列类型从 INT 改成 DOUBLE
  问题：哪些下游表会受影响？

有血缘 → 秒级溯源:
  apply_amount (dwd_application)
    → apply_amount_avg (dws.user_risk_feature_wide)
      → 训练样本表 ads_training_samples
        → XGBoost 模型的特征列
  结论：模型需要重训，因为特征类型变了

没有血缘 → 灾难:
  让各团队自己去排查 → 3 天后才发现模型评分异常

```text

---

---

---

### L118
**分类：** 数据仓库
**题目：** 请讲讲数据血缘 + SchemaRegistry 元数据管理中的SchemaRegistry：数据仓库的"目录服务"（1h）
**参考答案：** ### 2.1 核心代码

打开 `src/data/schema_registry.py`：


```python
class SchemaRegistry:
    """
    三大职责:
    1. 加载: 从 config/schemas/*.yaml 读取表结构
    2. 写入: 执行 ETL 时将 _TABLE_SCHEMA.json 写入数据目录
    3. 查询: 提供统一的 get_table() / list_tables() 接口
    """

    def __init__(self, config_dir: str = "config"):
        self._tables: dict[str, TableSchema] = {}  # 核心: 内存中的表目录
        self._load_all()  # 启动时一次性加载所有 schema

    # ═══ 职责1: 加载 YAML 配置 ═══
    def _load_dws(self):
        """加载 DWS 宽表的 schema"""
        path = self.schemas_dir / "dws_wide_table.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)

        for cat_key in ['category_profile', 'category_behavior',
                         'category_repayment']:
            for feat in data['wide_table'][cat_key]['features']:
                columns.append(ColumnDef(
                    name=feat['name'],
                    type=feat.get('type', 'STRING'),
                    description=feat.get('description', ''),
                    aggregation=feat.get('aggregation', ''),  # ← 聚合公式
                    risk_direction=feat.get('risk_direction', ''),  # ← 风险方向
                ))

    # ═══ 职责2: 写入数据目录 ═══
    def write_schema_to_data_dir(self, data_dir, table_name, layer):
        """
        将 _TABLE_SCHEMA_{table}.json 写入数据目录。

        为什么数据目录需要自带 schema？
        - Parquet 有列名和类型，但没有 COMMENT（业务含义）
        - COMMENT 是数仓工程师写的 "近30天深夜操作占比>60%→可疑"
        - 数据被复制/迁移时，schema 跟随 → 知识不丢失
        """
        path = Path(data_dir) / f"_TABLE_SCHEMA_{table_name}.json"
        json.dump(schema.to_dict(), open(path, 'w'), indent=2)

    # ═══ 职责3: 统一查询 ═══
    def get_table(self, layer, table_name):
        return self._tables.get(f"{layer}.{table_name}")

    def list_tables(self, layer=None):
        tables = list(self._tables.values())
        return [t for t in tables if not layer or t.layer == layer]

```text
### 2.2 运行验证


```bash
cd credit_risk_control_system
python3 -c "
from src.data.schema_registry import SchemaRegistry
r = SchemaRegistry()
print(r.print_summary())
print()
# 查一张具体的表
t = r.get_table('dws', 'user_risk_feature_wide')
print(f'宽表: {t.table_name}, {len(t.columns)}列, 主键={t.primary_key}')
for c in t.columns[:3]:
    print(f'  {c.name}: {c.type} — {c.description[:50]}...')
"

```text

---

---

---

### L119
**分类：** 数据仓库
**题目：** 请讲讲数据血缘 + SchemaRegistry 元数据管理中的数据血缘：每列追溯来源（40min）
**参考答案：** ### 3.1 血缘的两种形态

打开 `config/schemas/data_lineage.yaml`：


```yaml
# 形态1: 层间流转（表级血缘）
lineage:
  ods_to_dwd:
    - source: ods_application
      target: dwd_application
      relationship: "1:1 + 新增 dq_score 列"

  dwd_to_dws:
    - sources: [dwd_application, dwd_behavior, dwd_repayment]
      target: dws.user_risk_feature_wide
      relationship: "N:1 聚合"

# 形态2: 宽表列追溯（列级血缘）
wide_table_lineage:
  night_ops_ratio_30d:
    source_column: dwd_user_behavior.event_time
    aggregation: "AVG(hour IN 22-05) WHERE event_time >= ref-30d"

  on_time_rate:
    source_columns: [dwd_repayment.status, dwd_repayment.repayment_id]
    aggregation: "1 - SUM(OVERDUE) / COUNT(*)"

```text
### 3.2 一个特征的完整追溯路径


```text
night_ops_ratio_30d = 0.27
  ↑ DWS 聚合: AVG(hour IN [22,23,0,1,2,3,4,5]) 时间窗口30天
  ← dwd_user_behavior.event_time
    ↑ DWD 继承自 ODS（未转换）
    ← ods_user_behavior.event_time
      ↑ SDK 上报
      ← 客户端 App 埋点代码: trackEvent('page_view', timestamp=now())

```text
### 3.3 练习：画一条血缘链（20min）

在纸上画出 `on_time_rate` 的完整血缘链：


```text
★ 参考答案:

on_time_rate (DWS 特征)
  ↑ AGG: 1 - SUM(status='OVERDUE') / COUNT(*), 新用户=1.0
  ← dwd_repayment.status + dwd_repayment.repayment_id
    ↑ DWD 清洗: status 标准化 overdue→OVERDUE
    ← ods_repayment.status + ods_repayment.repayment_id
      ↑ ODS 镜像: 从 MySQL binlog 1:1 同步
      ← 还款系统 MySQL 表: repayment.status, repayment.repayment_id
        ↑ 用户点击"立即还款"按钮
        ← App 还款页面 → 支付网关回调 → 写入还款系统

```text

---

---

---

### L120
**分类：** 数据仓库
**题目：** 请讲讲数据血缘 + SchemaRegistry 元数据管理中的动手练习：为 SchemaRegistry 添加新功能（1h）
**参考答案：** ```python
# 为 src/data/schema_registry.py 添加一个校验方法

def validate_dataframe(self, layer: str, table_name: str,
                       df: pd.DataFrame) -> tuple[bool, list[str]]:
    """
    校验 DataFrame 是否与注册的 schema 一致。

    检查项:
    1. 是否有多余的列（不在 schema 中）
    2. 是否有缺失的必填列
    3. 必填列是否有空值

    返回: (是否通过, [错误列表])
    """
    schema = self.get_table(layer, table_name)
    if schema is None:
        return False, [f"表 {layer}.{table_name} 未注册"]

    errors = []
    schema_cols = {c.name for c in schema.columns}
    df_cols = set(df.columns)

    # 多余列
    extra = df_cols - schema_cols
    if extra:
        errors.append(f"多余列: {extra}")

    # 缺少的必填列
    required = {c.name for c in schema.columns if not c.nullable}
    missing = required - df_cols
    if missing:
        errors.append(f"缺少必填列: {missing}")

    # 必填列空值检查
    for col in required & df_cols:
        null_count = df[col].isna().sum()
        if null_count > 0:
            errors.append(f"列 {col} 有 {null_count} 个空值")

    return len(errors) == 0, errors


# 测试
import pandas as pd
r = SchemaRegistry()
df = pd.DataFrame({
    'user_id': ['u1', 'u2', None],  # ← 有空值
    'apply_amount': [1000, 2000, 3000],
    'extra_col': [1, 2, 3],         # ← schema 中没有的列
})
ok, errors = r.validate_dataframe('ods', 'ods_application', df)
print(f"通过: {ok}")
for e in errors:
    print(f"  - {e}")

```text

---

---

---

### L121
**分类：** 数据仓库
**题目：** 请讲讲数据血缘 + SchemaRegistry 元数据管理中的今天要点
**参考答案：** ```text
SchemaRegistry 的三个价值:
  1. 代码可消费: NL2SQL 可以直接读 schema 构造 LLM Prompt
  2. 数据可自描述: 数据目录下的 _TABLE_SCHEMA.json 让别人也能读懂
  3. 变更可追溯: schema 和代码一起用 git 管理

数据血缘的两种形态:
  1. 表级: 层与层之间的流转关系（哪张 DWD 表生成了哪张 DWS 表）
  2. 列级: 每个特征追溯到 DWD 源列和聚合公式

```text

---

---

---

### L122
**分类：** 数据仓库
**题目：** 请讲讲PII 脱敏 + DDL 规范 + 合规中的脱敏不是"全删"——是"保留该保留的"（30min）
**参考答案：** ### 1.1 DataMasker 的四种策略

打开 `src/data/warehouse/dwd_layer.py` 第 48-78 行：


```python
class DataMasker:
    # 策略1: 掩码(Mask) — 保留部分结构，可做统计分析
    @staticmethod
    def mask_name(name):        # 黄敏 → 黄*
        return name[0] + "*" * (len(name) - 1)

    @staticmethod
    def mask_id_card(id_card):  # 934184...8691 → 934184********8691
        return id_card[:6] + "********" + id_card[-4:]

    @staticmethod
    def mask_phone(phone):      # 13872128795 → 138****8795
        return phone[:3] + "****" + phone[-4:]

    # 策略2: 哈希(Hash) — 不可逆但可去重
    @staticmethod
    def hash_user_id(user_id):  # user_000042 → a1b2c3d4e5f6...
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

```text
**策略选择矩阵**：

| 策略 | 可逆性 | 可分析性 | 适用场景 |
|------|--------|---------|---------|
| Mask(掩码) | 部分可逆 | 高（保留结构） | 姓名、身份证、手机 |
| Hash(哈希) | 不可逆 | 仅可去重 | user_id、设备 ID |
| Generalize(泛化) | 不可逆 | 中（高维→低维） | IP→网段、年龄→年龄段 |
| Encrypt(加密) | 可逆（凭密钥） | 高 | 银行卡号（需结算时解密） |

### 1.2 为什么保留部分信息？


```text
身份证: 934184********8691
  前6位 934184 = 地区码 → 可衍生"户籍省份"特征
  中间8位 = 出生日期 → 可衍生""年龄"特征
  后4位 = 校验码 → 可去重

全部哈希 → 丢失了地区和年龄两个有用特征
保留前6后4 → 既保护了隐私，又保留了分析价值

```text

---

---

---

### L123
**分类：** 数据仓库
**题目：** 请讲讲PII 脱敏 + DDL 规范 + 合规中的DDL 写作规范（1h）
**参考答案：** ### 2.1 生产级 DDL 必须包含的元素

打开 `config/ddl/02_dwd_tables.sql` 看完整示例：


```sql
CREATE TABLE IF NOT EXISTS dwd.dwd_application (
    user_id           STRING    COMMENT '用户ID。原始为空→填充MISSING',
    apply_amount      DOUBLE    COMMENT '申请金额(元)。已修正: 负数→0',
    user_name         STRING    COMMENT '★ 已脱敏: 黄敏→黄*',
    id_card           STRING    COMMENT '★ 已脱敏: 934184********8691',
    dq_score          INT       COMMENT '★ 数据质量评分 0-100。≥60通过',
    dq_quarantined    BOOLEAN   COMMENT '★ 隔离标记。dq_score<60→TRUE',
    dt                STRING    COMMENT '分区键 — 日期 YYYY-MM-DD'
)
COMMENT '清洗+脱敏后的用户申请明细 — dq_score<60记录被隔离'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_table' = 'ods.ods_application',          -- 从哪来
    'transformation' = 'clean_application()',         -- 做了什么
    'pii_columns' = 'user_name,id_card,phone,ip_address',  -- 敏感列
    'retention_days' = '365',                         -- 保留多久
    'data_owner' = '风控团队',
    'update_frequency' = 'daily'
);

```text
### 2.2 COMMENT 的写作标准


```text
好的 COMMENT = 含义 + 格式/阈值 + 风险方向（如果是特征列）

示例:
  ✓ "近30天深夜操作占比(22-05时)。>60%→高度可疑"     ← 含义+阈值+方向
  ✗ "深夜操作占比"                                   ← 只有含义
  ✗ "night_ops_ratio_30d"                            ← 重复列名

  ✓ "已脱敏: 黄敏→黄*"。                              ← 原值→脱敏值
  ✗ "脱敏后的姓名"                                    ← 没说明怎么脱敏

  ✓ "分区键 — 申请日期 YYYY-MM-DD"                    ← 含义+格式
  ✗ "日期"                                           ← 太简略

```text
### 2.3 TBLPROPERTIES 的必备项


```text
必须包含:
  'source_system' / 'source_table'  — 数据来源
  'retention_days'                   — 生命周期
  'pii_columns'（如有）              — 敏感列清单
  'update_frequency'                 — 更新频率

建议包含:
  'data_owner'                       — 负责人
  'transformation'                   — 转换规则简述

```text

---

---

---

### L124
**分类：** 数据仓库
**题目：** 请讲讲PII 脱敏 + DDL 规范 + 合规中的动手练习（1.5h）
**参考答案：** ### 练习 1：为电商数据写脱敏策略（45min）


```python
# ★ 参考答案

def mask_收货人姓名(name: str) -> str:
    """掩码: 张三→张*。保留姓氏用于地域分析"""
    if not name or not isinstance(name, str):
        return "***"
    return name[0] + "*" * (len(name) - 1)

def mask_收货手机号(phone: str) -> str:
    """掩码: 保留前3后4, 可分析运营商号段"""
    if not phone or not isinstance(phone, str) or len(phone) < 11:
        return "INVALID_PHONE"
    return phone[:3] + "****" + phone[-4:]

def generalize_收货地址(address: str) -> str:
    """
    泛化: "北京市朝阳区望京街道XX小区3号楼502" → "北京市朝阳区"
    保留区级用于物流区域分析，去掉门牌号保护隐私
    """
    if not address or not isinstance(address, str):
        return "UNKNOWN"
    # 提取到区级: 按"市"和"区"切
    parts = address.split('区')
    if len(parts) >= 2:
        return parts[0] + '区'
    parts = address.split('县')
    if len(parts) >= 2:
        return parts[0] + '县'
    return "UNKNOWN"

def hash_支付卡号(card_no: str) -> str:
    """哈希: SHA256 不可逆，只用于去重和关联"""
    if not card_no or not isinstance(card_no, str):
        return "INVALID"
    import hashlib
    return hashlib.sha256(card_no.encode()).hexdigest()[:16]

```text
### 练习 2：写生产级 DDL（30min）

为电商的 `dwd_order` 写生产级 DDL。要求：
- 至少 8 个业务字段 + COMMENT
- PARTITIONED BY
- TBLPROPERTIES 至少 4 项
- 标注 PII 列


```sql
-- ★ 参考答案
CREATE TABLE IF NOT EXISTS dwd.dwd_order (
    order_id          STRING    COMMENT '订单ID。原始为空→MISSING',
    user_id           STRING    COMMENT '用户ID',
    pay_amount        DOUBLE    COMMENT '支付金额(元)。已修正:负数→0',
    shipping_address  STRING    COMMENT '★ 收货地址(已脱敏:保留到区级)',
    phone             STRING    COMMENT '★ 手机号(已脱敏:138****0000)',
    status            STRING    COMMENT '订单状态(已标准化):PAID/SHIPPED/RETURNED',
    category          STRING    COMMENT '商品品类',
    province          STRING    COMMENT '省份(从address解析)。UNKNOWN→10分',
    dq_score          INT       COMMENT '★ 数据质量评分 0-100。≥60通过',
    dt                STRING    COMMENT '分区键 — 下单日期 YYYY-MM-DD'
)
COMMENT '清洗后的电商订单明细 — PII列已脱敏'
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_table' = 'ods.ods_order',
    'transformation' = 'clean_order()',
    'pii_columns' = 'shipping_address,phone',
    'retention_days' = '365',
    'update_frequency' = 'daily'
);

```text

---

---

---

### L125
**分类：** 数据仓库
**题目：** 请讲讲PII 脱敏 + DDL 规范 + 合规中的跨业务思考（30min）
**参考答案：** ### GDPR "被遗忘权"场景


```text
用户要求删除所有个人数据 → 数仓应该怎么做？

方案 A: DELETE FROM ... WHERE user_id = 'xxx'
  问题: Hive/Iceberg 不支持行级删除（或性能极差）
  问题: 删了之后聚合指标会变（昨日 GMV 从 100 变成 99）

方案 B: 软删除 — 保留数据但标记 deleted=True
  优势: 聚合指标不变
  问题: 技术上数据没有被"删除"

方案 C: 匿名化 — 把 user_id 替换为 anonymous_xxx
  优势: 聚合指标不变，原始用户无法识别
  问题: 如果其他表也有 user_id → 关联失效

实际做法: 根据法规选择 B(金融, 必须保留审计) 或 C(电商, 可匿名)

```text

---

---

---

### L126
**分类：** 数据仓库
**题目：** 请讲讲分区策略 + 数据产品设计中的分区是数仓性能的基石（40min）
**参考答案：** ### 1.1 有分区 vs 无分区


```sql
-- 无分区: 全表扫描
SELECT * FROM orders WHERE dt = '2026-07-01';
-- → 扫描 10 亿行（一年数据），耗时 5 分钟

-- 有分区(PARTITIONED BY dt):
SELECT * FROM orders WHERE dt = '2026-07-01';
-- → 只扫描 1 个分区(100 万行)，耗时 5 秒
-- → 速度提升 60 倍

```text
### 1.2 分区四步法


```text
Step 1: 选分区键 → 最常用的 WHERE 条件是什么？
Step 2: 选粒度   → 天？小时？月？
Step 3: 定生命周期 → 每层保留多久？
Step 4: 选写入模式 → INSERT OVERWRITE / INSERT INTO / MERGE？

```text
### 1.3 项目的分区设计

打开 `config/ddl/01_ods_tables.sql`，观察不同表的不同保留期：


```sql
-- 申请表: 90天（短期高频查询）
TBLPROPERTIES ('retention_days' = '90')

-- 行为日志: 30天（数据量大，很快过期）
TBLPROPERTIES ('retention_days' = '30')

-- 还款记录: 365天（监管要求至少一年）
TBLPROPERTIES ('retention_days' = '365')

```text
**为什么不同表保留期不同？**


```text
行为日志: 日增 5000 条 × 2000 用户 = 1000 万条/天 × 365 = 36 亿条/年
  → 保留一年太贵 → 30 天够用（行为特征只看近期）
还款记录: 日增 500 条，一年才 18 万条
  → 保留一年很便宜 → 监管要求必须留

```text
### 1.4 分区粒度的选择


```text
按天(dt)   = 365 个分区/年 → 信贷/电商 大多数场景
按小时(dt+hour) = 8760 个分区/年 → 广告点击/实时大屏
按月(dt=YYYY-MM) = 12 个分区/年 → 年度报表/审计

```text

---

---

---

### L127
**分类：** 数据仓库
**题目：** 请讲讲分区策略 + 数据产品设计中的ADS 数据产品：不是"把 DWS 改个名"（1h）
**参考答案：** 打开 `src/data/warehouse/ads_layer.py`，三种数据产品各有不同的消费者和格式。

### 2.1 训练样本 — Parquet → 模型训练


```python
def build_training_samples(self, dws_wide_table, label_df):
    """
    消费者: XGBoost 模型训练
    格式: Parquet（列式存储，读取快）
    特点: 宽表（每列一个特征），不需要聚合
    """
    return dws_wide_table.merge(label_df, on='user_id', how='inner')

```text
**为什么用 Parquet？**
- 列式存储：读 17 列特征时只扫描这些列，跳过不需要的列
- 压缩率高：数值特征压缩比 3-5x
- ML 框架原生支持：`pd.read_parquet()` / `Spark.read.parquet()`

### 2.2 监控日报 — CSV → Grafana


```python
def build_model_monitor_daily(self, predictions, dws_wide_table, dt):
    """
    消费者: Grafana 监控大盘
    格式: CSV（人类可读，Grafana 原生支持）
    粒度: 每日一条（预聚合！）
    """
    return pd.DataFrame([{
        'dt': dt,
        'total_applications': n_total,
        'approval_rate': round(len(approved) / n_total, 4),
        'avg_score': round(predictions['score'].mean(), 2),
        'score_p10': round(predictions['score'].quantile(0.10), 2),  # ★
        'score_p50': round(predictions['score'].quantile(0.50), 2),  # ★
        'score_p90': round(predictions['score'].quantile(0.90), 2),  # ★
    }])

```text
**为什么包含 p10/p50/p90 三个分位数？**


```text
avg_score = 615

场景 A: 分数均匀分布 [500, 730] → avg=615，看起来正常
场景 B: 分数两极分化 [300, 300, 900, 900] → avg=600，看起来也正常

但 p10=300, p90=900 能揭示场景B的异常！
只有 avg 会掩盖分布变化。

```text
### 2.3 资产分析 — JSON → 风控报表


```python
def build_portfolio_analysis(self, decisions, dws_wide_table) -> dict:
    """
    消费者: 风控报表/BI 看板
    格式: JSON（嵌套结构、前端可直接渲染）
    """
    return {
        'total_portfolio': int(len(merged)),
        'score_distribution': {
            'A+': 20, 'A': 30, 'B+': 89, 'B': 105, 'C': 172, 'D': 39
        },
        'avg_score_by_bucket': {
            'A+': 780.5, 'A': 720.3, ...
        },
    }

```text
**为什么用 JSON？**
- 嵌套结构：`score_distribution` 是一个 dict，CSV 无法直接表达
- 前端友好：`fetch('/api/portfolio') → .json() → render(chart)`
- 一次返回所有数据：不需要前端多次查询

---

---

---

### L128
**分类：** 数据仓库
**题目：** 请讲讲分区策略 + 数据产品设计中的动手练习（1.5h）
**参考答案：** ### 练习 1：设计电商分区策略（45min）


```text
★ 参考答案

场景: 电商订单表

1. 分区键: dt（下单日期）
   理由: 90% 查询按日期过滤，dt 是最常用过滤条件

2. 分区粒度: 天 + 大促当天用二级分区(小时)
   平常: dt 天分区即可（每天 5000 万行，天粒度够）
   618大促: 当天 5 亿行 → 按小时二级分区
     dt='2026-06-18' AND hour='14' → 只扫描该小时数据
     不加二级分区 → 大促日查询扫描 5 亿行（慢 10 倍）

3. 各层保留:
   ODS: 30 天（原始数据量大，保留太久贵）
   DWD: 90 天（清洗后的数据更紧凑）
   DWS: 365 天（用户画像需要看一年趋势）
   ADS: 730 天（监控报表需要两年对比）

4. 大促优化:
   方案 A: 当天做二级分区(小时) → 查询加速
   方案 B: 大促数据单独存储（hot path）
   方案 C: 用 ClickHouse 代替 Hive 做实时查询

```text
### 练习 2：设计广告投放的数据产品（30min）


```python
def build_ad_monitor_minute(ad_impressions, ad_clicks, dt, hour, minute):
    """
    消费者: 实时大屏（每分钟刷新）
    粒度: 广告 × 分钟
    指标: ctr, ecpm, spend, conversion
    """
    # ★ 参考答案
    merged = ad_impressions.merge(ad_clicks, on=['ad_id', 'user_id'],
                                  how='left')

    monitor = merged.groupby('ad_id').agg(
        impressions=('impression_id', 'count'),
        clicks=('click_id', lambda x: x.notna().sum()),
        spend=('cost', 'sum'),
        conversions=('conversion_flag', 'sum'),
    ).reset_index()

    monitor['ctr'] = monitor['clicks'] / monitor['impressions'].replace(0, 1)
    monitor['ecpm'] = monitor['spend'] / monitor['impressions'].replace(0, 1) * 1000
    monitor['dt'] = dt
    monitor['hour'] = hour
    monitor['minute'] = minute

    return monitor[['ad_id', 'ctr', 'ecpm', 'spend', 'conversions',
                    'impressions', 'clicks', 'dt', 'hour', 'minute']]

```text

---

---

---

### L129
**分类：** 数据仓库
**题目：** 请讲讲综合项目 — 为在线教育平台设计完整数仓中的业务理解（30min）
**参考答案：** ```text
业务: 在线教育平台 "LearnFast"

核心业务:
  - 学生: 观看视频课程、做练习题、参加考试、发表评论
  - 老师: 发布课程、批改作业、回复评论
  - 管理员: 看日报、分析课程质量

数据源:
  - MySQL: 用户表、课程表、订单表（购买课程）
  - 埋点 SDK: 观看行为（播放/暂停/快进/完成）、做题行为
  - 日志文件: 考试系统的答题记录（CSV 格式）
  - 第三方 API: 支付回调、短信通知记录

```text

---

---

---

### L130
**分类：** 数据仓库
**题目：** 请谈谈设计任务（2h）怎么设计？
**参考答案：** ### 任务 1：ODS 层（20min）

定义 5 张 ODS 表，使用 `ODSTable` dataclass：


```python
from dataclasses import dataclass

@dataclass
class ODSTable:
    name: str
    source_system: str
    ingest_method: str    # binlog / sdk / file / api_log
    partition_key: str = "dt"
    description: str = ""

# ★ 参考答案
教育_ODS_TABLES = {
    "ods_user": ODSTable(
        name="ods_user",
        source_system="mysql_user_center",
        ingest_method="binlog",
        description="用户表(学生/老师)。来自MySQL用户中心",
    ),
    "ods_course": ODSTable(
        name="ods_course",
        source_system="mysql_course_center",
        ingest_method="binlog",
        description="课程表。来自MySQL课程中心",
    ),
    "ods_order": ODSTable(
        name="ods_order",
        source_system="mysql_payment",
        ingest_method="binlog",
        description="课程购买订单表。来自支付系统",
    ),
    "ods_watch_behavior": ODSTable(
        name="ods_watch_behavior",
        source_system="sdk_analytics",
        ingest_method="sdk",
        description="观看行为埋点。SDK实时上报",
    ),
    "ods_exam_result": ODSTable(
        name="ods_exam_result",
        source_system="exam_system",
        ingest_method="file",
        description="考试结果。来自考试系统CSV日志",
    ),
}

```text
### 任务 2：DWD 层 — 清洗观看行为表（30min）


```python
def clean_watch_behavior(ods_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    清洗规则:
    1. user_id/video_id 为空 → 扣 30 分
    2. watch_duration < 0 或 > video_duration*3 → 扣 20 分（作弊刷时长？）
    3. 视频状态标准化: play/pause/seek/complete/error → 标准枚举
    4. user_id 脱敏（如果涉及 PII）
    5. dq_score < 60 → 隔离
    """
    df = ods_df.copy()
    df['dq_score'] = 100

    # ★ 参考答案
    # 1. 必填检查
    df.loc[df['user_id'].isna() | df['video_id'].isna(), 'dq_score'] -= 30
    # 2. 时长异常
    df.loc[df['watch_duration'] < 0, 'dq_score'] -= 20
    # 3. 状态标准化
    valid_status = {'play', 'pause', 'seek', 'complete', 'error'}
    df['status'] = df['status'].fillna('unknown')
    df.loc[~df['status'].isin(valid_status), 'status'] = 'unknown'
    # 4. 脱敏
    df['user_id'] = df['user_id'].apply(lambda x: x)  # 生产中用hash

    df_clean = df[df['dq_score'] >= 60]
    report = {"total": len(df), "passed": len(df_clean),
              "quarantined": len(df) - len(df_clean)}
    return df_clean, report

```text
### 任务 3：DWS 层 — 学生学习画像宽表（40min）


```python
def build_student_profile_wide_table(
    dwd_order,          # 购买记录
    dwd_watch_behavior, # 观看行为
    dwd_exam_result,    # 考试结果
    dt: str,
) -> pd.DataFrame:
    """
    粒度: 学生 × 日期
    要求至少 10 个特征:

    购买画像(3个): 总购买课程数、总消费金额、最近购买距今天数
    学习行为(4个): 近7天观看视频数、近7天观看总时长(分钟)、
                  平均完成率(completed/total_watch)、跳过率(seek/total_watch)
    考试表现(3个): 近30天考试次数、平均得分、通过率

    关键设计决策:
    - 聚合函数选择: 为什么平均完成率用 mean 而不是 sum？
    - left join or inner join: 新学生没有考试记录怎么办？
    """
    # ★ 参考答案
    # 1. 购买画像聚合
    order_agg = dwd_order.groupby('user_id').agg(
        total_courses=('course_id', 'nunique'),
        total_spend=('amount', 'sum'),
        days_since_last_purchase=('purchase_time', lambda x:
            (pd.to_datetime(dt) - x.max()).days),
    ).reset_index()

    # 2. 观看行为聚合
    in_7d = dwd_watch_behavior['watch_time'] >= pd.to_datetime(dt) - timedelta(days=7)
    watch_7d = dwd_watch_behavior[in_7d].groupby('user_id').agg(
        video_watched_7d=('video_id', 'nunique'),
        total_watch_minutes_7d=('duration_sec', lambda x: x.sum() / 60),
        completion_rate=('is_complete', 'mean'),
        skip_rate=('event_type', lambda x: (x == 'seek').mean()),
    ).reset_index()

    # 3. 考试表现聚合
    exam_agg = dwd_exam_result[dwd_exam_result['exam_time'] >=
                               pd.to_datetime(dt) - timedelta(days=30)].groupby('user_id').agg(
        exam_cnt_30d=('exam_id', 'nunique'),
        avg_score=('score', 'mean'),
        pass_rate=('is_pass', 'mean'),
    ).reset_index()

    # 4. left join + fillna（新学生无考试记录→fillna(0)）
    wide = order_agg.merge(watch_7d, on='user_id', how='left') \
                    .merge(exam_agg, on='user_id', how='left')
    numeric_cols = wide.select_dtypes(include=[np.number]).columns
    wide[numeric_cols] = wide[numeric_cols].fillna(0)

    return wide

```text
### 任务 4：分区策略（15min）


```text
★ 参考答案

1. 分区键: 统一 dt 日期分区
   所有表按 dt 分区 → ETL 统一按天调度

2. 观看行为: 保留 30 天
   日增 1000 万，按天分区后每天 1000 万行可管理
   超过 30 天的用户行为数据价值低

3. 考试结果: 永久保留（学业记录）
   但需要冷热分离:
   - 活跃数据(2年): Parquet 保留在 HDFS
   - 历史数据(2年+): 压缩归档到对象存储(S3/OSS)

4. 二级分区:
   课程类别可以作为二级分区 → 优化"按课程查"场景
   但只在 DWS/ADS 层加，ODS/DWD 不用（保持简单）

```text
### 任务 5：PII 脱敏（15min）


```text
教育平台的敏感数据:
  - 学生姓名 / 手机号
  - 老师身份证（提现需要实名认证）
  - 支付信息
  - 考试分数（属于个人隐私，GDPR 保护范围）

为每个字段选脱敏策略（Mask/Hash/Generalize/Encrypt）并写理由

```text
### 任务 6：ADS 数据产品（20min）

设计 2 个数据产品：


```text
产品 1: 学习效果预测训练样本
  - 消费者: ML 模型训练（预测学生是否会中途退课）
  - 格式: Parquet
  - 结构: DWS 宽表 + label (30天后是否退课)
  - PIT 约束: 特征时间 < 标签时间

产品 2: 课程质量日报
  - 消费者: 运营看板 / Grafana
  - 格式: CSV
  - 粒度: 课程 × 日期
  - 指标: 观看人数、平均完成率、平均评分、退课率

```text

---

---

---

### L131
**分类：** 数据仓库
**题目：** 请讲讲综合项目 — 为在线教育平台设计完整数仓中的自评表（20min）
**参考答案：** | 能力 | 自评(1-5) | 在线教育项目中的体现 |
|------|---------|-------------------|
| 分层架构 | | 定义了 4 层 + ODS 5 张表 |
| 数据质量 | | 设计了观看行为表的扣分规则 |
| 维度建模 | | 设计了学生学习画像 10+ 特征宽表 |
| 血缘管理 | | — （本练习未涉及） |
| PII 脱敏 | | 设计了教育数据的脱敏策略 |
| 分区策略 | | 设计了不同表的分区和保留期 |
| 数据产品 | | 设计了训练样本 + 课程日报 |

---

---

---

### L132
**分类：** 模型可解释性
**题目：** 请讲讲补充/07_reason_codes和 SHAP 区别.md中的批量监控：从“看一个人”到“看一群人”
**参考答案：** **日常操作（看张三一个人）**：
我们每天只盯着张三的明细单，能看到他学历 +15 分，因为没房 -10 分。这能解释他个人的情况，但看不出问题。

**批量监控（每天早上看 1 万个申请人的明细单）**：
我们把昨天所有申请人的明细单汇总，算出**“所有博士的平均加分值”**。之前的 3 个月，这个数字一直是 **+15 分**，非常稳定。

**触发警告**：突然有一天，我们发现所有博士的平均加分值变成了 **+25 分**。

**监控系统反应**：立刻发出告警，提示“逻辑漂移（Logic Drift）”——模型决策逻辑发生了显著变化。

**在信贷场景中的对应**：模型对“学历”这个特征的重视程度，在短短一天内突然被放大了，这本身就是一种强烈的风险信号。

---

---

---

### L133
**分类：** 模型可解释性
**题目：** 逻辑漂移：为什么“标准”变了？
**参考答案：** **什么是逻辑漂移**：
简单说，就是模型对同一个特征（比如学历）的**“评判标准”**变了。昨天博士还是 +15 分，今天博士突然变成 +25 分，或者反过来掉到 +5 分，都算漂移。

**逻辑漂移的本质**：模型还是那个模型，**是它内部各个特征之间的博弈关系（非线性交互）发生了剧烈变化**。它开始“认为”某个特征比之前更重要了，而这种“认为”没有经过人工验证，可能潜藏着风险。

**具体到张三这个例子（模拟漂移发生）**：

| 特征 | 上周的评判标准 | 这周的评判标准（异常） | 漂移方向 |
| :--- | :--- | :--- | :--- |
| **学历（博士）** | 固定 +15 分 | 突然变成 +25 分 | **↑ 向上漂移**（过度依赖学历） |
| **职住区域（郊区有房）** | 固定 +10 分 | 突然变成 0 分（无效） | **↓ 向下漂移**（职住指标失效） |
| **创新指标（专利）** | 1项 -2分，3项 +5分 | 1项 -10分，3项 +2分 | **加剧惩罚**（对创新门槛要求更高） |

**为什么漂移很危险？**
因为模型开始执行一套我们没有验证过的“潜规则”。比如，如果模型在短短一天内，把“博士”的价值从 +15 分提到了 +25 分，那它可能是在过度放大学历的作用，覆盖了其他关键因素（比如人品、工作能力），这会让我们的决策体系变得不够稳健。

---

---

---

### L134
**分类：** 模型可解释性
**题目：** 请讲讲补充/07_reason_codes和 SHAP 区别.md中的面试完整话术（建议背诵）
**参考答案：** **面试官**：“你对 SHAP 在生产环境中的应用有什么理解？”

**面试者**：
“关于 SHAP，我想用北京积分落户这个生活化的例子来说明。

**首先，SHAP 的核心是‘拆解’**：每个人的最终得分都是从基准分（100分）开始，然后加上各项加减分项得到的。比如张三，他博士学历 +15 分，高额纳税 +10 分，但因为没房 -10 分，最终 118 分。**SHAP 就是负责打印每个人专有的这份‘加减分明细单’，这解决了模型‘黑盒’的可解释性问题。**

**更重要的是生产环境中的批量应用**：我们不会只看张三一个人，而是每天把所有申请人的明细单汇总。这就好比政策研究员会统计**所有‘博士’人群的平均加分值**。

**如果连续几个月都是 +15 分，突然某一天变成了 +25 分，这就叫‘逻辑漂移’。** 这意味着模型对我输入的‘学历’这个特征的评判标准，在没有任何告知的情况下变化了。它可能是在主动放大学历的作用，以弥补其他特征的失效。无论哪种情况，**未经确认的逻辑变化都是一种巨大的风险，可能直接导致审批策略的有效性偏离我们的预期。**

**而我们每天的‘批量监控’任务，就是通过观察所有特征的平均 SHAP 值趋势，来捕捉这种‘漂移’。** 这种机制让我们能**在坏账率等结果指标恶化之前，提前发现策略失效的苗头，并介入干预。** 这就是 SHAP 离线批任务在生产环境的核心价值，也是模型治理从被动响应转向主动预防的关键一步。”

---

---

---

### L135
**分类：** 模型可解释性
**题目：** 请讲讲补充/07_reason_codes和 SHAP 区别.md中的附加思考：逻辑漂移的根因（面试备选）
**参考答案：** 如果面试官追问“哪些因素会导致逻辑漂移”，可以补充：

1. **数据分布变化（最典型）**：近期申请客群中出现大量“高学历、无房产”人群（就像张三），模型为了把“有房”这个重要信号权重调高，相对地就会自动“压低”其他特征的权重，导致全局 SHAP 值变动。
2. **模型热更新/版本变更**：例如误加载了实验版模型的权重文件，导致所有规则的评判标准都变了。
3. **数据上游异常（Bug）**：例如某个特征字段在日志中全部丢失，模型被迫过度依赖剩余的特征来做决策。

---

这套话术把“张三案例 + 批量监控 + 逻辑漂移”串联成了一个完整的故事链，既有生活化的类比，又有生产级的深度，面试时用这个框架回答 SHAP 相关问题，基本能覆盖面试官的所有追问点。😊

---

---

### L136
**分类：** 综合
**题目：** 什么是特征
**参考答案：** **特征 = 从原始数据中提取的、能刻画事物某个侧面的数值或类别标签。**  
例如：
- 信贷：年龄、近30天申请次数、征信分、收入负债比。
- 推荐：用户过去7天点击最多的品类、商品价格、当前时段。
- 图像识别：边缘直方图、纹理特征、或者深度学习中间层的 embedding 向量。
- 自然语言处理：词袋向量、TF-IDF 权重、BERT 输出的语义向量。

特征可以是**人工定义**的（传统 ML），也可以是**自动学习**出来的（深度学习），但在生产系统中，它们都必须被可靠地计算、存储和管理。

---

---

---

### L137
**分类：** 综合
**题目：** 请讲讲补充/02_Feature 详细解释，作用，实现，应用.md中的特征的作用
**参考答案：** ### 1. 决定模型性能的上限
业界有句名言：**“数据和特征决定了机器学习的上限，而模型和算法只是逼近这个上限。”**  
如果特征没有包含足够的信息，再复杂的模型也无法做出准确预测。比如想预测用户是否会逾期，但你只给了“用户注册时间”一个特征，模型几乎无法工作。

### 2. 消除训练-服务偏差 (Training-Serving Skew)
这是生产级 ML 系统最大的挑战之一。如果在线推理时计算特征的逻辑与离线训练时不一致，模型的表现会迅速劣化。统一的特征平台通过标准化特征定义，保证两端的计算口径完全一致。

### 3. 实现特征复用与共享
同一个“用户信用分”特征，可以被 A 卡（贷前审批）、B 卡（贷中管理）、反欺诈等多个模型使用，避免各个团队重复开发，也保证了数据口径统一。

### 4. 支持模型可解释性
在信贷、医疗等强监管领域，模型必须逐笔解释决策原因。只有使用含义清晰、可追溯的特征，才能计算出每个特征对最终结果的贡献（如 SHAP 值、评分卡得分明细）。

### 5. 处理时态逻辑，防止时间泄漏
通过特征平台提供的 **Point-in-Time Join** 能力，可以确保训练样本中所有特征的值都来自于标签时间戳之前，避免用“未来信息”预测“过去结果”。

---

---

---

### L138
**分类：** 综合
**题目：** 请谈谈特征工程的实现：从设计到服务怎么设计？
**参考答案：** 特征不仅仅是算出来就完了，在生产系统中需要一套完整的工程链路：

### 1. 特征设计
由数据科学家和业务专家一起，根据业务理解和数据分析，设计出具有区分度和稳定性的特征。例如：
- 基础画像：年龄、性别、学历。
- 行为统计：近 30 天登录次数、夜间操作占比。
- 交叉特征：用户品类偏好 × 折扣敏感度。
- 序列特征：最近 50 次点击的商品 ID 序列。

### 2. 离线特征计算（批量）
- **技术**：使用 Spark SQL 或 PySpark，从数仓（Iceberg/Hive）中读取 ODS/DWD 明细数据，按天或小时进行聚合计算。
- **例子**：计算“用户过去 90 天的累计借款金额”，Spark 作业每天凌晨扫描交易表，按 `user_id` 分组聚合，结果写入 Iceberg 的特征表。
- **特征回填**：定义新特征后，通过指定起始时间，Spark 可以重新计算过去任意一段时间的历史特征值，并覆盖写入特征表。Iceberg 的时间旅行功能保证了随时可回溯历史快照。

### 3. 实时特征计算（流式）
- **技术**：Flink 或 Kafka Streams 消费 Kafka 中的埋点流、CDC 变更流，在滑动窗口内计算聚合指标。
- **例子**：实时统计“过去5分钟内同一IP的申请次数”，Flink 使用 `TUMBLE` 窗口，每次新事件到来都会更新 Redis 中的计数器，用于反欺诈模型。

### 4. 特征存储与服务
采用**双存储架构**：
- **离线存储**：Iceberg/Hive 上的 Parquet 表，用于大规模训练样本的批量拉取。
- **在线存储**：Redis/Cassandra，用于毫秒级低延迟查询。实时特征由 Flink 直接写入，离线特征由 Feast materialize 命令批量推送。
- **特征服务接口**：通过 Feast 的 `get_online_features` API 或自定义的 Feature Service（gRPC），统一提供在线特征查询。

### 5. 特征注册与管理（特征平台）
使用 **Feast** 作为元数据层，它定义了：
- **Entity**：特征关联的主体（如 `user_id`、`item_id`）。
- **FeatureView**：一组特征的计算逻辑和数据源（离线表、实时流）。
- **OnDemandFeatureView**：在线动态计算的特征（如请求参数转换）。
- **Point-in-Time Join**：自动保证训练样本的时间正确性。

整个流程：

```text
业务专家定义 → Feast 注册 → Spark/Flink 计算 → 离线存储 (Iceberg) + 在线存储 (Redis) → 模型训练/推理统一调用

```text

---

---

---

### L139
**分类：** 综合
**题目：** 请讲讲补充/02_Feature 详细解释，作用，实现，应用.md中的特征在不同场景中的应用实例
**参考答案：** ### 1. 信贷风控
- **特征**：多头借贷次数、征信查询次数、信用卡使用率、设备是否越狱、近 7 天修改手机号次数。
- **实现**：征信特征来自第三方报告解析后脱敏入湖；行为特征来自 Flink 实时窗口；设备指纹特征来自埋点上报。所有特征通过 Feast 管理，A 卡和 B 卡复用同一套特征定义。

### 2. 电商推荐
- **特征**：
  - 用户端：近 30 天购买类目分布、历史平均订单金额、最近一次下单距今时间。
  - 物品端：商品价格、销量、好评率、品牌。
  - 上下文：当前时间、用户所在城市、设备类型。
  - 交互序列：用户最近 50 次点击的商品 ID 序列（作为序列特征输入双塔模型）。
- **实现**：长期画像离线 Spark 聚合，短期行为 Flink 实时更新。双塔模型将用户特征和物品特征分别映射成 embedding，在线 ANN 检索。

### 3. 广告点击率预估
- **特征**：广告创意类型、广告位位置、用户人口属性、用户近 10 次广告交互历史、当前时段、网络环境。
- **实现**：因为特征规模极大（亿级用户和广告 ID），通常将 ID 类特征通过深度学习 Embedding 层转换为低维稠密向量。实时特征和离线特征混合输入到 Wide&Deep 等模型中。

### 4. 图像识别（工业缺陷检测）
- **传统 ML 特征**：边缘长度、面积、圆形度、灰度共生矩阵纹理特征。
- **深度学习特征**：使用 CNN 中间层输出的 feature map 或全连接层前的向量作为“视觉特征”，供后续分类器或检索使用。
- **实现**：特征平台可统一管理“图像 embedding”这种特征，离线批量用 GPU 提取并存入特征存储，在线推理时直接调用。

### 5. 自然语言处理（智能客服）
- **特征**：对话历史嵌入、用户意图分类结果、FAQ 匹配相似度分数、对话轮次、客户情绪分数。
- **实现**：使用 BERT 等模型将文本转换为固定维度的语义特征向量，离线为所有 FAQ 生成 embedding 存入向量数据库，在线时实时编码用户问题并检索相似 FAQ。

---

---

---

