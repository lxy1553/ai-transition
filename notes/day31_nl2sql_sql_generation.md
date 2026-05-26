# Day 31 - NL2SQL SQL 生成：从结构化解析到只读 SQL

## 今日目标

今天继续第 5 周 NL2SQL 主线。

Day 29 做 Schema Catalog 和候选表选择。
Day 30 做问题解析，把用户问题拆成指标、维度、时间范围、过滤条件和风险标记。
Day 31 进入 SQL 生成，但重点不是“让模型随便写 SQL”，而是：

- 把结构化解析结果转换成 SQL 草稿；
- 只使用 Schema Catalog 里的表和字段；
- 默认生成只读查询；
- 对敏感字段和缺少时间范围的问题拒绝生成；
- 生成后留下 SQL、候选表、阻断原因和静态校验结果。

今天产出：

- 一个规则版 NL2SQL SQL 生成脚本；
- 一份 SQL 生成结果 JSON；
- 一份 SQL 生成 Markdown 报告；
- Day 31 核心问题自测。

---

## 大白话解释

NL2SQL 的 SQL 生成不是让模型从零开始“猜一段 SQL”。
更稳的做法是让前面的链路先把信息准备好：

```json
{
  "question": "上周每个渠道的授信通过率是多少？",
  "query_type": "group_by",
  "metrics": ["approval_rate"],
  "dimensions": ["channel"],
  "time_range": "last_week",
  "filters": {},
  "risk_flags": []
}
```

然后 SQL 生成器只在可信范围内拼出 SQL：

```sql
select
  channel,
  sum(approval_count) / nullif(sum(application_count), 0) as approval_rate
from dws_credit_application_daily
where dt between date_trunc('week', current_date) - interval '7' day
  and date_trunc('week', current_date) - interval '1' day
group by channel;
```

这里真正重要的不是 SQL 语法，而是几个约束：

- `approval_rate` 不能直接平均，要尽量用分子分母重新计算；
- `channel` 必须是候选表里的维度；
- 时间范围必须落到 `dt`；
- 只能查白名单表；
- 不能生成手机号、身份证这类敏感查询；
- 生成后还不能直接执行，要交给 SQL 校验层。

---

## 生产实际

在金融信贷公司里，NL2SQL 很容易被业务同学用来问：

- 昨天授信申请量是多少？
- 上周每个渠道的授信通过率是多少？
- 最近 7 天放款金额趋势怎么样？
- 本周逾期率比上周变化多少？
- 查询申请 A123 的审批状态。

这些问题看起来都像“查数”，但生产风险完全不同。

| 场景 | 生成 SQL 时要注意什么 |
|------|------------------------|
| 授信申请量 | 必须有时间范围，避免扫全量申请汇总表 |
| 授信通过率 | 不能简单 `avg(approval_rate)`，优先用 `sum(approval_count) / sum(application_count)` |
| 放款金额趋势 | 要按 `dt` 分组，不能只返回一个总金额 |
| 逾期率对比 | 要拆成两个时间窗口，不能把本周和上周混在一个 where 里 |
| 申请明细 | 必须有申请编号这类精确过滤，且字段要受权限控制 |
| 客户手机号 | 不应该生成 SQL，应该在生成前拒绝或走授权流程 |

生产里的 SQL 生成层通常不是最后一道防线。
完整链路应该是：

```text
用户问题
-> 问题解析
-> Schema Router
-> SQL 生成
-> SQL 校验
-> 权限校验
-> 成本预估
-> 查询执行
-> 结果解释
-> 审计日志
```

Day 31 只做到 SQL 生成。
Day 32 会继续做 SQL 校验，检查危险关键字、字段白名单、时间范围、limit、权限和扫描成本。

---

## SQL 生成的核心输入

SQL 生成器至少需要三类输入。

| 输入 | 作用 |
|------|------|
| `parse_result` | 告诉系统要查什么指标、按什么维度看、时间范围是什么 |
| `schema_catalog` | 告诉系统哪些表字段真实存在、哪些字段是指标、维度、时间字段 |
| `generation_policy` | 告诉系统哪些 SQL 能生成，哪些必须拒绝 |

如果没有 `parse_result`，模型容易漏掉时间、维度和过滤条件。
如果没有 `schema_catalog`，模型容易编造字段。
如果没有 `generation_policy`，模型可能生成写操作、敏感字段查询或高成本 SQL。

---

## 常见 SQL 生成策略

### 1. 模板生成

对常见问题类型使用固定模板：

- metric：`select 聚合指标 from 表 where 时间条件`
- group_by：`select 维度, 聚合指标 from 表 where 时间条件 group by 维度`
- trend：`select dt, 聚合指标 from 表 where 时间条件 group by dt`
- topn：`group by 维度 order by 指标 desc limit N`
- detail：`select 明细字段 from 明细表 where 精确条件 limit N`

优点是稳定、可解释、容易测试。
缺点是覆盖不了复杂表达和复杂 join。

### 2. LLM 生成

把 Schema Catalog、问题解析结果和约束放进 prompt，让模型生成 SQL。

优点是能处理复杂表达。
缺点是更容易出现幻觉、字段编造、口径偏差和不可控 SQL。

生产里更常见的是混合方式：

```text
简单问题用模板；
复杂问题让 LLM 生成；
无论哪种方式，最后都必须过 SQL 校验器。
```

