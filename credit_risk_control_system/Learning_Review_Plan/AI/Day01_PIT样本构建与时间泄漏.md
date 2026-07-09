# Day 01：PIT 样本构建 — 时间泄漏是 AI 工程师的第一课

> 目标：理解时间泄漏的本质，能手写 PIT 正确的训练样本构建代码。

---

## 一、一个让你记住一辈子的例子（20min）

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

## 二、从代码看 PIT 正确性（1h）

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

## 三、动手练习（1.5h）

### 练习 1：写时间泄漏检测器（30min）

```python
def detect_time_leakage(
    samples: pd.DataFrame,
    feature_time_col: str,
    label_time_col: str,
) -> dict:
    """
    检测训练样本中是否存在时间泄漏。

    Args:
        samples: 训练样本 DataFrame
        feature_time_col: 特征时间列名（如 'feature_dt'）
        label_time_col: 标签时间列名（如 'label_dt'）

    Returns:
        {
            "total_samples": 总样本数,
            "leaked_samples": 泄漏样本数,
            "leak_rate": 泄漏比例,
            "leaked_indices": [泄漏的行索引],
            "is_critical": 泄漏率 > 1% → True（需要立即修复）,
        }

    时间泄漏判定: feature_time >= label_time
    """
    # TODO: 实现
    pass


# 测试用例
test_samples = pd.DataFrame({
    'user_id': ['u1', 'u2', 'u3', 'u4', 'u5'],
    'feature_dt': [
        '2026-07-01', '2026-08-05',  # u4: 正常, u5: 时间泄漏！
        '2026-07-01', '2026-07-01', '2026-08-01'
    ],
    'label_dt': [
        '2026-08-01', '2026-08-01',
        '2026-08-01', '2026-08-01', '2026-07-15'
    ],
})
result = detect_time_leakage(test_samples, 'feature_dt', 'label_dt')
assert result['leaked_samples'] == 1  # u3 和 u5 的特征时间 >= 标签时间
```

### 练习 2：为电商推荐写 PIT 样本构建（45min）

```python
def build_电商推荐_训练样本(
    user_features: pd.DataFrame,   # 曝光时刻的特征
    click_labels: pd.DataFrame,    # T+7 的购买标签
) -> pd.DataFrame:
    """
    电商推荐场景的 PIT 样本构建。

    场景: 用户 u1 在 07-01 看到商品 A → 07-05 购买了
         用户 u2 在 07-01 看到商品 B → 一直没有买

    特征时间 = 曝光时刻（show_time）
    标签时间 = 曝光后 7 天（show_time + 7d）
    标签 = 1（购买了）/ 0（没购买）

    要求:
    1. 用 merge 关联 user_id + item_id
    2. 显式过滤 feature_time < label_time
    3. 一个用户对多个商品的曝光 → 每个(user, item, time)是一条样本
    """
    # TODO: 实现
    pass


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
    'label': [1, 0],  # u1 买了 A, u2 没买 A
    'click_time': ['2026-07-05', '2026-07-10'],  # ← 注意：u2 的 click_time > show_time+7
})

samples = build_电商推荐_训练样本(user_features, click_labels)
# 预期: u1-A 保留(label=1), u1-B 没有标签→丢弃, u2-A → 取决于时间过滤
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

## 四、跨业务思考（30min）

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

## 五、今日要点

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

## 六、检查清单

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