# Day 32 - NL2SQL SQL 校验器

这个项目练习 NL2SQL 的第四步：对 Day 31 生成的 SQL 草稿做执行前校验。

SQL 生成正确不代表能执行。生产环境里还要检查：

- 是否只读；
- 是否包含危险关键字；
- 是否使用白名单表；
- 是否查询敏感字段；
- 大表查询是否带时间范围；
- 明细查询是否带精确过滤和 `limit`；
- 是否存在 `select *`、未知表、未知字段等风险。

## 运行方式

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day32_nl2sql_sql_validator/main.py
```

## 输出文件

```text
projects/day32_nl2sql_sql_validator/output/sql_validation_results.json
projects/day32_nl2sql_sql_validator/output/sql_validation_report.md
```

## 生产映射

真实生产里，SQL Validator 应该位于 SQL 生成之后、查询执行之前。
它不是为了“挑模型毛病”，而是作为执行前安全闸门，阻止越权、敏感字段泄露、
危险写操作、大表全量扫描和不可控成本。

