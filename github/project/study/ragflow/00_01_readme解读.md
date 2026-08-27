# RAGFlow README 深度解读（含源码验证）

> 学习方式：README 讲"设计意图"，源码验证"真实实现"。
> 本文把 README 的每个卖点，对应到真实代码路径。
>
> 项目位置：`github/project/ragflow`
> 完成时间：2026-08-20

---

## 一、RAGFlow 是什么？（README 一句话）

> **A leading open-source RAG engine that fuses cutting-edge RAG with Agent capabilities.**
> 领先的开源 RAG 引擎，把 RAG 和 Agent 能力融合，给 LLM 提供"上下文层"。

关键定位（README.md:78）：
- **不是**"又一个 LLM 封装库"，而是**完整的 RAG 引擎**（带 UI、带存储、带编排）。
- 核心差异化：**"Quality in, quality out"** —— 通过 DeepDoc 深度文档理解，从复杂非结构化数据里提取高质量知识。

**代码位置**：整个仓库的核心在 `rag/`（Python 引擎）+ `deepdoc/`（文档理解）+ `api/`（服务层）。

---

## 二、四大核心卖点 → 源码验证

README 的 Key Features 逐个对源码：

### 1. 🍭 "Quality in, quality out"（DeepDoc 深度文档理解）

**README 说**：从复杂格式的非结构化数据里提取知识。

**源码真相**：`deepdoc/` 目录，核心是"文档解析 + OCR + 版面识别 + 表格结构识别"：

```
deepdoc/
├── parser/          # 各格式解析器（pdf/docx/excel/html/markdown/epub...）
│   ├── pdf_parser.py        # 2145 行，PDF 解析（含版面/表格/OCR）
│   ├── docx_parser.py       # Word 解析
│   ├── excel_parser.py      # Excel 解析
│   └── ...
└── vision/          # 视觉理解
    ├── ocr.py               # OCR（PaddleOCR/Tesseract）
    ├── layout_recognizer.py # 版面分析（标题/正文/表格/图）
    ├── table_structure_recognizer.py  # 表格结构识别（识别表格行列）
    └── recognizer.py        # 视觉模型识别
```

**关键**：普通 RAG 只是"抽文本"，RAGFlow 是"**先版面分析 → 识别标题/正文/表格/图片 → 表格单独结构化 → 图片走 OCR/VLM**"，所以复杂 PDF 也能切对。

### 2. 🍱 Template-based chunking（模板化分块）

**README 说**：智能、可解释、多种模板可选。

**源码真相**：`rag/app/` 下每种文档类型一个模板，`rag/svr/task_executor.py:111` 的 FACTORY 分派：

```python
FACTORY = {
    "general": naive,                 # 通用
    ParserType.PAPER.value: paper,    # 论文（按标题层级切）
    ParserType.BOOK.value: book,      # 书籍
    ParserType.LAWS.value: laws,      # 法律（按条款切）
    ParserType.QA.value: qa,          # 问答对
    ParserType.TABLE.value: table,    # 表格
    ParserType.RESUME.value: resume,  # 简历
    ...
}
```

**关键**：不同类型文档用不同分块策略——这就是"模板化分块"，比 LangChain 的"一刀切 RecursiveCharacterTextSplitter"更精细。

### 3. 🌱 Grounded citations（可追溯引用、减少幻觉）

**README 说**：可视化分块、快速查看引用、支撑有据回答。

**源码真相**：每个 chunk 带 `page_num_int`、`position_int`、`doc_id` 等元数据（`rag/nlp/search.py:156-170` 的 fields），检索后能定位到"原文档哪一页哪一行"，前端高亮引用。

### 4. 🎮 可编排 ingestion pipeline（2025-10-15 新增）

**README 说**：ingestion 流水线可编排。

**源码真相**：`rag/flow/` 目录——把"解析→分块→分词→embedding"拆成**可拖拽的 DAG 组件**：

```python
# rag/flow/pipeline.py:28
class Pipeline(Graph):          # ★ 继承 agent.canvas.Graph，DSL 描述组件图
    async def run(self, **kwargs):
        # 从 path 依次取组件，invoke 后 get_downstream() 扩展路径
        # 组件顺序由 Canvas（前端拖拽）生成的 DSL 决定，不是硬编码
```

**关键**：这是 RAGFlow 相比旧版的架构升级——把 ingestion 从"硬编码函数调用"变成"可编排组件图"。

---

## 三、技术栈全景（README 架构 → 源码目录）

| 层 | README 说 | 源码目录 |
|----|----------|---------|
| **接入层** | REST API + Web UI | `api/`(Quart/Python) + `internal/`(Go) + `web/`(React) |
| **离线链路** | 文档解析/分块/向量化 | `rag/flow/` + `deepdoc/` + `rag/svr/task_executor.py` |
| **在线链路** | 检索/重排/生成 | `rag/nlp/search.py` + `rag/llm/rerank_model.py` + `rag/app/` |
| **LLM 层** | 多模型可插拔 | `rag/llm/`（chat/embedding/rerank/cv/ocr） |
| **Agent 层** | Agentic workflow + MCP | `agent/`（canvas/component/plugin/tools/sandbox） |
| **存储层** | ES/Infinity/OpenSearch + MySQL/PG + Redis + MinIO | `common/doc_store/` + `api/db/` |

