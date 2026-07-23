---
id: L057
source: learning
category: 数据仓库
title: 请讲讲分区策略 + 数据产品设计中的ADS 数据产品：不是"把 DWS 改个名"（1h）
generated: 2026-07-23T15:41:19.865701
---

# 请讲讲分区策略 + 数据产品设计中的ADS 数据产品：不是"把 DWS 改个名"（1h）

> 来源: 学习复习计划 | 分类: 数据仓库

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