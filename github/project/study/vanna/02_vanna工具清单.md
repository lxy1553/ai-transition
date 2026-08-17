# Vanna 真实工具清单（tools/ 目录全部核实）

> 全部基于 `src/vanna/tools/` 实际代码查证，不凭空写。
> 每个工具 = 名字 + 参数 + 用途 + 说明。

---

## 一、工具总表（5 大类 10 个工具）

| 工具名 | 类名 | 参数 | 用途（description）| 说明 |
|--------|------|------|-------------------|------|
| **run_sql** | `RunSqlTool` | `sql` | 对配置的数据库执行 SQL 查询 | ★ 核心，Vanna 的立身之本 |
| **visualize_data** | `VisualizeDataTool` | `filename`, `title` | 从 CSV 文件创建可视化图表，自动选图型 | ★ 把查询结果画成图表 |
| **save_question_tool_args** | `SaveQuestionToolArgsTool` | `question`, `tool_name`, `args` | 记住"这个问题用这个工具和参数成功了" | 训练式 RAG 的"存" |
| **search_saved_correct_tool_uses** | `SearchSavedCorrectToolUsesTool` | `question`, `limit`, `similarity_threshold`, `tool_name_filter` | 找类似问题之前怎么成功的 | 训练式 RAG 的"查" |
| **save_text_memory** | `SaveTextMemoryTool` | `content` | 存自由文本记忆（洞察/观察/上下文）| 文本记忆 |
| **search_files** | `SearchFilesTool` | `query`, `path` | 按文件名或内容搜索文件 | 文件系统 |
| **list_files** | `ListFilesTool` | `path` | 列出目录下的文件 | 文件系统 |
| **read_file** | `ReadFileTool` | `path` | 读取文件内容 | 文件系统 |
| **write_file** | `WriteFileTool` | `path`, `content` | 写内容到文件 | 文件系统 |
| **edit_file** | `EditFileTool` | `path`, `lines` | 修改文件里的特定行 | 文件系统 |
| **run_python_file** | `RunPythonFileTool` | `script_path` | 用工作区解释器执行 Python 文件 | Python |
| **pip_install** | `PipInstallTool` | `packages` | 用 pip 安装 Python 包 | Python |

> 实际是 **5 类 12 个**工具（我最初 grep 到 10 个，补全了 run_python_file 和 pip_install）。

---

## 二、按类拆分

### 1. 数据查询（Data）—— ★ 最核心

#### RunSqlTool（run_sql）
```python
# tools/run_sql.py
class RunSqlTool(Tool[RunSqlToolArgs]):
    """执行 SQL 查询，用注入的 SqlRunner"""

    @property
    def description(self):
        return "Execute SQL queries against the configured database"

    async def execute(self, context, args):
        # 用 sql_runner 执行，结果存文件供可视化用
        # 返回 DataFrame + 保存 CSV 供 visualize_data 用
        ...
```
**参数**：`sql: str`（要执行的 SQL）
**用途**：用户自然语言 → LLM 生成 SQL → 这里执行 → 返回结果
**关键**：`result.result_for_llm` 回喂给 LLM，同时结果存 CSV 给 visualize_data 用

#### VisualizeDataTool（visualize_data）
```python
# tools/visualize_data.py
class VisualizeDataTool(Tool[VisualizeDataArgs]):
    @property
    def description(self):
        return "Create a visualization from a CSV file. The tool automatically selects an appropriate chart type based on the data."
```
**参数**：`filename`（CSV 文件）+ `title`（可选图表标题）
**用途**：把 run_sql 保存的 CSV 画成图表（Plotly）
**关键**：自动选图型（柱状/折线/饼图等）

### 2. 记忆（Memory）—— 训练式 RAG

#### SaveQuestionToolArgsTool（save_question_tool_args）
```python
# tools/agent_memory.py
class SaveQuestionToolArgsTool(Tool[SaveQuestionToolArgsParams]):
    """记住：这个问题用这个工具和参数成功了"""
```
**参数**：`question`（原问题）+ `tool_name`（用的工具）+ `args`（参数）
**用途**：存"成功查询模式"——训练式 RAG 的"存"

