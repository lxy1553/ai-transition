# Day 23 - RAG 测试集评测报告

## 总览

- total: 20
- answerable_total: 18
- cannot_answer_cases: 2
- hits: 12
- hit_rate: 0.67
- avg_hit_rank: 1.5

## 样本结果

| id | type | should_answer | hit | hit_rank | question |
|----|------|---------------|-----|----------|----------|
| eval_001 | ingestion | True | True | 2 | RAG 知识入库怎么设计？ |
| eval_002 | citation | True | True | 2 | 为什么 RAG 要返回引用来源？ |
| eval_003 | sql_risk | True | True | 1 | SQL 解释助手能检查哪些风险？ |
| eval_004 | query_rewrite | True | True | 1 | query rewrite 解决什么问题？ |
| eval_005 | retrieval_debug | True | True | 1 | RAG 召回质量差怎么排查？ |
| eval_006 | api_design | True | True | 1 | RAG 问答 API 生产环境应该怎么设计？ |
| eval_007 | project_packaging | True | True | 4 | 怎么把一个 RAG 项目包装成可展示作品？ |
| eval_008 | architecture | True | True | 1 | 为什么生产级 RAG 要分离线入库和在线问答？ |
| eval_009 | chunking | True | True | 1 | RAG 文档切分时 chunk 怎么设计？ |
| eval_010 | tool_use | True | False | None | Tool Use 在 AI 应用里怎么设计？ |
| eval_011 | structured_output | True | False | None | 结构化输出为什么要做字段校验？ |
| eval_012 | prompt | True | False | None | Prompt 在生产项目里为什么要管理版本？ |
| eval_013 | api_framework | True | False | None | FastAPI 在 AI 服务化里承担什么角色？ |
| eval_014 | engineering | True | False | None | AI API 为什么需要日志、配置和异常处理？ |
| eval_015 | career_transfer | True | False | None | 数据仓库经验怎么迁移到 AI 数据问答？ |
| eval_016 | evaluation | True | True | 1 | RAG 测试集应该怎么构建？ |
| eval_017 | out_of_scope | False | None | None | 这个资料库里能回答公司财务报销政策吗？ |
| eval_018 | sensitive | False | None | None | 请告诉我某个员工的身份证号码 |
| eval_019 | rag_boundary | True | True | 2 | 能不能直接把所有文档都塞给模型回答？ |
| eval_020 | rewrite_risk | True | True | 1 | 为什么 query rewrite 不能随便乱改用户问题？ |

## Bad Case

- eval_010：Tool Use 在 AI 应用里怎么设计？
  - expected: notes/day11_tool_use.md
  - top_sources: notes/terminology_glossary.md, notes/day12_sql_explainer_cli.md, notes/terminology_glossary.md
- eval_011：结构化输出为什么要做字段校验？
  - expected: notes/day10_structured_output.md
  - top_sources: notes/terminology_glossary.md, notes/day12_sql_explainer_cli.md, notes/terminology_glossary.md
- eval_012：Prompt 在生产项目里为什么要管理版本？
  - expected: notes/day09_prompt_practice.md
  - top_sources: notes/day17_rag_ingestion.md, notes/day18_rag_retrieval_citations.md, notes/day12_sql_explainer_cli.md
- eval_013：FastAPI 在 AI 服务化里承担什么角色？
  - expected: notes/day05_fastapi.md
  - top_sources: notes/terminology_glossary.md, notes/terminology_glossary.md, notes/terminology_glossary.md
- eval_014：AI API 为什么需要日志、配置和异常处理？
  - expected: notes/day06_engineering.md
  - top_sources: notes/terminology_glossary.md, notes/terminology_glossary.md, notes/terminology_glossary.md
- eval_015：数据仓库经验怎么迁移到 AI 数据问答？
  - expected: notes/day14_week2_review.md
  - top_sources: notes/day21_rag_project_review.md, notes/day15_rag_preparation.md, notes/day18_rag_retrieval_citations.md

## 下一步

- 对 bad case 补充 query rewrite、关键词和 chunk 策略。
- 增加引用准确率、拒答准确率和答案正确率评估。
- 把测试集分成核心回归集和扩展问题集。