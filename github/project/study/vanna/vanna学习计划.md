# Vanna 完整学习计划

> 学习目标：通过拆解 Vanna 2.0 开源项目，学习 AI Agent 落地的硬能力 + 软能力
> 项目位置：`/Users/lxy/Documents/ai_transition/github/project/vanna`
> 学习笔记：本目录（study/vanna）
> 开始时间：2026-08-14

---

## 设计原则

跟着"数据流"走，不按文件行数走。每个阶段 = 一个完整的数据流环节，学完能画出来。

对照自己的 `ai_assistant` 项目读：每学一个概念，问"我的项目缺这个吗？该怎么加？"

---

## 阶段 0：建立心智模型（30 分钟）

| 读什么 | 学到什么 |
|--------|---------|
| `README.md` | 2.0 新特性、整体定位（自然语言→SQL→答案） |
| `MIGRATION_GUIDE.md` | 从旧版到 2.0 的演进，理解为什么这么设计 |
| `src/vanna/__init__.py` | 顶层导出的核心概念清单（Agent、Tool、LlmService...） |

**产出**：能说出"Vanna = Agent（LLM + 工具循环）+ 可插拔集成 + UI 组件"。

**完成情况**：✅ 已完成（拆解时读过）

---

## 阶段 1：跑通最小示例（2 小时）

**核心文件：`src/vanna/examples/mock_sqlite_example.py`**

用 MockLLM（无需 API Key）+ SQLite（无需数据库服务），完整展示 Tool → ToolRegistry → Agent.send_message 的用法。

读的顺序：
1. `create_demo_agent()` —— Agent 怎么组装
2. `MockSqliteLlmService` —— LLM 怎么模拟返回 ToolCall
3. `main()` —— 怎么用 agent.send_message()

**产出**：跑通它，亲眼看到"LLM 说调 run_sql → Agent 执行 → 结果回喂 → LLM 回答"循环。

**状态**：⬜ 进行中

---

## 阶段 2：抓主干——七核心抽象（逐个产出 md）

> 主干 = 真正要读透的核心（约 400 行）。外围（UI/观测/legacy）不读。
> 方法：**三问法**（每个模块问：①解决什么问题 ②在数据流哪一环 ③删掉会怎样）
> **抓主干 + 对照动手**：每学一个抽象，对照 `ai_assistant` 给改造动作。

### 七个主干清单（逐个拆解，一个主干一个 md）

| # | 主干 | 核心位置 | 学习要点 | 产出 md | 状态 |
|---|------|---------|---------|--------|------|
| ① | **Agent 循环** | `agent.py` 646-1040 | while + ToolCall + finish_reason + 生产级分支 | `04_主干①_Agent循环.md` | ✅ 完成 |
| ⓑⓒ | **循环外扩展点** | `workflow/` + `lifecycle/` + `middleware/` | WorkflowHandler / LifecycleHook / LlmMiddleware | `04b_循环外扩展点与响应分类.md` | ✅ 完成 |
| ② | **Tool 抽象** | `core/tool/base.py`（70行）| 名字+描述+参数schema+执行+权限 | `05_主干②_Tool抽象.md` | ⬜ 下一步 |
| ③ | **Registry 分派** | `core/registry.py` | execute 带权限/校验/审计 | `06_主干③_Registry.md` | ⬜ |
| ④ | **LlmService 抽象** | `core/llm/base.py`（40行）| send_request + stream_request + validate_tools | `07_主干④_LlmService.md` | ⬜ |
| ⑤ | **models** | `core/tool/models.py` | ToolCall / ToolResult / ToolContext | `08_主干⑤_models.md` | ⬜ |
| ⑥ | **用户/权限** | `core/user/` | User + UserResolver + RequestContext | `09_主干⑥_用户权限.md` | ⬜ |
| ⑦ | **记忆** | `capabilities/agent_memory/` + `tools/agent_memory.py` | 记住成功查询模式（训练式RAG）| `10_主干⑦_记忆.md` | ⬜ |

**产出**：能画出"User → Agent 循环 → Tool → Registry → LLM → 记忆"完整交互图。

---

