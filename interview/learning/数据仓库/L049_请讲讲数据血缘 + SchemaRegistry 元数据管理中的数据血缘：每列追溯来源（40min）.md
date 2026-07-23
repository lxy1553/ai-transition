---
id: L049
source: learning
category: 数据仓库
title: 请讲讲数据血缘 + SchemaRegistry 元数据管理中的数据血缘：每列追溯来源（40min）
generated: 2026-07-23T15:41:19.864584
---

# 请讲讲数据血缘 + SchemaRegistry 元数据管理中的数据血缘：每列追溯来源（40min）

> 来源: 学习复习计划 | 分类: 数据仓库

### 3.1 血缘的两种形态

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

```

### 3.2 一个特征的完整追溯路径


```
night_ops_ratio_30d = 0.27
  ↑ DWS 聚合: AVG(hour IN [22,23,0,1,2,3,4,5]) 时间窗口30天
  ← dwd_user_behavior.event_time
    ↑ DWD 继承自 ODS（未转换）
    ← ods_user_behavior.event_time
      ↑ SDK 上报
      ← 客户端 App 埋点代码: trackEvent('page_view', timestamp=now())

```

### 3.3 练习：画一条血缘链（20min）

在纸上画出 `on_time_rate` 的完整血缘链：


```
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

```

---