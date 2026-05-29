# Day 33 - NL2SQL 查询执行与结果格式化

这个项目练习 NL2SQL 的第五步：只执行已经通过 Day 32 校验的安全 SQL，
并把数据库返回结果整理成稳定的接口响应结构。

生产环境里，查询执行层不是简单 `execute(sql)`。
它至少要做这些事：

- 只接收 SQL Validator 放行的 SQL；
- 使用只读连接或查询网关访问数据库；
- 控制超时、返回行数和结果大小；
- 跳过被校验层阻断的高风险 SQL；
- 把结果格式化成指标卡、趋势表、对比结果或明细表；
- 记录执行状态，方便审计和排查。

## 运行方式

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day33_nl2sql_query_executor/main.py
```

## 输出文件

```text
projects/day33_nl2sql_query_executor/output/nl2sql_demo.sqlite
projects/day33_nl2sql_query_executor/output/query_execution_results.json
projects/day33_nl2sql_query_executor/output/query_execution_report.md
```

## 生产映射

真实生产里，Day 33 对应查询网关或只读查询服务。
它位于 SQL 校验之后、结果解释之前。

```text
用户问题
-> 问题解析
-> Schema Router
-> SQL 生成
-> SQL 校验
-> 查询执行
-> 结果解释
```

本地脚本使用 SQLite 和固定样例数据模拟执行链路。
这样可以先把“只执行安全 SQL、返回结构化结果”的工程习惯练起来，
后续再替换成真实数仓、Postgres、ClickHouse 或公司内部查询服务。
