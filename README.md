# AI 转型学习仓库

## 置顶笔记

- [AI 转型学习术语表](./notes/terminology_glossary.md)：学习过程中遇到的新名字、专业术语和大白话解释。
- [面试核心问题库](./docs/interview_core_questions.md)：每天学习内容沉淀成高频问题和详细精准回答。
- [用户提问与完整回答](./docs/user_questions_answers.md)：保存学习过程中值得反复看的问题和完整回答。
- [生产级 RAG 流程框架图](notes/rag_production_architecture.md)：生产 RAG 的在线问答链路、离线入库链路和各层解释。
- [代码注释规则](./docs/code_commenting_guidelines.md)：旧代码和新代码都要用大白话说明用途、设计原因和风险。
- [规则更新记录](./docs/rule_update_log.md)：记录规则什么时候更新、改了什么、影响哪些文档。

## 背景

当前背景：金融信贷开发工程师。当前目标：在 56 天内完成从金融信贷开发到 AI 应用 / 信贷+AI 落地方向
的第一轮能力切换

## 目标岗位

- AI 应用工程师
- 数据工程师（AI方向）
- RAG / NL2SQL / 数据问答工程师

## 当前阶段

Day 30：问题解析 - 指标、维度、时间抽取（进行中）

今天要完成：

- 阅读 `notes/day30_nl2sql_question_parser.md`
- 跑通 `projects/day30_nl2sql_question_parser/`
- 理解指标、维度、时间范围、过滤条件和 TopN 的抽取方式
- 生成问题解析结果和准确率报告
- 在 `notes/day30_nl2sql_question_parser.md` 中回答 Day 30 核心问题

## 仓库结构

```text
.
├── config/
├── data/
├── docs/
├── launchd/
├── logs/
├── notes/
├── plans/
├── projects/
├── scripts/
└── README.md
```

## 56 天主线

- 第1周：定位、Python、API、FastAPI、工程化基础
- 第2周：LLM、Prompt、结构化输出、SQL 解释助手
- 第3周：RAG 入门与项目化
- 第4周：RAG 优化、评测、幻觉控制、安全
- 第5周：NL2SQL
- 第6周：服务化、Docker、配置、测试、部署
- 第7周：Agent 工作流与作品扩展
- 第8周：简历、面试、投递与收官

详细计划见：[plans/ai_56_day_plan.md](/Users/longfeiguo/PycharmProjects/bi_cube1/ai_transi
tion/plans/ai_56_day_plan.md)

## Day 30 完成标准

- `projects/day30_nl2sql_question_parser/main.py` 能运行
- 生成 `projects/day30_nl2sql_question_parser/output/question_parse_results.json`
- 生成 `projects/day30_nl2sql_question_parser/output/question_parse_report.md`
- 能说清 NL2SQL 问题解析为什么要先抽指标、维度、时间和过滤条件
- `notes/day30_nl2sql_question_parser.md` 中的 Day 30 核心问题已填写并通过校验

## 后续规则

- 每天必须留下代码、文档或演示产物。（2026-04-22 建立）
- 每天必须完成当天 note 里的“每日核心问题自测”；（2026-05-15 建立，2026-05-20 完善）
  格式为“我的回答 -> 回答评价 -> 参考答案”，回答正确并补齐参考答案后当天才算完成
- 每日自测问题统一使用 `### 序号. 问题`；（2026-05-21 二次更新）
  下一行写两个空格缩进的 `我的回答：`，后面留空行，下一题再另起标题
- 每天的自测题必须加入前 2 天最核心问题；（2026-05-21 更新）
  每 7 天复盘日还要加入上一周最核心问题，方便回顾前一段学习内容
- 后续新增或修改学习规则时，必须写入 `docs/rule_update_log.md`；
  记录日期、变更内容和影响范围。（2026-05-21 更新）
- 每天学习内容必须增加“生产实际”部分；（2026-05-20 更新）
  说明真实公司里怎么用、会遇到什么问题、如何取舍
- 后续业务例子默认结合金融信贷开发背景；（2026-05-25 更新）
  优先使用授信申请、额度审批、风控规则、反欺诈、放款、还款、逾期、贷后、催收和合规审计场景
- 所有新生成文档按阅读需要换行，不是遇到所有分号或句号都换行；（2026-05-20 更新）
  单行接近 100 字时，优先在分号、句号或自然语义边界处断行
- 新增术语时不能只写术语名，必须解释术语含义；（2026-05-25 更新）
  同时补充英文 / 缩写、大白话解释和真实项目例子
- 每天沉淀 1-5 个生产级面试问题；（2026-05-20 更新）
  低频或学习日记类问题不进入主问题库
- 以后写新代码、修改旧代码时都要补大白话注释；（2026-05-20 更新）
  不只写用法，要说明用途、设计原因和可能风险
- 每周至少形成一个可展示的阶段性成果。（2026-04-22 建立）
- 从第 4 周开始同步优化简历和准备投递。（2026-04-22 建立）
