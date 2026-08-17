# Vanna 完整学习计划

> 学习目标：通过拆解 Vanna 2.0 开源项目，学习 AI Agent 落地的硬能力 + 软能力
> 项目位置：`/Users/lxy/Documents/ai_transition/github/project/vanna`
> 学习笔记：本目录（study/vanna）
> 开始时间：2026-08-14

---
vanna 目前包含：
┌──────┬──────────────┬───────────────────┐
  │ 护栏 │    Vanna     │  你 ai_assistant  │
  ├──────┼──────────────┼───────────────────┤
  │ 评测 │ 框架✅ │      │ 评测集 55 条 ✅   │
  │      │ 无评测集     │                   │
  ├──────┼──────────────┼───────────────────┤
  │ 权限 │ 框架✅      │ │ 指标级 ✅（比    │
  │      │ 无权限表     │ Vanna 全）        │
  ├──────┼──────────────┼───────────────────┤
  │ 审计 │ 框架✅      │ │ audit_logger ✅    │
  ├──────┼──────────────┼───────────────────┤
  │ 降级 │ 接口未接线   │ 无（该补）        │
  └──────┴──────────────┴───────────────────┘
还缺少 rag+nl2sql 落地项目，数据仓库项目，ml 落地项目

# ⭐ 置顶：AI 应用开发三大核心能力支柱 + ML

> 这是整体能力地图——所有学习都应服务这三个支柱 + ML 认知。
> 定位：AI 应用开发工程师。

## 三支柱 + ML 总览

```
   用户问题
     │
     ▼
┌─────────────────────────┐
│ ③ 工程化护栏（能上线/可信）│
│   评测 │ 权限 │ 降级 │ 审计 │
│   ┌─────────────────┐  │
│   │ ① Agent 编排     │  │
│   │  LLM ↔ 工具 循环  │  │
│   │   ┌───────────┐ │  │
│   │   │ ② 知识接入  │ │  │
│   │   │ RAG/NL2SQL │ │  │
│   │   └───────────┘ │  │
│   └─────────────────┘  │
└─────────────────────────┘
    +
   📊 ML 机器学习（应用决策，非训练细节）
```

- **① 编排是骨架**（怎么执行）
- **② 知识是血肉**（知道什么）
- **③ 工程是护栏**（能上线）
- **ML 是基础认知**（应用决策，非训练细节）

---

## 支柱 ①：Agent 编排 —— 让 LLM 做"复杂任务"

**本质**：不是"问一句答一句"，而是"让 LLM 在循环里自主决定下一步"。

**核心概念**（Vanna 学的）：
- while 循环 + `is_tool_call()` 判断
- 工具抽象（name + description + args + execute）
- 结果回喂、多步推理
- 上下文管理（记忆、压缩、指代消解）

**为什么最核心**：这是"脚本"和"Agent"的分水岭。会调 API 的人很多，但能让 LLM"自主拆任务、调工具、看结果再决定"的人少。你的 ai_assistant 缺的就是这个（8 步 if-else vs while 循环）。

## 支柱 ②：知识与数据接入 —— 让 LLM 知道"具体的事"

**本质**：LLM 只有通用知识，你的业务数据（信贷指标、公司文档）要"喂"给它。

**核心概念**：
- RAG（检索→增强→生成）：文档切分、向量检索、重排
- NL2SQL / 数据问答：自然语言→SQL→答案
- 工具注入（run_sql 查数）

**为什么核心**：没有知识接入，LLM 只会"瞎编"。RAG/NL2SQL 是 AI 应用"接地气"的关键——也是你数仓背景的差异化优势。

## 支柱 ③：生产级工程化 —— 让系统"能上线、可信"

**本质**：把 demo 变成产品——可靠、安全、可观测、可控成本。

**核心概念**（Vanna 学的）：
- 评测体系（准确率、bad case 归因）
- 权限分层（认证/授权/脱敏/RLS/审计）
- 降级与兜底（超时、重试、撞上限）
- 可观测（日志、指标、追踪）
- 成本控制（缓存、模型分级）

**为什么核心**：AI 应用岗位的 JD 反复出现"工程化落地"——这一支柱决定你能不能过面试、能不能上线。

## 📊 ML 机器学习：应用决策，不是训练细节

**定位**：AI 应用开发**不要求 ML 工程师深度**，但要求"ML 认知"——分清三层：

| 层 | 要求 | 内容 | 你的现状 |
|----|------|------|---------|
| ① LLM 原理 | **必须懂** | Transformer/Attention/Token/Embedding/微调概念 | 正在学（大模型工程）|
| ② 传统 ML 基础 | **建议懂** | XGBoost/特征工程/过拟合/AUC | ✅ 已超过（信贷项目）|
| ③ 深度训练 | **不需要** | 反向传播/自己训Transformer | 别陷进去（ML工程师的事）|

**学习重点**：AI 应用面试官问的 ML 是**应用导向**（"什么时候微调 vs RAG""Embedding 怎么选""为什么表格数据用XGBoost"），不是让你讲反向传播。**你的 ML 学习 = 应用决策，不是训练细节。**

