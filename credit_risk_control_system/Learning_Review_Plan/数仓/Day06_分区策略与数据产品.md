# Day 06：分区策略 + 数据产品设计

> 目标：掌握分区设计方法论，能独立设计 ADS 层的数据产品。

---

## 一、分区是数仓性能的基石（40min）

### 1.1 有分区 vs 无分区

```sql
-- 无分区: 全表扫描
SELECT * FROM orders WHERE dt = '2026-07-01';
-- → 扫描 10 亿行（一年数据），耗时 5 分钟

-- 有分区(PARTITIONED BY dt):
SELECT * FROM orders WHERE dt = '2026-07-01';
-- → 只扫描 1 个分区(100 万行)，耗时 5 秒
-- → 速度提升 60 倍
```

### 1.2 分区四步法

```
Step 1: 选分区键 → 最常用的 WHERE 条件是什么？
Step 2: 选粒度   → 天？小时？月？
Step 3: 定生命周期 → 每层保留多久？
Step 4: 选写入模式 → INSERT OVERWRITE / INSERT INTO / MERGE？
```

### 1.3 项目的分区设计

打开 `config/ddl/01_ods_tables.sql`，观察不同表的不同保留期：

```sql
-- 申请表: 90天（短期高频查询）
TBLPROPERTIES ('retention_days' = '90')

-- 行为日志: 30天（数据量大，很快过期）
TBLPROPERTIES ('retention_days' = '30')

-- 还款记录: 365天（监管要求至少一年）
TBLPROPERTIES ('retention_days' = '365')
```

**为什么不同表保留期不同？**

```
行为日志: 日增 5000 条 × 2000 用户 = 1000 万条/天 × 365 = 36 亿条/年
  → 保留一年太贵 → 30 天够用（行为特征只看近期）
还款记录: 日增 500 条，一年才 18 万条
  → 保留一年很便宜 → 监管要求必须留
```

### 1.4 分区粒度的选择

```
按天(dt)   = 365 个分区/年 → 信贷/电商 大多数场景
按小时(dt+hour) = 8760 个分区/年 → 广告点击/实时大屏
按月(dt=YYYY-MM) = 12 个分区/年 → 年度报表/审计
```

---

## 二、ADS 数据产品：不是"把 DWS 改个名"（1h）

打开 `src/data/warehouse/ads_layer.py`，三种数据产品各有不同的消费者和格式。

### 2.1 训练样本 — Parquet → 模型训练

```python
def build_training_samples(self, dws_wide_table, label_df):
    """
    消费者: XGBoost 模型训练
    格式: Parquet（列式存储，读取快）
    特点: 宽表（每列一个特征），不需要聚合
    """
    return dws_wide_table.merge(label_df, on='user_id', how='inner')
```

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
```

**为什么包含 p10/p50/p90 三个分位数？**

```
avg_score = 615

场景 A: 分数均匀分布 [500, 730] → avg=615，看起来正常
场景 B: 分数两极分化 [300, 300, 900, 900] → avg=600，看起来也正常

但 p10=300, p90=900 能揭示场景B的异常！
只有 avg 会掩盖分布变化。
```

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
```

**为什么用 JSON？**
- 嵌套结构：`score_distribution` 是一个 dict，CSV 无法直接表达
- 前端友好：`fetch('/api/portfolio') → .json() → render(chart)`
- 一次返回所有数据：不需要前端多次查询

---

## 三、动手练习（1.5h）

### 练习 1：设计电商分区策略（45min）

```
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
```

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
```

---

## 四、检查清单

- [ ] 能说出分区四步法
- [ ] 能解释为什么不同表保留期不同
- [ ] 能解释 Parquet/CSV/JSON 各自的适用场景
- [ ] 完成了电商分区策略设计
