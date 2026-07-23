# Day 02：数据质量体系 — 扣分制 vs 二元判定

> 目标：掌握扣分制数据质量评分（dq_score），理解"数据质量是一个频谱，不是 0/1"。

---

## 一、为什么简单的"通过/不通过"不够用？（20min）

### 1.1 两种世界观

```
二元判定（简单但粗糙）:
  数据有一条空字段 → 整条丢弃 ❌
  问题: 丢了太多"部分可用"的数据

扣分制（精细但需要设计）:
  数据有一条空字段 → 扣分，达到隔离线才丢弃
  优势: 保留"大部分 OK，小部分有问题"的数据
```

**实际案例对比**：

```
用户 A: user_id=OK, apply_amount=OK, product_type=OK, phone=OK, occupation=空
  二元判定: "有空字段 → 丢弃" ❌
  扣分制:   扣 5 分 → dq_score=95 → 通过 ✓（phone 可用，只是职业未知）

用户 B: user_id=空, apply_amount=OK, product_type=OK
  二元判定: "有空字段 → 丢弃" ✓（确实该丢）
  扣分制:   扣 30 分 → dq_score=70 → 通过（但要注意）

用户 C: user_id=空, apply_amount=负数, product_type=空
  二元判定: "有空字段 → 丢弃" ✓
  扣分制:   扣 30+20+10=60 → dq_score=40 → 隔离 ✓（确实该丢）
```

---

## 二、项目中的扣分制实现（1h）

### 2.1 完整阅读 `clean_application()`

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
```

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
```

**为什么这 5 个字段就够？**

- `total_rows`：数据量突然掉一半 → 源系统挂了
- `quarantined_rows/total_rows`：隔离率从 5% 突增到 30% → 源系统数据质量急剧恶化
- `null_rate_by_column`：某一列空值率突然升高 → 该字段的采集可能出了问题
- `invalid_rate_by_column`：区分"空"和"错"——空是缺失，错是有但不对

---

## 三、动手练习（1.5h）

### 练习 1：为电商订单写清洗函数（1h）

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
```

### 练习 2：设计扣分权重（30min）

针对以下"医疗检验结果表"，设计扣分规则：

```
字段：patient_id, test_time, glucose(血糖), blood_pressure(血压), lab_tech(检验师)

问题场景：
A. patient_id 为空 → 扣 30 分（理由: 患者ID是主键，缺失=记录不可用，等同于信贷的user_id为空）
B. glucose = 0（不可能，活人血糖不会是 0）→ 扣 20 分（理由: 核心检验字段异常，
   但可修正为NULL标记"无效"，单独异常(80分)不隔离，叠加其他问题隔离）
C. lab_tech 为空 → 扣 5 分（理由: 检验师姓名对诊断分析不重要，不影响医学判断，
   只影响追溯和审计，单独缺失几乎不影响数据质量）
```

---

## 四、跨业务思考（30min）

### 场景：物流数据"包裹重量为 0"

```
包裹重量 = 0 有两种可能：
1. 真的没称重（数据缺失）→ 应该修正还是隔离？
2. 信封/文件类（实际重量接近 0）→ 0 是否合理？

作为数据仓库工程师，你需要判断：
- 这个字段对下游什么用途？（运费计算？→ 很关键。统计分析？→ 不太关键）
- 区分"数据缺失"和"数据为 0"的方法？（加一个 is_weighed 标记列）
```

---

## 五、今日要点

```
扣分制的三个核心决策:
  1. 扣分阈值: 致命(-30) / 严重(-20) / 轻微(-10) / 提示(-5)
  2. 隔离线: dq_score < 60 → 隔离（一个致命 + 一个严重 + 一个轻微 = 40 < 60）
  3. 质量报告: 不是打印日志，是结构化数据（DQReport）供监控系统消费

扣分权重不是拍脑袋:
  → 需要和下游消费者（AI工程师、BI分析师）沟通
  → 哪些字段缺失"还行"，哪些"绝对不能丢"
```

---

## 六、检查清单

- [ ] 能说出扣分制 vs 二元判定的优劣
- [ ] 能解释为什么 dq_score 隔离线是 60 分
- [ ] 完成了电商订单清洗函数（含测试通过）
- [ ] 完成了医疗检验扣分权重设计
- [ ] 运行过 `generate_data_pipeline.py`，观察了 DQ 报告输出
