# Day 03：维度建模 + 宽表设计

> 目标：掌握"先聚合再 Join"的宽表构建方法，理解粒度、Join 策略、聚合函数的选择。

---

## 一、核心概念：粒度（30min）

### 1.1 粒度决定了宽表能回答什么问题

```
粒度 A: 用户（每个用户一行）
  能回答: "张三这个人的信用评分是多少？"
  不能回答: "张三上个月和这个月的评分差了多少？"

粒度 B: 用户 × 日期（每人每天一行）
  能回答: "张三月度信用变化趋势"
  能回答: "张三今天的评分是多少"

粒度 C: 用户 × 申请（每人每次申请一行）
  能回答: "张三第3次申请和第5次申请有什么不同"
  不能回答: 粒度 B 能回答的聚合问题（需要二次聚合）
```

**项目的选择：粒度 = 用户 × 日期**

为什么？信贷风控需要在**时间维度上观察用户变化**——一个人收入在涨还是在跌？逾期次数在增加还是在减少？

### 1.2 粒度选择的黄金法则

```
选择能回答"最有价值的业务问题"的最粗粒度。

最粗 = 数据量可控，存储和查询成本低
有价值 = 能支撑核心分析场景

反例（太细）: 粒度 = 用户 × 分钟 → 数据量爆炸，但没有人需要分钟级信用评分
反例（太粗）: 粒度 = 城市 → 一个城市只有一行，无法做个人信用评估
```

---

## 二、项目宽表：从 3 张 DWD 到 1 张 DWS（1h）

### 2.1 三路聚合 → left join → fillna

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
```

### 2.2 为什么 left join 而不是 inner join？

```
场景: 新用户 user_X，刚注册，只有申请记录
  dwd_application: user_X 有 1 行
  dwd_behavior:    user_X 无（从未打开过 App）
  dwd_repayment:   user_X 无（从未借过钱）

inner join:
  user_X → 被丢弃 ❌ → 训练集里没有新用户 → 模型不认识新用户

left join:
  user_X → 保留 ✓ → 行为特征=0, 还款特征=0 → 模型能学到"全0=新用户"
```

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
```

---

## 三、动手练习（2.5h）

### 练习 1：先聚合再 Join vs 先 Join 再聚合（40min）

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
```

**改写为你的项目宽表代码**：

打开 `src/data/warehouse/dws_layer.py` 第 84-88 行，确认项目使用"先聚合再 Join"模式：

```python
# 项目代码确认:
wide_table = (
    profile_features          # ← 已经 groupby 聚合过（每用户一行）
    .merge(behavior_features, on='user_id', how='left')   # ← 1:1 关联，无膨胀
    .merge(repayment_features, on='user_id', how='left')  # ← 1:1 关联，无膨胀
)
```

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
```

预期输出：

```
DWD 行为日志: 5000 行
用户 user_000xxx: 16 条行为记录
宽表: 1 行
特征: page_view_cnt_7d=5, apply_cnt_7d=1
```

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
```

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
```

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
```

---

## 四、跨业务思考（30min）

### 粒度设计练习

为以下业务选择宽表粒度：

| 业务 | 分析需求 | 建议粒度 | 理由 |
|------|---------|---------|------|
| 信贷风控 | 实时信用评估 | 用户×日期 | 每天评估一次，保留时间变化 |
| 电商大促监控 | 每小时 GMV | 小时级 | 需要秒级刷新，10分钟数据太粗 |
| 网约车司机管理 | 每周司机活跃度 | 司机×周 | 周度考核，不需要每天粒度 |
| 游戏玩家 | 每次登录后的行为分析 | 玩家×会话 | 关注每次登录的"单次行为序列" |

**扩展思考：存算分离对粒度的影响**

```
传统数仓: 粒度越细 → 存储越大 → 成本越高 → 倾向于选粗粒度
湖仓一体(Iceberg): 存储成本低 → 粒度可以更细 → 保留更多可能性

问题: 如果存储不要钱，你应该选最细的粒度吗？
答案: 不一定。太细的粒度(如用户×秒)会让查询变得非常慢，
      即使存储成本可以忽略，查询性能也无法接受。
      所以粒度选择还要考虑查询模式。
```

---

## 五、今日要点

```
宽表三原则:
  1. 先聚合，再 Join — 避免笛卡尔积放大指标
  2. left join — 新用户不丢数据
  3. fillna(0) — "无信息" ≠ "平均值"

粒度黄金法则:
  选能回答核心问题的最粗粒度
  对信贷 = 用户×日期（需要时间变化）
  对实时大屏 = 分钟级（需要秒级刷新）
  对年度报告 = 月级（不需要那么细）
```

---

## 六、检查清单

- [ ] 能解释"先聚合再 join vs 先 join 再聚合"的区别
- [ ] 能解释 left join vs inner join 的选择逻辑
- [ ] 能为至少 3 个特征选择正确的聚合函数并说明理由
- [ ] 完成了电商用户消费画像宽表的代码
- [ ] 完成了粒度选择练习