#### SearchSavedCorrectToolUsesTool（search_saved_correct_tool_uses）
```python
# tools/agent_memory.py
class SearchSavedCorrectToolUsesTool(Tool[SearchSavedCorrectToolUsesParams]):
    @property
    def description(self):
        return "Search for similar tool usage patterns based on a question"
```
**参数**：`question` + `limit` + `similarity_threshold` + `tool_name_filter`
**用途**：找类似问题之前怎么成功的——训练式 RAG 的"查"

#### SaveTextMemoryTool（save_text_memory）
```python
# tools/agent_memory.py
class SaveTextMemoryTool(Tool[SaveTextMemoryParams]):
    @property
    def description(self):
        return "Save free-form text memory for important insights, observations, or context"
```
**参数**：`content`（文本）
**用途**：存自由文本记忆

### 3. 文件系统（File System）

| 工具 | 参数 | 用途 |
|------|------|------|
| search_files | `query`, `path` | 按文件名/内容搜索 |
| list_files | `path` | 列目录 |
| read_file | `path` | 读文件 |
| write_file | `path`, `content` | 写文件 |
| edit_file | `path`, `lines` | 改文件特定行 |

### 4. Python 执行

| 工具 | 参数 | 用途 |
|------|------|------|
| run_python_file | `script_path` | 执行 Python 文件 |
| pip_install | `packages` | 装 Python 包 |

---

## 三、这些工具怎么配合（数据流）

```
用户："画一下每月的销售额"
  │
  ▼
Agent 循环 → LLM 决定：
  ├─ 调 run_sql("SELECT month, SUM(sales) FROM orders GROUP BY month")
  │    → 执行 → 结果存 CSV
  │    → result_for_llm 回喂给 LLM
  ├─ LLM 看到结果，再决定：
  │    → 调 visualize_data("query_results_xxx.csv")
  │    → 画成图表返回
  └─ 最终回答
```

**关键配合**：`run_sql` 存 CSV → `visualize_data` 读 CSV 画图。所以 run_sql 的 execute 里有"保存结果到文件"的逻辑（`file_system` 默认 LocalFileSystem）。

---

## 四、`sanitize_tool_parameters` 是工具吗？—— 不是，是配置项

**你问的 `sanitize_tool_parameters` 不是工具**，它是 **AgentConfig 的配置项**（第 3 层脱敏层的开关）：

```python
# core/agent/config.py:108
sanitize_tool_parameters: bool = Field(
    default=True, description="Sanitize sensitive parameters (passwords, tokens)"
)
```

**它的作用**：控制审计日志里要不要把敏感参数（password/token/api_key）打码。

**和工具的关系**：它不是 Tool，而是"**工具被记录时，参数怎么处理**"的配置。

### 区分三个概念（避免混淆）

| 概念 | 是什么 | 位置 |
|------|--------|------|
| **Tool** | 一个能力（run_sql 等）| `tools/` 目录 |
| **ToolRegistry** | 管理所有工具 | `core/registry.py` |
| **sanitize_tool_parameters** | 配置项，控制日志脱敏 | `core/agent/config.py:108` |

> 一句话：`sanitize_tool_parameters` 是"权限五层里第 3 层（脱敏）的开关"，不是工具本身。

---

## 五、落地对照 ai_assistant

你的 ai_assistant 现在只有 1 个"查数"能力。Vanna 的工具清单给你启示——生产级可以拆成多个工具：

| 你现在 | 可以拆成（Vanna 式）|
|--------|-------------------|
| 1 个 sql 生成+执行 | `query_indicator`（查指标）+ `explain_definition`（解释口径）|
| 无记忆 | `save_usage` + `search_usage`（记住成功查询）|
| 无图表 | `visualize_data`（画图）|
| 无审计文件 | `write_file` / `read_file`（存报告）|

**核心**：一个工具 = 一个能力 = name + description + args + execute。LLM 靠 description 决定何时调，靠 args schema 填参数。工具拆得越细，LLM 越能精确调用。

---

# 附：工具从哪来？—— 三层来源（要不要自己写）

> 你问："工具是需要自己写还是直接调用？"
> 答案：**通用内置、连接靠配、业务自写**——分三层。

## ① 内置工具：import 直接用（不用自己写）

`tools/__init__.py` 已导出 12 个内置工具，import 就能用：

