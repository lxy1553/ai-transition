# Day 53 - 离线 NL2SQL + SQL 安全

这个项目用于 Day 53 的本地练习：把金融信贷离线指标问题转换成 SQL，并在执行前做安全校验。

它不调用真实大模型。脚本用规则模拟 NL2SQL 链路，重点放在生产约束：

- 优先查询 ADS/DWS，不直接查 ODS/DWD 明细；
- SQL 必须只读；
- 必须有时间范围和分区条件；
- 禁止访问手机号、身份证号、客户名单等敏感字段；
- 控制扫描天数和返回行数；
- SQL 通过校验后才允许执行。

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day53_offline_nl2sql_sql_safety/main.py
```

运行后生成：

```text
projects/day53_offline_nl2sql_sql_safety/output/offline_warehouse.sqlite
projects/day53_offline_nl2sql_sql_safety/output/nl2sql_cases.json
projects/day53_offline_nl2sql_sql_safety/output/nl2sql_eval_results.json
projects/day53_offline_nl2sql_sql_safety/output/offline_nl2sql_sql_safety_report.md
```

## 生产映射

真实金融信贷 Agent 里，离线指标查询链路一般是：

```text
用户问题
-> 主题域和意图识别
-> 指标字典确认口径
-> Schema Catalog 找 ADS/DWS 表和字段
-> 生成候选 SQL
-> SQL Validator 校验只读、分区、权限、成本和敏感字段
-> 查询执行
-> 结果解释
-> 审计记录
```

Day 53 的重点是：SQL 生成不是终点，SQL 安全校验和执行控制才是能上线的关键。