---

## 四、数据流全图（文档 → 答案）

结合源码画出的完整流程（这是整个项目最核心的图）：

```
① 用户上传文档 (PDF/Word/Excel...)
  │
  ▼
② api/ 接收 → 存 MinIO → 写 MySQL 文档记录 → 发 Redis 队列任务
  │
  ▼
③ TaskExecutor（rag/svr/task_executor.py）
  │  消费 Redis 队列，按 FACTORY[parser_type] 分派到 rag/app/naive.py 等
  │  限流：task_limiter / chunk_limiter / embed_limiter / minio_limiter
  ▼
④ Parser 解析（deepdoc + rag/flow/parser）
  │  PDF→版面分析→识别标题/正文/表格/图→表格结构化→OCR
  │  产出：sections（文本块）+ tables（结构化表格）
  ▼
⑤ Chunker 分块（rag/flow/chunker）
  │  按模板切分（delimiter 切分 / token 合并），带 overlap，表格附上下文
  ▼
⑥ Tokenizer 分词（rag/flow/tokenizer）
  │  多路分词：title_tks / content_ltks / important_kwd / question_tks
  ▼
⑦ Embedding 向量化（rag/llm/embedding_model）
  │  批处理 encode，truncate 到 max_length，标题向量加权
  │  产出 q_{dim}_vec 字段
  ▼
⑧ 写入文档库（ES/Infinity）：chunk 文本 + 向量 + 关键词 + 元数据
  │
  ▼  ──── 以上是离线链路，以下是在线链路 ────
  │
⑨ 用户提问 query
  ▼
⑩ Dealer.search（rag/nlp/search.py）
  │  混合检索：向量(cosine) + full_text(BM25) → weighted_sum fusion
  ▼
⑪ Rerank 重排（rag/llm/rerank_model）
  │  相似度打分，归一化到 [0,1]，精排 top-N
  ▼
⑫ 拼上下文 → LLM 生成（带引用）→ 返回用户
```

**关键洞察**：步骤 ③-⑧ 就是你上一个问题问的"RAG 离线链路"，RAGFlow 把它做到了生产级（队列、限流、多引擎、元数据、增量）。

---

## 五、RAGFlow 最值得学的 5 个点（学习价值排序）

1. **可编排 ingestion pipeline**（`rag/flow/`）—— 把离线链路抽象成"组件图"，可拖拽、可复用、可观测。这是"生产级 RAG 离线链路"的骨架。
2. **DeepDoc 深度文档理解**（`deepdoc/`）—— 复杂 PDF/表格的处理，是普通 RAG 和高质量 RAG 的分水岭。
3. **混合检索 + 重排**（`rag/nlp/search.py` + `rerank_model.py`）—— 向量 + BM25 fusion + 归一化重排，召回质量的关键。
4. **LLM 五类抽象可插拔**（`rag/llm/`）—— chat/embedding/rerank/cv/ocr 各自 Base + 30+ provider，换模型不改主流程。
5. **任务调度 + 限流**（`rag/svr/`）—— 队列消费、并发限流、进度回调，生产级工程的样板。

---

## 六、对照我的 `ai_assistant` 项目

| RAGFlow 概念 | 我的 ai_assistant | 差距 |
|-------------|------------------|------|
| Parser 多引擎（Pdf/Docling/MinerU） | 只读文本/SQL | ❌ 该支持复杂文档解析 |
| Chunker 模板化分块 | 固定分块 | ❌ 该按类型分块 |
| Tokenizer 多路分词 | 无 | ❌ 该加关键词/标题加权 |
| Embedding 批处理 + 限流 | 单条调用 | ❌ 该批处理 + 限流 |
| Dealer 混合检索（向量+BM25） | 纯向量 | ❌ 该加关键词检索 |
| Rerank 归一化重排 | 无重排 | ❌ 该加重排 |
| 任务队列 + 限流器 | 同步执行 | ❌ 该异步化 |

**结论**：你的 ai_assistant 在"知识接入"上还停留在 demo 级——RAGFlow 的 Parser/Chunker/Embedding/检索四件套，就是你 RAG 该长成的样子。

---

## 七、下一步学习指引

- **阶段 2·主干①**：读 `rag/svr/task_executor.py`（离线任务调度入口）
- **阶段 2·主干②**：读 `rag/flow/base.py` + `pipeline.py`（组件抽象 + DAG 编排）
- **阶段 2·主干③**：读 `rag/flow/parser/parser.py` + `deepdoc/`（文档解析）
- **阶段 2·主干④-⑦**：读 chunker / tokenizer+embedding / llm / search

> 学习心法：每学一个组件，问"我的 ai_assistant 缺这个吗？该怎么加？"——然后把 RAGFlow 式组件重构进自己的项目。
