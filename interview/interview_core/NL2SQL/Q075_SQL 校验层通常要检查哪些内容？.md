---
id: Q075
source: interview_core
category: NL2SQL
title: SQL 校验层通常要检查哪些内容？
generated: 2026-07-23T15:41:19.819959
---

# SQL 校验层通常要检查哪些内容？

> 来源: 核心题库 | 分类: NL2SQL

SQL 校验层至少要检查三类内容，每类都有具体的检查项和处理方式：

第一，安全约束（硬阻断）：
- 只读检查：只能包含 SELECT，禁止 INSERT/UPDATE/DELETE/DROP/TRUNCATE
- 敏感字段检查：字段是否命中 restricted 列表（手机号、身份证号、银行卡号）
- 危险函数检查：是否包含系统命令、文件读写等危险函数
- 权限检查：当前用户是否有该表、该字段的查询权限

第二，业务和 Schema 约束（硬阻断或预警）：
- 表白名单检查：表名是否在 Schema Catalog 中注册
- 字段存在性检查：每个字段是否在 Catalog 的字段列表中
- 指标口径校验：大表查询是否带了时间范围或分区条件
- 明细查询检查：是否含有精确过滤条件（如 order_id、user_id）和 LIMIT
- 跨域检查：JOIN 的表之间是否存在允许的关联关系

第三，性能和成本约束（预警或限流）：
- 分区裁剪检查：SQL 中是否包含分区字段条件（如 WHERE dt='2026-07-01'）
- 扫描范围检查：扫描分区数是否超过阈值（如超过 31 天需审批）
- LIMIT 检查：明细查询是否有 LIMIT 且数值合理（不超过 1000 行）
- 排序检查：ORDER BY 是否有 LIMIT，防止全局排序
- JOIN 检查：是否涉及大表全字段 JOIN 或笛卡尔积

这些检查用代码层规则 + SQL parser（sqlparse/sqlglot）+ 权限系统 + 查询网关
共同完成，不能依赖模型判断。校验结果要有明确的 blocked_reasons、检查项列表和错误码。