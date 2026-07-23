---
id: L055
source: learning
category: 数据仓库
title: 请讲讲PII 脱敏 + DDL 规范 + 合规中的跨业务思考（30min）
generated: 2026-07-23T15:41:19.865465
---

# 请讲讲PII 脱敏 + DDL 规范 + 合规中的跨业务思考（30min）

> 来源: 学习复习计划 | 分类: 数据仓库

### GDPR "被遗忘权"场景


```
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

```

---