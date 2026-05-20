# AI 转型学习术语表

> 维护规则：每天学习新内容后，把当天出现的新名词、新缩写、新工具、新工程概念追加到本表。
> 表格优先使用“大白话解释”，后续再补真实场景和面试表达。

## 术语总表

| 分类 | 术语 | 英文 / 缩写 | 大白话解释 | 真实场景 / 例子 | 学习阶段 |
|------|------|-------------|------------|------------------|----------|
| 后端与 API | FastAPI | FastAPI | 用 Python 快速写 Web API 的框架。 | 写 `/health`、`/users`、`/ask` 这类接口。 | Day 1 / Day 5 |
| 后端与 API | API | Application Programming Interface | 系统之间约定好的办事窗口，传参数进去，拿结果出来。 | SQL 解释助手以后可以做成 `POST /sql/explain`。 | Day 4 |
| 后端与 API | RESTful API | REST | 一种常见接口设计风格，用 GET、POST、PUT、DELETE 表达动作。 | `GET /users` 查询用户，`POST /users` 创建用户。 | Day 5 |
| 后端与 API | JSON | JSON | 系统之间传数据的常见格式，长得像 Python 字典。 | `{"risk_level": "medium", "can_publish": false}` | Day 4 / Day 10 |
| 后端与 API | Pydantic | Pydantic | Python 里的数据校验工具，检查字段和类型是否正确。 | 校验邮箱、年龄、请求体字段。 | Day 5 |
| LLM 基础 | LLM | Large Language Model | 能理解和生成文字的大语言模型。 | 解释 SQL、总结文档、生成回答。 | Day 8 |
| LLM 基础 | Model | model | 你选择让哪个模型来干活。 | 简单任务用小模型，复杂 RAG 问答用更强模型。 | Day 8 |
| LLM 基础 | Prompt | prompt | 给模型的任务说明书。 | 告诉模型“你是 SQL 解释助手，请解释 SQL 风险”。 | Day 9 |
| LLM 基础 | System Prompt | system prompt | 给模型的长期规矩，定义角色、边界和禁止事项。 | “你是 SQL 解释助手，不要编造表结构。” | Day 8 |
| LLM 基础 | User Prompt | user prompt | 用户这一次具体要模型做的事。 | “请解释下面这段 SQL。” | Day 8 |
| LLM 基础 | Parameters | parameters | 控制模型怎么回答的一组设置。 | `temperature`、`top_p`、`max_tokens`。 | Day 8 |
| LLM 基础 | Response | response | 模型返回的结果。 | 模型返回 SQL 解释、JSON 或自然语言回答。 | Day 8 |
| LLM 基础 | Token | token | 模型处理文字的计费和长度单位。 | 输入越长、输出越长，成本越高。 | Day 8 |
| LLM 基础 | Temperature | temperature | 控制模型回答的发散程度。 | SQL 解释用低温度，文案创作用高温度。 | Day 8 |
| LLM 基础 | Top-p | top_p | 控制模型候选词范围的参数。 | 初学阶段先固定 `top_p = 1`。 | Day 8 |
| LLM 基础 | Max Tokens | max_tokens | 控制模型最多输出多长。 | 太小会截断，太大会啰嗦且更贵。 | Day 8 |
| LLM 基础 | LLM API | LLM API | 调用大模型的接口。 | 把 prompt、模型名、参数发给模型服务，拿到回答。 | 第 3 周前补齐 |
| LLM 基础 | API Key | API Key | 调用模型或外部服务的身份凭证。 | `OPENAI_API_KEY=xxx`，不能提交到 Git。 | 第 3 周前补齐 |
| Prompt 工程 | Prompt 五要素 | Role / Task / Context / Constraints / Format | 好 Prompt 要说清角色、任务、上下文、约束和输出格式。 | SQL 解释 Prompt 要限制模型不要编造字段口径。 | Day 9 |
| Prompt 工程 | Role | Role | 模型当前扮演的角色。 | “你是一个数据仓库 SQL 解释助手。” | Day 9 |
| Prompt 工程 | Task | Task | 要模型完成的具体任务。 | “解释 SQL 的业务含义和风险。” | Day 9 |
| Prompt 工程 | Context | Context | 模型回答问题需要参考的背景信息。 | 表结构、字段含义、指标口径、业务规则。 | Day 9 |
| Prompt 工程 | Constraints | Constraints | 告诉模型哪些事不能乱做。 | “不要编造不存在的表结构。” | Day 9 |
| Prompt 工程 | Output Format | Output Format | 要求模型按固定格式回答。 | 按“业务含义、字段解释、风险提示”输出。 | Day 9 |
| Prompt 工程 | Prompt 模板 | Prompt Template | 可以反复复用的任务说明书。 | `sql_explain_v1`、`sql_risk_v1`。 | Day 9 |
| Prompt 工程 | Prompt 模板版本管理 | Prompt Versioning | 把 Prompt 像代码一样管理版本，方便回滚和对比效果。 | `sql_explain_v1` 到 `sql_explain_v3`。 | 第 3 周前补齐 |
| 结构化输出 | 结构化输出 | Structured Output | 让模型按固定字段返回，而不是随便写一段话。 | 返回 `risk_level`、`can_publish`、`risks`。 | Day 10 |
| 结构化输出 | JSON 合法 | Valid JSON | 格式能被程序解析。 | `{"risk_level": "非常严重"}` 是合法 JSON，但业务不一定能用。 | Day 10 |
| 结构化输出 | 业务校验通过 | Business Validation | 字段、类型、枚举和业务逻辑都符合系统要求。 | `risk_level` 必须是 `low / medium / high`。 | Day 10 |
| 结构化输出 | 固定枚举 | Enum | 字段只能取规定好的几个值。 | `risk_level` 只能是 `low`、`medium`、`high`。 | Day 10 |
| 结构化输出 | 风险等级 | risk_level | SQL 或任务的风险级别。 | `low` 放行，`medium` 复核，`high` 拦截。 | Day 10 |
| 结构化输出 | 是否允许上线 | can_publish | 系统是否允许这段 SQL 或任务继续上线。 | 高风险 SQL 的 `can_publish` 应为 `false`。 | Day 10 |
| 结构化输出 | JSON 输出失败 | JSON Output Failure | 模型没按要求返回可用 JSON。 | 缺字段、类型错、枚举值不合法。 | 第 3 周前补齐 |
| 结构化输出 | 重试策略 | Retry Strategy | 模型输出不合格时，带着错误原因让模型再修正一次。 | 第一次 `risk_level=比较高`，第二次要求改成固定枚举。 | 第 3 周前补齐 |
| Tool Use | Tool Use | Tool Use | 模型负责调度，工具负责真正干活。 | 模型决定调用 `check_sql_risk` 检查 SQL。 | Day 11 |
| Tool Use | 函数调用 | Function Calling | Tool Use 的一种实现方式，模型决定调用哪个函数并生成参数。 | 调用 `check_sql_risk(sql, dialect)`。 | Day 11 |
| Tool Use | Tool | Tool | 给模型使用的外部能力。 | 查表结构、查指标口径、检查 SQL 风险。 | Day 11 |
| Tool Use | Tool Parameters | Tool Parameters | 调用工具时传入的参数。 | `{"sql": "select * from orders", "dialect": "hive"}` | Day 11 |
| Tool Use | Tool Result | Tool Result | 工具执行后返回的结构化结果。 | `{"risk_level": "high", "risks": ["使用 select *"]}` | Day 11 |
| 数据与 SQL | SQL | Structured Query Language | 查询数据库的语言。 | `select city, count(*) from orders group by city`。 | Day 3 / Day 12 |
| 数据与 SQL | SQL 解释助手 | SQL Explainer | 输入 SQL，输出它在做什么、有什么风险、怎么优化。 | 当前项目：`projects/day12_sql_explainer_cli/`。 | Day 12 |
| 数据与 SQL | NL2SQL | Natural Language to SQL | 用户用人话问问题，系统自动生成 SQL。 | “上周每个城市的活跃用户数是多少？”转成 SQL。 | Day 14 |
| 数据与 SQL | 数据问答 | Data Q&A | 业务人员直接问数据问题，系统查数并解释。 | “这个月 GMV 环比上个月涨了多少？” | Day 14 |
| 数据与 SQL | 指标口径 | Metric Definition | 一个指标到底怎么算。 | 活跃用户 = 指定时间内发生 `app_open` 的去重 `user_id`。 | Day 12 / RAG |
| 数据与 SQL | 表结构 | Schema | 一张表有哪些字段、字段类型和字段含义。 | `user_id`、`dt`、`event_name`。 | Day 12 / RAG |
| 数据与 SQL | 分区字段 | Partition Field | 大表里用来缩小扫描范围的字段。 | 常见分区字段是 `dt`。 | Day 12 |
| 数据与 SQL | Group By | GROUP BY | 按字段分组统计。 | `group by city` 表示按城市统计。 | Day 12 |
| 数据与 SQL | Order By | ORDER BY | 对结果排序。 | 大数据场景里全局排序可能很贵。 | Day 12 |
| 数据与 SQL | Select * | SELECT * | 查询所有字段。 | 可能读取不必要字段，也可能暴露敏感字段。 | Day 12 |
| 数据与 SQL | SQL 解析 | SQL Parsing | 让程序看懂 SQL 结构。 | 识别表名、字段、where、group by、order by。 | 第 3 周前补齐 |
| 数据与 SQL | SQL 解析准确性 | SQL Parsing Accuracy | 程序理解 SQL 的结果准不准。 | 复杂 SQL 里正则可能识别错表名或字段。 | 第 3 周前补齐 |
| 数据与 SQL | CTE | Common Table Expression | SQL 里的临时结果，通常用 `with ... as (...)` 写。 | `with t as (...) select * from t`。 | 第 3 周前补齐 |
| RAG | RAG | Retrieval-Augmented Generation | 先从知识库找资料，再让模型基于资料回答。 | 问 active_users 口径时，先检索指标文档。 | Day 15+ |
| RAG | Retrieval | Retrieval | 检索，从知识库里找相关资料。 | 找到和“活跃用户怎么算”最相关的文档片段。 | Day 15+ |
| RAG | Generation | Generation | 生成，模型根据资料组织最终回答。 | 基于口径文档解释 active_users。 | Day 15+ |
| RAG | Embedding | Embedding | 把文字变成一串数字，用来比较语义相似度。 | “活跃用户怎么算”和“active_users 口径”语义接近。 | Day 16+ |
| RAG | 向量数据库 | Vector Database | 存向量并支持相似度搜索的数据库。 | RAG 用它找最相关文档片段。 | Day 16+ |
| RAG | Chunk | Chunk | 文档切片，把长文档切成小段。 | 按标题、段落、问答、指标切分。 | Day 16+ |
| RAG | Top-k | Top-k | 检索时取最相关的前 k 条结果。 | `top_k = 5` 表示取前 5 个片段。 | Day 16+ |
| RAG | 召回 | Recall / Retrieval Recall | 从知识库里把可能相关的资料找出来。 | 用户问 SQL 风险时，先召回 SQL 风险规则相关 chunk。 | Day 16 |
| RAG | 相似度 | Similarity | 衡量问题和文档片段有多相关。 | 相似度越高，越可能进入 top-k 结果。 | Day 16 |
| RAG | 余弦相似度 | Cosine Similarity | 常见向量相似度算法，看两个向量方向是否接近。 | Day 16 Demo 用它计算问题和 chunk 的匹配程度。 | Day 16 |
| RAG | Query Rewrite | Query Rewrite | 把用户问得不清楚的问题改写成更适合检索的问题。 | “这个怎么算？”改成“active_users 指标口径是什么？” | Day 19 |
| RAG | 改写偏移 | Rewrite Drift | query rewrite 改变了用户原意，导致检索命中错误资料。 | 用户问“接口怎么设计”，被错误改成“前端页面怎么设计”。 | Day 22 |
| RAG | 多查询召回 | Multi-query Retrieval | 一个用户问题生成多个 query，一起召回资料。 | 原始问题和补全后的 RAG API query 同时检索。 | Day 22 |
| RAG | 评测集 | Evaluation Set | 固定的一批问题和期望答案，用来判断系统改动是否变好。 | 每次改 top-k、chunk、prompt 后都跑同一批问题。 | Day 23 |
| RAG | 期望引用 | Expected Source | 测试问题应该命中的资料来源。 | “RAG 为什么要引用”应该命中 Day 18 笔记。 | Day 23 |
| RAG | 召回命中率 | Retrieval Hit Rate | 正确资料进入 top-k 的样本比例。 | 20 条问题里 15 条命中 expected source，命中率是 75%。 | Day 23 |
| RAG | 幻觉 | Hallucination | 模型在没有可靠依据时编造看似合理的答案。 | 知识库没有资料时，模型仍然猜测指标口径。 | Day 24 |
| RAG | 拒答 | Refusal | 系统判断不能安全回答，并明确说明原因。 | 无依据、越权、敏感信息或危险操作时拒绝回答。 | Day 24 |
| RAG | 边界控制 | Guardrail | 在模型生成前后限制风险行为的规则和流程。 | 先判断权限、敏感词、检索置信度，再决定是否调用 LLM。 | Day 24 |
| RAG | 澄清 | Clarification | 问题不清楚时先追问，而不是直接猜答案。 | 用户问“这个怎么算”，系统要求补充指标名和时间范围。 | Day 24 |
| RAG 安全 | 数据分级 | Data Classification | 按敏感程度给资料打等级。 | 公开文档、内部文档、薪酬资料和客户名单分开管理。 | Day 25 |
| RAG 安全 | 脱敏 | Masking | 返回或入库前隐藏敏感字段。 | 手机号 `13812345678` 返回前改成 `138****5678`。 | Day 25 |
| RAG 安全 | 权限标签 | Permission Tag | 写在 metadata 里的访问控制信息。 | chunk 标记 `allowed_roles=["hr","admin"]`。 | Day 25 |
| RAG 安全 | 审计日志 | Audit Log | 记录谁在什么时间问了什么、召回了什么、返回了什么。 | 通过 request_id 回放一次越权风险。 | Day 25 |
| RAG | Citation / 引用 | Citation | 回答时标明答案依据来自哪份文档。 | “依据：指标口径文档 - 活跃用户定义”。 | Day 16+ |
| RAG | 知识库 | Knowledge Base | RAG 用来检索资料的文档集合。 | 表结构说明、指标口径、SQL 规范、FAQ。 | Day 15+ |
| RAG | 文档切分 | Document Chunking | 把长文档切成适合检索的小片段。 | 按标题、段落、问答或指标切。 | Day 16+ |
| RAG | 资料治理 | Document Governance | 在入库前先筛选、清洗、脱敏和确认资料是否可信。 | Day 15 先整理知识库清单，而不是直接写向量库代码。 | Day 15 |
| RAG | 知识库清单 | Knowledge Base Inventory | 记录哪些文档要进入知识库、能回答什么问题、怎么切分。 | `docs/knowledge_base_inventory_day15.md`。 | Day 15 |
| RAG | 测试问题 | Test Questions | 用来检查 RAG 是否能检索并回答的问题集合。 | “SQL 解释助手当前能识别哪些风险？” | Day 15 |
| RAG | 入库 | Ingestion | 把原始资料解析、切分、向量化并写入知识库。 | Day 17 脚本把学习笔记写入 SQLite 索引。 | Day 17 |
| RAG | 文档指纹 | Document Hash | 用 hash 标记文档内容，判断文档是否变化。 | 内容没变就不需要重复解析和生成 embedding。 | Day 17 |
| RAG | 元数据 | Metadata | chunk 的附加信息，比如来源、权限、版本、业务域。 | 检索时按权限和业务域过滤结果。 | Day 17 |
| RAG | 索引 | Index | 为了更快检索而建立的数据结构。 | 向量库索引用于快速找相似 chunk。 | Day 17 |
| RAG | 增量更新 | Incremental Update | 只处理新增或变化的文档，不全量重建知识库。 | 文档 hash 变化时才重新入库。 | Day 17 |
| RAG | 在线问答链路 | Online QA Pipeline | 用户提问后，系统检索资料、构造上下文、生成答案并返回引用。 | Day 18 脚本从 SQLite 索引检索 chunk 并返回 citations。 | Day 18 |
| RAG | 引用来源 | Citation Source | 答案背后的资料出处，说明来自哪个文件、chunk 和位置。 | 回答里返回 `source_path`、`chunk_id`、`position`。 | Day 18 |
| RAG | 可追溯 | Traceability | 答案出错时能回查依据，判断是资料错、检索错还是生成错。 | 通过 citations 和日志排查 RAG bad case。 | Day 18 |
| RAG | 召回优化 | Retrieval Optimization | 让系统更容易找到正确资料，并把关键资料排到前面。 | Day 19 对比 top-k 和 query rewrite 的命中效果。 | Day 19 |
| RAG | 命中率 | Hit Rate | 测试问题中成功召回期望资料的比例。 | 4 个测试问题命中 3 个，命中率是 75%。 | Day 19 |
| RAG | Bad Case | Bad Case | 系统没有按预期工作的失败样例。 | 问 SQL 分区却召回了无关 FastAPI 文档。 | Day 19 |
| RAG | 混合检索 | Hybrid Search | 同时使用关键词检索和向量检索。 | 表名字段用关键词，业务语义用向量。 | Day 19 |
| RAG | 重排 | Rerank | 对召回候选重新排序，把最相关资料放前面。 | 先召回 top 30，再 rerank 选 top 5。 | Day 19 |
| RAG | RAG API | RAG API | 把 RAG 问答能力封装成可调用的 HTTP 接口。 | `POST /rag/ask` 输入问题，返回答案和 citations。 | Day 20 |
| 后端与 API | Request ID | Request ID | 每次请求的唯一编号，用来串起日志和排查链路。 | 用户反馈答错时，用 request_id 找到问题、召回和回答。 | Day 20 |
| RAG | 项目收口 | Project Packaging | 把能跑的 Demo 整理成别人能看懂、能启动、能评估的项目。 | README 写清启动命令、接口示例、bad case 和限制。 | Day 21 |
| 工程化 | CLI | Command Line Interface | 命令行工具，在终端输入命令执行。 | `python3 projects/day12_sql_explainer_cli/main.py --example` | Day 12 |
| 工程化 | README | README | 项目说明书，告诉别人项目是什么、怎么运行。 | `projects/day12_sql_explainer_cli/README.md` | Day 13 |
| 工程化 | 日志 | Logging | 程序运行时留下的记录，方便排查问题。 | 请求开始、接口报错、风险等级为 high。 | Day 6 |
| 工程化 | 异常处理 | Exception Handling | 程序出错时不直接崩掉，而是返回清楚错误。 | API 返回统一错误 JSON。 | Day 6 |
| 工程化 | 配置管理 | Configuration Management | 把端口、密钥、日志级别等设置从代码里拆出来。 | `.env`、环境变量、settings 类。 | Day 6 |
| 工程化 | 环境变量 | Environment Variable | 系统级配置，常用来放密钥和环境开关。 | `APP_ENV=dev`、`OPENAI_API_KEY=xxx`。 | Day 6 |

## 每日更新流程

| 步骤 | 要做什么 |
|------|----------|
| 1 | 学完当天笔记后，找出新术语、新缩写、新工具名。 |
| 2 | 判断它属于哪个分类：LLM、Prompt、RAG、SQL、工程化等。 |
| 3 | 用一句大白话解释它。 |
| 4 | 补一个真实场景或项目例子。 |
| 5 | 写上首次学习阶段，例如 `Day 15` 或 `第 3 周前补齐`。 |

## 本阶段最重要的几句话

| 编号 | 记忆句 |
|------|--------|
| 1 | Prompt 不是随便提问，而是任务说明书。 |
| 2 | 结构化输出不是为了好看，而是为了让系统能继续处理。 |
| 3 | Tool Use 是让模型做调度，工具做确定性工作。 |
| 4 | NL2SQL 不只是生成 SQL，还包括理解口径、找表字段、校验风险和解释结果。 |
| 5 | RAG 是先检索资料，再让模型基于资料回答。 |
| 6 | 数据仓库经验可以迁移到 AI 应用：表结构、指标口径、SQL 风险、数据质量都是核心能力。 |