---

## 今日项目

项目路径：

```text
projects/day31_nl2sql_sql_generator/
```

运行：

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day31_nl2sql_sql_generator/main.py
```

输出：

```text
projects/day31_nl2sql_sql_generator/output/sql_generation_results.json
projects/day31_nl2sql_sql_generator/output/sql_generation_report.md
```

当前结果：

```text
total: 10
generated: 8
blocked: 2
validation_failed: 0
```

两个被拦截的例子：

- `导出客户手机号列表`：命中敏感字段和敏感查询；
- `各风险等级的授信通过量`：缺少时间范围，不能直接扫大表。

---

## 工程取舍

Day 31 先做规则版 SQL 生成，而不是直接接 LLM。

原因：

- 当前目标是先把 NL2SQL 链路跑通，形成稳定 baseline；
- 常见指标、维度、TopN、趋势查询可以先用模板覆盖；
- 规则版输出稳定，方便 Day 32 做 SQL 校验；
- 以后接 LLM 时，可以拿规则版结果做对照评测；
- 金融信贷场景有权限和合规要求，不适合第一步就让模型自由生成。

但是规则版也有边界：

- 复杂 join 支持弱；
- 复杂口径需要更多指标配置；
- 对模糊问题不如 LLM 灵活；
- 不同 SQL 方言的日期函数可能不同；
- 对比查询、占比查询、漏斗查询还需要专门模板。

生产里比较稳的路线是：

```text
先规则 baseline
-> 加 SQL 校验器
-> 加固定测试集
-> 再引入 LLM 生成复杂 SQL
-> 用评测集比较准确率、拒答率、越权率和执行成本
```

---

## 面试沉淀

Q071：NL2SQL 生成 SQL 时为什么必须加 Schema 约束？

### 回答

NL2SQL 生成 SQL 时必须加 Schema 约束，因为模型本身不知道真实数据库里有哪些表、字段、指标口径和权限边界。
如果只让模型根据自然语言生成 SQL，它可能编造不存在的字段，选错事实表，漏掉分区条件，
或者访问敏感字段。

生产里应该把 Schema Catalog、指标定义、字段角色、时间字段和权限标签作为 SQL 生成的输入。
生成器只能使用白名单里的表字段，不能自由发明字段名。
生成后还要经过 SQL 校验，确认只读、字段合法、时间范围完整、权限允许、成本可控。

Q072：为什么 SQL 生成后不能直接执行？

### 回答

SQL 生成后不能直接执行，因为生成正确语法不代表业务正确、安全或低成本。
它还可能存在口径错误、字段越权、缺少时间范围、扫描大表、没有 limit、危险关键字或 join 放大。

在金融信贷场景里，SQL 可能涉及客户隐私、授信审批、风控评级、逾期和贷后数据。
这些数据有明显权限边界和审计要求。
所以生成 SQL 后必须经过只读校验、表字段白名单校验、权限校验、时间范围校验、成本预估和审计记录。
只有通过校验的 SQL 才能进入执行层。

Q073：规则模板生成 SQL 和 LLM 生成 SQL 怎么取舍？

### 回答

规则模板适合高频、结构清楚、口径稳定的问题，比如授信申请量、放款金额趋势、TopN 城市和逾期率对比。
它的优点是稳定、可解释、容易测试，也更适合作为生产 baseline。

LLM 适合复杂表达、跨表关联、模糊意图和非标准问法。
但 LLM 更容易出现字段编造、口径偏差和不稳定输出。

生产里通常不会二选一。
更稳的做法是简单问题走模板，复杂问题走 LLM，但两者都必须使用同一套 Schema Catalog、权限规则和 SQL 校验器。
最终看固定测试集上的准确率、拒答率、越权率、执行成本和可维护性。

---

## 术语更新

今天新增或强化这些术语：

- SQL Generation / SQL 生成
- Read-only SQL / 只读 SQL
- SQL Template / SQL 模板
- Time Predicate / 时间条件
- SQL Validation / SQL 校验

这些术语已补充到：

```text
notes/terminology_glossary.md
```

---

## 每日核心问题自测

> 回答通过校验后，才把当天学习状态标记为完成。
> 用户回答通过校验前，不提前写参考答案；通过后在对应问题后追加参考答案。

### A. 今日核心问题

### 1. NL2SQL 生成 SQL 时为什么必须加 Schema 约束？
  我的回答：

### 2. 为什么 SQL 生成后不能直接执行？
  我的回答：

### 3. 规则模板生成 SQL 和 LLM 生成 SQL 怎么取舍？
  我的回答：

### 4. 金融信贷场景里，SQL 生成层必须拦截哪些问题？
  我的回答：

### 5. 为什么授信通过率、逾期率这类比例指标不能随便 `avg()`？
  我的回答：

### B. 前两天核心回顾

### 6. [Day 29] NL2SQL 为什么不能直接把用户问题交给模型生成 SQL？
  我的回答：

### 7. [Day 29] Schema Catalog 在 NL2SQL 里解决什么问题？
  我的回答：

### 8. [Day 30] NL2SQL 为什么要先做问题解析，而不是直接生成 SQL？
  我的回答：

### 9. [Day 30] 指标抽取和维度抽取有什么区别？
  我的回答：
