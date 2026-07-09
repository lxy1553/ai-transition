# Day 02：特征工程 — 从事件流到特征向量的三种模式

> 目标：掌握三种特征构造模式，能对任意业务事件日志提取预测性特征。

---

## 一、原始事件 vs 特征向量（20min）

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

## 二、三种特征构造模式（1.5h）

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

## 三、动手练习（1.5h）

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

    要求 8 个特征:
    模式1(COUNT WHERE):
      - view_cnt_7d: 近7天浏览商品次数
      - cart_cnt_7d: 近7天加购次数
      - purchase_cnt_7d: 近7天购买次数
      - search_cnt_7d: 近7天搜索次数
    模式2(比率衍生):
      - cart_conversion_7d: 加购转化率 = 加购/浏览
      - purchase_conversion_7d: 购买转化率 = 购买/加购
    模式3(多样性):
      - category_diversity_7d: 浏览品类数（nunique）
      - avg_daily_events_7d: 日均事件数
    """
    ref = datetime.strptime(ref_date, '%Y-%m-%d')
    events['event_time'] = pd.to_datetime(events['event_time'])

    result = []
    for user_id, group in events.groupby('user_id'):
        # TODO: 实现
        pass

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
# 构造两个用户，行为总量不同但模式相似
高频用户: 200 次事件, 其中 40 次购买 → sum=40, rate=0.20
低频用户: 20 次事件, 其中 4 次购买 → sum=4, rate=0.20

# 任务：
# 1. 写代码生成这两个用户的模拟数据
# 2. 分别用 sum 和 rate 计算"购买倾向"
# 3. 分析：如果用 sum 排序，谁排在前面？如果用 rate 排序呢？
# 4. 哪个更合理？为什么？
```

---

## 四、跨业务思考（30min）

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

## 五、今日要点

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

## 六、检查清单

- [ ] 能为电商行为数据写出 8 个特征的完整代码
- [ ] 能解释为什么 mean() 优于 sum()
- [ ] 能解释为什么 fillna(0) 优于 fillna(均值)
- [ ] 能解释为什么 event_time 而非 dt 分区键
- [ ] 为游戏/打车行业各设计了 5 个以上特征
