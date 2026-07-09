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

## 三、动手练习（1.5h）

### 练习 1：为电商写用户消费画像宽表（1h）

```python
# 电商场景: 3 张 DWD 表 → 1 张 DWS 宽表

# 输入表:
# dwd_order:     订单明细 (order_id, user_id, pay_amount, category, order_time)
# dwd_cart:      购物车行为 (user_id, item_id, action, action_time)
# dwd_view:      浏览行为 (user_id, item_id, page, view_time)

def build_user_consumption_wide(dwd_order, dwd_cart, dwd_view, dt):
    """
    粒度: 用户 × 日期
    要求至少 10 个特征:
    - 订单聚合(3个): avg_order_amount, order_cnt_30d, return_rate
    - 购物车(3个): cart_cnt_7d, cart_abandon_rate, wishlist_cnt
    - 浏览(3个): view_cnt_7d, category_diversity, avg_session_pages
    - 衍生(1个): purchase_conversion = 购买/浏览

    聚合策略:
    - 先各自 groupby 聚合 → 压缩到用户粒度
    - 再 left join → 保证新用户不丢失
    - 最后 fillna(0)
    """
    # TODO: 实现
    pass
```

### 练习 2：选择正确的聚合函数（30min）

```python
# 下列特征应该选什么聚合函数？写理由。

选择题 = {
    "用户月收入(多次填写)": {
        "选项": ["AVG", "MAX", "MIN", "LAST"],
        "你的选择": "?",
        "理由": "?"
    },
    "用户退货率": {
        "选项": ["AVG(status=='returned')", "SUM(returned)/SUM(total)", "MAX(returned)"],
        "你的选择": "?",
        "理由": "?"
    },
    "用户最常浏览的品类": {
        "选项": ["MODE", "MAX(COUNT)", "FIRST"],
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
| 电商大促监控 | 每小时 GMV | ? | ? |
| 网约车司机管理 | 每周司机活跃度 | ? | ? |
| 游戏玩家 | 每次登录后的行为分析 | ? | ? |

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