**你的差异化优势**：credit_risk_control_system（XGBoost + 特征工程 + 模型评估）——这是很多 AI 应用候选人没有的。

## 三支柱 + ML 关系总结

- ① 编排是骨架（怎么执行）—— 你最缺，最该补
- ② 知识是血肉（知道什么）—— 你已超过 Vanna
- ③ 工程是护栏（能上线）—— 你有雏形，缺降级/RLS
- ML 是基础（应用决策）—— 你已超过平均

> **三者缺一不可**：只有编排没工程 = 能跑但上不了线；只有工程没编排 = 是脚本不是 Agent；只有编排没知识 = 会执行但不懂业务。

---

# ⭐ 核心认知：框架 vs 手写编排

> 来源：Vanna 没用到 LangChain/LangGraph，而是自己手搓了 Agent 编排（while 循环 + Tool 抽象 + 记忆）。这揭示了编排的本质。

## Vanna 的技术栈真相

Vanna **没有用 LangChain/LangGraph**——依赖只有 pydantic/httpx/pandas 等基础库。它**自己手写了**：
- while 循环（agent.py:646）≈ LangGraph 的图
- Tool 抽象（core/tool/base.py）≈ LangChain 的 Tool
- AgentMemory ≈ LangChain 的 Memory
- conversation 消息管理 ≈ LangGraph 的 State

## 框架的作用：不是"更容易写"，而是"补上手写版缺的能力"

| 能力 | Vanna 手写版 | LangGraph 封装版 |
|------|-------------|-----------------|
| 循环控制 | ✅ 手写 while | ✅ 图结构 |
| 消息管理 | ✅ 手动 add_message | ✅ 状态自动 |
| **断点/恢复** | ❌ **没有**（查证）| ✅ checkpoint 持久化 |
| **中断续跑** | ❌ 没有 | ✅ 断点恢复 |
| **并行/分支** | ❌ 靠代码 | ✅ 图节点天然 |
| **可视化** | ❌ 无 | ✅ LangSmith 追踪 |

## 框架三层价值

1. **少写样板**（最小价值）—— 简单循环本来就能写
2. **状态持久化 + 断点恢复**（关键价值）—— 长任务中断恢复，手写要自己造
3. **可视化调试**（额外价值）—— LangSmith 看每步

## 结论：先手写，需要时再上框架

```
简单编排（数据问答，单Agent顺序执行）
  → 手写 while 循环就够了，用框架反增学习成本
复杂编排（长任务恢复 / 多Agent协作 / 并行分支）
  → 才需要 LangGraph
```

**学习路径**：先手写 while 循环（学 Vanna 懂原理）→ 遇到复杂编排再上 LangGraph（降维打击）。**别陷入"做 Agent 必须用框架"的误区。**

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
| ① | **Agent 循环** | `agent.py` 646-1040 | while + ToolCall + finish_reason + 生产级分支 | `01_主干01_Agent循环.md` | ✅ 完成 |
| ⓑⓒ | **循环外扩展点** | `workflow/` + `lifecycle/` + `middleware/` | WorkflowHandler / LifecycleHook / LlmMiddleware | `01_主干01_Agent循环.md`（含扩展点）| ✅ 完成 |
| ② | **Tool 抽象** | `core/tool/base.py`（70行）| 名字+描述+参数schema+执行+权限 | `02_主干02_Tool抽象.md` | ✅ 完成 |
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
| 阶段2·主干① | `01_主干01_Agent循环.md`（含生产级分支）| ✅ |
| 阶段2·扩展点 | `01_主干01_Agent循环.md`（含扩展点） | ✅ |
| 阶段2·问题交互图 | `01_主干01_Agent循环.md`（含交互图） | ✅ |
| 阶段2·步骤①②③ | `06_主干06_用户权限.md`（resolve_user/空消息/before_message + 权限五层）| ✅ |
| 阶段2·权限专题 | `05` 追加四/五/六节（transform_args表级/权限数据来源/权限建模vs数据vs选型）| ✅ |
| 阶段2·步骤④-⑦ | 待产出 | ⬜ 下一步解析步骤④ workflow_handler |

> **追加学习记录（2026-08-14）**：
> 用户对主干①的整体理解经 grill-me 审查，修正 3 个顺序错误 + 1 个概念混淆：
> 1. `empty`/`is_refusal` 是对 **LLM response** 的判断，应放 **循环内 response 之后**，不是"问题刚进来"
> 2. 漏了最前面的 `resolve_user`（agent.py:257，解析"谁在问"）
> 3. 4 个 LifecycleHook 钩子散布全链路（373 循环前 / 787、848 循环内 / 1119 循环后）
> 4. LlmMiddleware 在**循环内部每次迭代**跑（1244/1290），不是"循环前一步"
> 详见 `01_主干01_Agent循环.md`（含交互图）。

总时长约 15 小时，分 3-4 天。

---

## 学习心法

1. 别按文件读，按数据流读
2. 对照 `ai_assistant` 项目读
3. 学完动手改（把 8 步 if-else 改成 while 循环）
