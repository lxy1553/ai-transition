# Day 12 - 项目 1 雏形：SQL 解释助手 CLI

## 今日主题

SQL 解释助手 CLI：输入 SQL，输出解释、风险和建议

## 今日目标

- 把 Day 9 的 Prompt 思路、Day 10 的结构化输出、Day 11 的 Tool Use 串起来
- 做一个本地可运行的 SQL 解释助手命令行工具
- 输入 SQL 后输出稳定 JSON
- 为后续接入真实 LLM / RAG 留接口

## 真实工作场景

数据开发同学提交一段 SQL，系统需要在上线前给出初步检查：

- 这段 SQL 大概在做什么
- 查了哪些表
- 选择了哪些字段
- 有没有常见风险
- 是否建议直接上线

当前版本先不调用真实大模型，用本地规则模拟“工具层”。

## 今日任务拆解

### 任务 1：设计 CLI 输入

- [ ] 支持 `--example` 使用内置 SQL
- [ ] 支持 `--sql "..."` 传入自定义 SQL
- [ ] 缺少参数时给出提示

### 任务 2：设计结构化输出

输出字段：

| 字段 | 说明 |
|------|------|
| `summary` | SQL 简要说明 |
| `tables` | SQL 涉及的表 |
| `fields` | select 字段 |
| `risk_level` | `low` / `medium` / `high` |
| `can_publish` | 是否建议上线 |
| `risks` | 风险列表 |
| `suggestions` | 修改建议 |
| `missing_context` | 缺少的业务上下文 |

### 任务 3：实现基础风险规则
"使用 select * 会读取不必要字段。", "只选择业务需要的字段。")) "缺少 where 条件，
可能触发全表扫描。", "增加时间范围、分区或业务过滤条件。")) "未发现 dt 分区条件。",
"数仓大表优先补充分区过滤，例如 dt。")) "group by 可能产生较大的聚合开销。",
"确认分组字段基数，必要时先过滤再聚合。")) "order by 可能带来全局排序成本。",
"确认是否必须全局排序，或限制排序数据量。")) "limit 不代表扫描成本一定低。",
"先过滤再 limit，避免无意义扫描。"))

## 运行方式

```bash
cd /Users/lxy/Documents/ai_transition
python3 projects/day12_sql_explainer_cli/main.py --example
```

自定义 SQL：

```bash
python3 projects/day12_sql_explainer_cli/main.py --sql "select * from orders"
```

## 今日完成标准

- [x] CLI 可以运行
- [ ] 输出是合法 JSON
- [ ] 至少识别 5 类 SQL 风险
- [ ] 能解释这个项目和 Day 9-11 的关系

## 今日复盘

待填写：

1. 今天最清楚的概念：
2. 当前 CLI 最大不足：
3. 后续接入 LLM 时要替换哪一层：

---

## 每日核心问题自测

> 回答通过校验后，才把当天学习状态标记为完成。
> 用户回答通过校验前，不提前写参考答案；通过后在对应问题后追加参考答案。

### 1. SQL 解释助手 CLI 要解决什么真实生产问题？

我的回答：


### 2. SQL 解释助手的输出为什么要包含 summary、tables、fields、risks 和 suggestions？

我的回答：


### 3. 当前 CLI 里哪些能力适合用规则实现，哪些能力后续适合接 LLM？

我的回答：


### 4. 为什么 SQL 解释助手不能只输出自然语言解释？

我的回答：


### 5. 这个项目和 Prompt、结构化输出、Tool Use 分别有什么关系？

我的回答：