## 阶段 3：看真实集成（2 小时）

| 文件 | 学到什么 |
|------|---------|
| `integrations/sqlite/sql_runner.py` | 把数据库包装成 Tool 的 execute |
| `integrations/mock/llm.py` | Mock LLM 怎么实现 LlmService |
| `integrations/openai/llm.py` 或 `ollama/llm.py` | 真实 LLM 怎么实现 LlmService |

**学到**：可插拔 = 每种数据库/LLM 实现同一接口，Agent 只认接口。

---

## 阶段 4：学记忆系统（2 小时）

```
capabilities/agent_memory/base.py         ← 记忆接口
integrations/chromadb/agent_memory.py     ← 向量库实现
tools/agent_memory.py                     ← 记忆工具
```

**学到**：Vanna 会记住成功查询模式，下次复用——训练式 RAG 的精髓，自己项目缺的。

---

## 阶段 5：看服务层 + UI（2 小时）

| 文件 | 学到什么 |
|------|---------|
| `servers/fastapi/app.py` | Agent 怎么包成 API |
| `servers/fastapi/routes.py` | 路由怎么对接 send_message |
| `servers/base/chat_handler.py` | 流式响应怎么推给前端 |

**学到**：Agent 项目怎么从"代码"变成"可部署服务 + 可看界面"。

---

## 阶段 6：评测体系（2 小时）

```
core/evaluation/dataset.py     ← 评测数据集
core/evaluation/evaluators.py  ← 评估器
core/evaluation/report.py      ← 报告
core/evaluation/runner.py      ← 跑评测
```

**学到**：系统化评估 NL2SQL Agent —— 自己 eval_qa.py 该长成的样子。

---

## 学习顺序总览

```
阶段0 读README + __init__  →  建立心智模型        （产出 01_readme解读.md ✅）
阶段1 跑通最小示例          →  最小Agent+工具循环  （产出 02_最小示例跑通.md ✅）
阶段2 抓主干七核心抽象       →  逐个拆解产md        （产出 04/04b ✅ → 05-10 进行中）
阶段3 3个集成实现          →  理解可插拔
阶段4 记忆系统            →  学训练式RAG
阶段5 FastAPI + UI       →  学落地成产品
阶段6 评测体系            →  学系统化评估
```

## 当前进度（2026-08-14）

| 步骤 | 产出 | 状态 |
|------|------|------|
| 阶段0 | `01_readme解读.md` | ✅ |
| 阶段1 | `02_最小示例跑通.md` + 2个脚本 | ✅ |
| 阶段2·主干① | `04_主干①_Agent循环.md`（含生产级分支）| ✅ |
| 阶段2·扩展点 | `04b_循环外扩展点与响应分类.md` | ✅ |
| 阶段2·问题交互图 | `04c_完整交互图.md` | ✅ |
| 阶段2·步骤①②③ | `05_主干②_权限与用户解析.md`（resolve_user/空消息/before_message）| ✅ |
| 阶段2·权限专题 | `05` 追加四/五/六节（transform_args表级/权限数据来源/权限建模vs数据vs选型）| ✅ |
| 阶段2·步骤④-⑦ | 待产出 | ⬜ 下一步解析步骤④ workflow_handler |

> **追加学习记录（2026-08-14）**：
> 用户对主干①的整体理解经 grill-me 审查，修正 3 个顺序错误 + 1 个概念混淆：
> 1. `empty`/`is_refusal` 是对 **LLM response** 的判断，应放 **循环内 response 之后**，不是"问题刚进来"
> 2. 漏了最前面的 `resolve_user`（agent.py:257，解析"谁在问"）
> 3. 4 个 LifecycleHook 钩子散布全链路（373 循环前 / 787、848 循环内 / 1119 循环后）
> 4. LlmMiddleware 在**循环内部每次迭代**跑（1244/1290），不是"循环前一步"
> 详见 `04c_完整交互图.md`。

总时长约 15 小时，分 3-4 天。

---

## 学习心法

1. 别按文件读，按数据流读
2. 对照 `ai_assistant` 项目读
3. 学完动手改（把 8 步 if-else 改成 while 循环）
