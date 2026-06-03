# Day 46 - 错误治理：Prompt 与逻辑修正

这个项目用于 Day 46 的本地练习：把 Day 45 端到端评测报告里的 bad case 转成修复计划，
再重新跑回归评测。

它不接真实 LLM、数据库或知识库，而是模拟修复后的 Agent 输出。
今天的重点是建立错误治理习惯：先归因，再修复，再回归，而不是看到失败就随手改 Prompt。

## 练习目标

- 读取 Day 45 的端到端评测集和失败结果。
- 为每个失败样例定位责任层，例如工具路由、RAG 引用、工具前置条件和异常处理。
- 生成一轮修复计划。
- 对比修复前后的通过率和失败数量。
- 验证修复没有引入新的回归问题。

## 运行方式

在仓库根目录执行：

```bash
python3 projects/day46_error_governance/main.py
```

运行后生成：

```text
projects/day46_error_governance/output/error_fix_plan.json
projects/day46_error_governance/output/before_after_eval_results.json
projects/day46_error_governance/output/error_governance_report.md
```

## 生产映射

真实公司里的错误治理通常会从评测报告或线上 bad case 开始：

- 路由错误：问题进入了错误工具链路。
- 校验缺失：执行类工具绕过了安全、权限或成本校验。
- 引用缺失：RAG 没有可靠来源却给出确定答案。
- 异常误判：数据库、模型或检索失败被包装成业务回答。
- Prompt 漂移：改 Prompt 修了一个问题，却让旧问题退化。

金融信贷 Agent 的错误治理不能只靠 Prompt。
敏感数据、SQL 执行、权限过滤和系统异常必须由确定性规则、工具前置条件和审计链路兜住。
