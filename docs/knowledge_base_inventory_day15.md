# Day 15 - RAG 知识库清单

## 目标

为第 3 周 RAG 项目准备第一批可入库资料。

今天只做资料盘点和筛选，不写向量数据库代码。

## 推荐主题

**SQL 解释助手知识库**

原因：

- 能衔接 Day 12-14 的 SQL 解释助手
- 和数据仓库 / NL2SQL / 数据问答方向强相关
- 后续可以自然扩展到指标口径和表结构问答

## 候选资料清单

| 编号 | 文档名称 | 文档类型 | 主要内容 | 可回答的问题 | 是否需要脱敏 | 是否入库 | 切分建议 |
|------|----------|----------|----------|--------------|--------------|----------|----------|
| 1 | `projects/day12_sql_explainer_cli/README.md` | 项目 README | SQL 解释助手功能、运行方式、输出字段 | SQL 解释助手是什么？怎么运行？ | 否 | yes | 按标题切分 |
| 2 | `notes/day12_sql_explainer_cli.md` | 学习笔记 | SQL 解释助手项目目标和任务拆解 | 为什么要做 SQL 解释助手？ | 否 | yes | 按小节切分 |
| 3 | `notes/day13_sql_explainer_enhancement.md` | 学习笔记 | SQL 风险规则和 README 强化 | SQL 常见风险有哪些？ | 否 | yes | 按风险规则切分 |
| 4 | `docs/project_talk_outline_day14.md` | 项目讲解 | SQL 解释助手 30 秒和 1 分钟表达 | 如何介绍 SQL 解释助手项目？ | 否 | yes | 按问答切分 |
| 5 | `notes/day14_week3_prerequisites_review.md` | 过渡笔记 | 进入 RAG 前要补齐的概念 | RAG 前需要补哪些能力？ | 否 | yes | 按主题切分 |
| 6 | `notes/terminology_glossary.md` | 术语表 | AI 转型学习术语解释 | 什么是 RAG、NL2SQL、Embedding？ | 否 | yes | 按表格行或分类切分 |
| 7 | 待补充：真实指标口径文档 | 指标文档 | 指标定义、统计口径、时间范围 | 某个指标怎么算？ | 是 | later | 按指标切分 |
| 8 | 待补充：真实表结构说明 | 元数据文档 | 表名、字段、类型、字段说明 | 某张表有哪些字段？ | 是 | later | 按表切分 |

## 第一批入库资料

- `projects/day12_sql_explainer_cli/README.md`
- `notes/day12_sql_explainer_cli.md`
- `notes/day13_sql_explainer_enhancement.md`
- `docs/project_talk_outline_day14.md`
- `notes/day14_week3_prerequisites_review.md`
- `notes/terminology_glossary.md`

## 10 个 RAG 测试问题

1. SQL 解释助手是什么？
2. SQL 解释助手怎么运行？
3. SQL 解释助手当前能识别哪些风险？
4. 为什么 `select *` 有风险？
5. 为什么缺少 `where` 条件可能导致全表扫描？
6. 为什么数仓大表要关注 `dt` 分区字段？
7. 什么是结构化输出？
8. 什么是 Tool Use？
9. SQL 解释助手后续怎么接入 LLM？
10. SQL 解释助手和 NL2SQL 有什么关系？

## 今日结论

Day 15 的核心是把 RAG 项目的输入准备好。

RAG 的效果很大程度取决于知识库质量。先整理资料、筛选范围、写测试问题，后续做切分、
Embedding、入库和检索时才不会失控。
