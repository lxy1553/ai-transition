---
id: Q120
source: interview_core
category: NL2SQL
title: 离线 NL2SQL 的 SQL Validator 通常要检查哪些内容？
generated: 2026-07-23T15:41:19.825476
---

# 离线 NL2SQL 的 SQL Validator 通常要检查哪些内容？

> 来源: 核心题库 | 分类: NL2SQL

离线 NL2SQL 的 SQL Validator 至少要检查：是否只读、表是否在白名单或 Catalog 中、字段是否存在、
是否命中敏感字段、用户是否有权限、是否带时间范围、是否带分区条件、扫描范围是否超限、
是否访问 ODS/DWD 明细、是否有危险函数或子查询、limit 是否合理、join 是否在允许关系内。

金融信贷场景里，重点是控制客户隐私、口径一致和扫描成本。
普通指标查询应优先走 ADS/DWS；DWD 明细只能在授权排查场景下访问；手机号、身份证号、银行卡号和客户名单必须阻断。
如果用户没给时间范围，Agent 应先澄清；如果 SQL 缺分区条件，应阻断执行。

Validator 的价值是把模型生成的不确定结果变成可控的工程动作。