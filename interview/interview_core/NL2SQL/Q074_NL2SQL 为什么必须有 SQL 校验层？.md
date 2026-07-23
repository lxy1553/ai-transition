---
id: Q074
source: interview_core
category: NL2SQL
title: NL2SQL 为什么必须有 SQL 校验层？
generated: 2026-07-23T15:41:19.819767
---

# NL2SQL 为什么必须有 SQL 校验层？

> 来源: 核心题库 | 分类: NL2SQL

NL2SQL 必须有 SQL 校验层，因为生成 SQL 的语法正确不代表可以安全执行。

模型可能产生五类危险 SQL：
1. 越权 SQL——包含 restricted 敏感字段（手机号/身份证号/银行卡号）
2. 高危 SQL——包含 DELETE/UPDATE/DROP/TRUNCATE 危险关键字
3. 全扫 SQL——大表查询没有 WHERE 分区条件，可能扫描数百 GB 历史数据
4. 无限 SQL——明细查询没有 LIMIT，可能返回数十万行
5. 高成本 SQL——两张 DWD 级明细表全字段 JOIN 或无条件 ORDER BY

在金融信贷场景里，这些 SQL 可能执行在授信流水表、风控评分表、逾期催收表上，
一旦出现数据泄露或生产库被打爆，后果远不是"回答错了"这么简单。

SQL 校验层的位置必须在 SQL 生成之后、查询执行之前，不与生成器耦合。
校验不通过的 SQL 一律不进入执行层，返回 blocked_reasons 和错误码。
校验逻辑必须用确定性代码实现（SQL parser + 规则引擎 + 权限系统 + 查询网关），
不能依赖模型判断。只有这样，安全边界才是硬约束，而不是模型的心情。