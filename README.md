# AI 转型学习仓库

## 置顶笔记

- [AI 转型学习术语表](./notes/terminology_glossary.md)：学习过程中遇到的新名字、专业术语和大白话解释。
- [面试核心问题库](./docs/interview_core_questions.md)：每天学习内容沉淀成高频问题和详细精准回答。
- [用户提问与完整回答](./docs/user_questions_answers.md)：保存学习过程中值得反复看的问题和完整回答。
- [生产级 RAG 流程框架图](notes/rag_production_architecture.md)：生产 RAG 的在线问答链路、离线入库链路和各层解释。
- [代码注释规则](./docs/code_commenting_guidelines.md)：旧代码和新代码都要用大白话说明用途、设计原因和风险。

## 背景

当前背景：数据仓库工程师当前目标：在 56 天内完成从数仓工程师到 AI 应用 / 数据+AI 落地方向
的第一轮能力切换

## 目标岗位

- AI 应用工程师
- 数据工程师（AI方向）
- RAG / NL2SQL / 数据问答工程师

## 当前阶段

Day 25：权限与安全 - 敏感信息控制

今天要完成：

- 阅读 `notes/day25_security_controls.md`
- 跑通 `projects/day25_security_controls/`
- 阅读 `docs/day25_security_control_checklist.md`
- 理解 allow、deny、mask 三类安全决策
- 在 `notes/day25_security_controls.md` 中补充并回答 Day 25 核心问题

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

## 今日完成标准

- `projects/day25_security_controls/main.py` 能运行
- 生成 `projects/day25_security_controls/output/security_eval_results.json`
- 生成 `projects/day25_security_controls/output/security_eval_report.md`
- 能说清 RAG 权限过滤、敏感信息脱敏、citations 安全和审计链路
- `notes/day25_security_controls.md` 中的 Day 25 核心问题已填写并通过校验

## 后续规则

- 每天必须留下代码、文档或演示产物
- 每天必须完成当天 note 里的“每日核心问题自测”；
  格式为“我的回答 -> 回答评价 -> 参考答案”，回答正确并补齐参考答案后当天才算完成
- 每天学习内容必须增加“生产实际”部分，说明真实公司里怎么用、会遇到什么问题、如何取舍
- 所有新生成文档按阅读需要换行，不是遇到所有分号或句号都换行；
  单行接近 100 字时，优先在分号、句号或自然语义边界处断行
- 每天沉淀 1-5 个生产级面试问题，低频或学习日记类问题不进入主问题库
- 以后写新代码、修改旧代码时都要补大白话注释，不只写用法，要说明用途、设计原因和可能风险
- 每周至少形成一个可展示的阶段性成果
- 从第 4 周开始同步优化简历和准备投递