```python
from vanna import RunSqlTool, VisualizeDataTool
from vanna.tools import ListFilesTool, SearchFilesTool, ReadFileTool
from vanna.tools import WriteFileTool, EditFileTool, RunPythonFileTool, PipInstallTool
from vanna.tools import SaveQuestionToolArgsTool, SearchSavedCorrectToolUsesTool, SaveTextMemoryTool
```

**但注意**：内置 ≠ 直接能用。它们大多需要**注入依赖**：
- `RunSqlTool(sql_runner=...)` —— 必须传一个 sql_runner（连你的数据库）
- `VisualizeDataTool(chart_generator=...)` —— 必须传画图器

**所以"内置"指"类写好了"，但"连哪个库"要你配。**

## ② 要配的工具：Vanna 不提供，靠集成（integrations/）

Vanna 有 `integrations/` 目录，提供**连接器**（不是 Tool，是 Tool 的依赖）：

| 集成 | 给谁用 | 例子 |
|------|--------|------|
| sqlite / postgres / mysql / clickhouse... | 给 RunSqlTool 当 sql_runner | `RunSqlTool(sql_runner=SqliteRunner("data.db"))` |
| openai / anthropic / ollama... | 给 Agent 当 llm_service | `Agent(llm_service=OpenAILlmService(...))` |
| chromadb / milvus / qdrant... | 给记忆系统 | `DemoAgentMemory()` |

**所以**：查库的工具（run_sql）本身不用写，但"连什么库"要在 integration 里配。

## ③ 自定义工具：必须自己写（Vanna 不帮你）

任何 Vanna 没有的**业务能力**——查征信、查风控指标、发邮件——都要你自己写：

```python
from vanna import Tool, ToolContext, ToolResult
from pydantic import BaseModel

class QueryCreditReportArgs(BaseModel):
    user_id: str

class QueryCreditReportTool(Tool[QueryCreditReportArgs]):
    name = "query_credit_report"
    description = "查询用户征信报告"
    access_groups = ["risk"]          # 只有风控能用

    def get_args_schema(self):
        return QueryCreditReportArgs

    async def execute(self, context, args):
        result = await credit_bureau.query(args.user_id)   # 你的业务逻辑
        return ToolResult(success=True, result_for_llm=str(result))
```

**这是最常见的场景**——Vanna 内置的是"通用能力"（查SQL/读文件），你的"业务能力"（查征信/查风控）全得自己写。

## 那"直接调用"是什么意思？

Vanna 里**没有"直接调用工具"这回事**——**一切工具都由 LLM 通过 ToolRegistry 调用**：

```
你的代码不直接调 RunSqlTool
  ↓
而是：
  LLM 看到 run_sql 的 schema → 返回 ToolCall("run_sql", {...})
  → Agent 循环 → registry.execute(tool_call)
  → 找到 RunSqlTool 执行
```

**你注册、你提供依赖、你写业务工具**；**但"什么时候调、调哪个"由 LLM 决定**。

## 三种情况总结

| 场景 | 你要做什么 |
|------|-----------|
| 用内置工具（run_sql/读文件）| 1. import 2. 配依赖（sql_runner）3. 注册 |
| 用 Vanna 缺的连接（自己的库）| 写一个 integration（实现 sql_runner 接口）|
| 用 Vanna 没有的业务能力 | **写自定义 Tool**（name/description/args/execute）|

**最常见的实际工作**：
1. 大部分是**自定义 Tool**——把业务能力（查征信/查指标/发审批）包成 Tool
2. 小部分是**配内置工具**——连上自己的数据库

## 对应你的 ai_assistant

你的 `ai_assistant` 现在把"查数/解释/血缘"都写在一个 pipeline 里。Vanna 式改造是**拆成 3 个自定义 Tool**：

```python
# 每个都是自定义 Tool（要自己写）
QueryIndicatorTool     # 查指标（复用你的 sql_generator + executor）
ExplainDefinitionTool  # 解释口径（复用你的 RAG）
TraceLineageTool       # 血缘追溯（复用你的 catalog.get_lineage）
```

**核心**：工具不是"调用"出来的，是"注册 + LLM 决定调用"。你的 pipeline 逻辑 → 拆成一个个 Tool 注册进 registry → 让 LLM 在循环里自主选。

> **一句话**：通用内置（import 即用）、连接靠配（integrations/）、业务自写（自定义 Tool）。Vanna 没有"直接调用工具"——永远是"LLM 决定 + Registry 执行"。
