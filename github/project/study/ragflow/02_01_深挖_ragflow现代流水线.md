# 深挖：rag/flow 现代流水线（Pipeline 组件链）

> 深挖 02 讲 ProcessBase 组件基类。本篇回答"**`rag/flow/` 这套新流水线和旧 TaskExecutor 差在哪、组件怎么串起来**"。
> 核心认知：**旧版是"按 parser_id 查工厂，一个 chunker.chunk() 打到底"；新版把 解析→分块→分词→抽取 拆成可独立编排的 DAG 组件，用 agent 画布 DSL 描述，Pipeline 线性化执行**。
> `compiler/` 不是 DSL 编译器，而是知识图谱编译组件——别被名字骗了。

- 源码位置：`github/project/ragflow/rag/flow/{pipeline,base,file}.py` + `parser/` + `chunker/` + `tokenizer/` + `extractor/` + `compiler/`
- 组件链：`File → Parser → TokenChunker → TitleChunker → Tokenizer → Extractor → Compiler`（**没有 Index 组件**——索引在 `dataflow_service._insert_chunks`）
- 上游：深挖 12_01 的 Canvas 执行引擎（Pipeline 继承 Graph）
- 下游：`dataflow_service.py:94-185` 做 embedding + 索引落库

---

## 三问

- **Q1 解决什么问题**：旧版解析+切块耦合在一种配置里，加一种解析方式要改工厂。新版让每个阶段是独立组件，DSL 描述串联方式。
- **Q2 数据流哪一环**：离线链路核心——文件接入→解析→分块→分词→抽取，正是深挖 03/04/05 的组合框架。
- **Q3 删掉会怎样**：退回旧 TaskExecutor——逻辑耦合，没法独立替换某阶段，没法可视化编排。

---

## 一、整体设计 —— 组件链 + 自动注册

`rag/flow/` 是一组"画布组件"，`__init__.py` 包级扫描自动注册（`__init__.py:35-52`）：跳过 `__init__/_xxx/base`，导入每个模块并用 `inspect.getmembers` 收集类。之后 `component_class()`（agent/component/__init__.py:53-60）按 `["agent.component","agent.tools","rag.flow"]` 依次查找，**字符串节点类型直接反射成 Python 类**。

**与旧 TaskExecutor 的差别**：

```python
# 旧版（task_executor.py:300-317）——按 parser_id 查工厂，一次 chunk() 打到底
chunker = FACTORY[task["parser_id"].lower()]     # 按类型选单个 chunker
cks = await thread_pool_exec(
    chunker.chunk, task["name"], binary=binary, ...)   # 解析+切块耦合在一个函数
```

新版：`File → Parser → TokenChunker → ... → Compiler` 每个是独立 `ProcessBase` 组件，各持参数、校验、输出、进度回调，**DSL 决定串联方式**。

## 二、`Pipeline` —— DAG 构建与线性化执行 ★（pipeline.py:28-42）

```python
class Pipeline(Graph):                            # 直接继承 agent 的 Graph（画布图执行器）
    def __init__(self, dsl, tenant_id=None, doc_id=None, task_id=None, flow_id=None, language=None):
        super().__init__(dsl, tenant_id, task_id)   # Graph 构造：normalize + load
        self._doc_id = doc_id
        self._flow_id = flow_id
        self._kb_id = DocumentService.get_knowledgebase_id(doc_id) if doc_id else None
```

```python
# 执行循环（pipeline.py:123-178）——关键：把 DAG 展平成 path 线性序列
async def run(self, **kwargs):
    if not self.path:
        self.path.append("File")
        cpn_obj = self.get_component_obj(self.path[0])
        await cpn_obj.invoke(**kwargs)              # 入口：File 组件
    idx = len(self.path) - 1
    cpn_obj = self.get_component_obj(self.path[idx]); idx += 1
    self.path.extend(cpn_obj.get_downstream())      # 沿 downstream 展开执行路径
    while idx < len(self.path) and not self.error:
        last_cpn = self.get_component_obj(self.path[idx - 1])
        cpn_obj = self.get_component_obj(self.path[idx])
        async def invoke():
            await cpn_obj.invoke(**last_cpn.output())   # ★ 数据传递：上游完整 output() 作为 kwargs
        tasks = [asyncio.create_task(invoke())]
        await asyncio.gather(*tasks)
        if cpn_obj.error():
            self.error = "[ERROR]" + cpn_obj.error(); break
        idx += 1
        self.path.extend(cpn_obj.get_downstream())
```

**作用（关键）**：`Pipeline` 不做真正并行 DAG——把 DSL 的 `downstream/upstream` 展平成 `self.path` 线性序列，逐步 `cpn.invoke(**上游.output())` 传递数据。每个下游用 Pydantic `*FromUpstream` 模型做输入契约校验（如 `parser.py:1412` 的 `ParserFromUpstream.model_validate(kwargs)`）。

## 三、`ProcessBase` —— 异步组件基类 ★（rag/flow/base.py:26-60）

```python
class ProcessBase(ComponentBase):
    def __init__(self, pipeline, id, param: ProcessParamBase):
        super().__init__(pipeline, id, param)
        if hasattr(self._canvas, "callback"):
            self.callback = partial(self._canvas.callback, id)   # 进度回调绑到 Pipeline

    async def invoke(self, **kwargs) -> dict[str, Any]:
        self.set_output("_created_time", time.perf_counter())
        for k, v in kwargs.items():
            self.set_output(k, v)                               # 上游数据写入 outputs
        try:
            await asyncio.wait_for(self._invoke(**kwargs), timeout=self._param.timeout)
            self.callback(1, "Done")
        except Exception as e:
            if self.get_exception_default_value():
                self.set_exception_default_value()
            else:
                self.set_output("_ERROR", str(e))               # ★ 错误进 output 而非抛异常
            logging.exception(e)
            self.callback(-1, str(e))
        self.set_output("_elapsed_time", time.perf_counter() - self.output("_created_time"))
        return self.output()

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10 * 60)))
    async def _invoke(self, **kwargs):
        raise NotImplementedError()                             # 子类实现业务
```

**作用**：`invoke` 是模板方法——灌 kwargs → 计时 → await `_invoke` → 异常写 `_ERROR` 并回调 `-1` → 返回整个 `output()`。与 agent 同步 `invoke` 同构，flow 版把 `_invoke` 强制为协程并绑定画布 callback。**错误不抛异常，走 `_ERROR` 输出**——这是组件图"出错可路由"的关键。

## 四、各组件主干

**File —— 数据接入**（file.py:31-50）：

```python
async def _invoke(self, **kwargs):
    if self._canvas._doc_id:                       # 走已入库文档
        e, doc = DocumentService.get_by_id(self._canvas._doc_id)
        self.set_output("name", doc.name)          # 只输出文档名
    else:                                          # 走上传文件对象
        file = kwargs.get("file")[0]
        self.set_output("name", file["name"])
        self.set_output("file", file)              # 把 file dict 透传给下游
    self.callback(1, "File fetched.")
```

真正的二进制 blob 由下游 Parser 用 `File2DocumentService.get_storage_address` + `STORAGE_IMPL.get` 或 `FileService.get_blob` 拉取（parser.py:1418-1422）。

**Extractor —— LLM KV 元数据提取**（extractor/extractor.py:37,77-113）：

```python
class Extractor(ProcessBase, LLM):                     # ProcessBase + LLM 双继承
    async def _invoke(self, **kwargs):
        inputs = self.get_input_elements()             # 取上游所有输出
        chunks = []
        for k, v in inputs.items():
            args[k] = v["value"]
            if isinstance(args[k], list):
                chunks = deepcopy(args[k]); chunks_key = k
        if chunks:
            if self._param.field_name == "toc":        # 特例：生成目录
                toc = await self._build_TOC(chunks); chunks.append(toc)
                self.set_output("chunks", chunks); return
            for i, ck in enumerate(chunks):            # ★ 每个 chunk 调一次 LLM
                args[chunks_key] = ck["text"]
                msg, sys_prompt = self._sys_prompt_and_msg([], args)
                ck[self._param.field_name] = await self._generate_async(msg)  # KV：field_name=值
            self.set_output("chunks", chunks)
```

**作用**：对上游每个 chunk 执行一次 LLM 生成，把结果写进 `ck[self._param.field_name]`（如 `summary`/`keywords`，或内置 `toc` 目录模式）。

**Compiler —— 知识图谱编译组件**（compiler/compiler.py:71,510-527）：

```python
class Compiler(ProcessBase, LLM):
    component_name = "Compiler"
    async def _invoke(self, **kwargs):
        # 解析配置的 compilation_template_group → 模板 → RAPTOR/结构编译
        template_ids = resolve_template_ids_from_groups(self._param.compilation_template_group_ids, tenant_id)
        active_templates = load_active_templates(template_ids, tenant_id)
        if tree_templates:
            await self._compile_tree_templates(...)    # ★ RAPTOR 树图落库
        self.set_output("chunks", chunks)
```

**作用（纠正）**：`compiler/` 是"知识编译器"（RAPTOR 树图/结构编译），**不是 DSL 编译器**。真正的 DSL→流水线翻译在 `agent/dsl_migration.py:35-104`（`normalize_chunker_dsl` 把旧节点改名 Splitter→TokenChunker 等）+ `Graph.load`（canvas.py:102-111 把 JSON components 编译成内存组件实例）。

## 五、DSL 样例（rag/flow/tests/dsl_examples/general_pdf_all.json）

```json
{
  "components": {
    "File":        { "obj": {"component_name": "File", "params": {}},
                     "downstream": ["Parser:0"], "upstream": [] },
    "Parser:0":    { "obj": {"component_name": "Parser",
                     "params": {"setups": {"pdf": {"parse_method": "deepdoc", "lang": "Chinese",
                       "suffix": ["pdf"], "output_format": "json"}, ...}}},
                     "downstream": ["TokenChunker:0"], "upstream": ["Begin"] },
    "TokenChunker:0": { "obj": {"component_name": "TokenChunker",
                       "params": {"chunk_token_size": 512, "delimiters": ["\n"], "overlapped_percent": 0}},
                     "downstream": ["Tokenizer:0"], "upstream": ["Parser:0"] },
    "Tokenizer:0": { "obj": {"component_name": "Tokenizer", "params": {}},
                     "downstream": [], "upstream": ["TokenChunker:0"] }
  },
  "path": []
}
```

**作用**：DSL 就是"组件 id → {component_name, params} + 前后向边"的邻接表，`path` 留空由 `run()` 从 File 开始按 downstream 展开。`title_chunker.json` 是 `File → Parser → TokenChunker → TitleChunker`，TitleChunker 带 `levels`（标题正则）与 `hierarchy` 参数。

---

## 六、数据流示意

```
DSL JSON (components{id→{obj,downstream,upstream}} + path)
   │  normalize_chunker_dsl()         agent/dsl_migration.py:35  旧组件名迁移
   ▼
Pipeline(Graph) 构造                canvas.py:90-111  Graph.load()
   │  component_class(name)(graph, id, param)   实例化 File/Parser/... 为 ProcessBase
   ▼
Graph.components: { "File": obj, "Parser:0": obj, ... }
   │  Pipeline.run()  pipeline.py:123
   ▼
path 展开：File → Parser:0 → TokenChunker:0 → Tokenizer:0   （get_downstream 线性化）
   │  每步: cpn.invoke(**last_cpn.output())     pipeline.py:154
   │        └─ ProcessBase.invoke(): 灌 kwargs → await _invoke() → set_output → 回调
   ▼  数据契约（Pydantic FromUpstream 校验）
File        → {"name","file"}                    file.py:50
Parser:0    → {"output_format":"json","json":[...bboxes...]}   parser.py:1412/781
TokenChunker→ {"output_format":"chunks","chunks":[{text,doc_type_kwd,...}]}  token_chunker.py:550
Tokenizer   → {"chunks":[{text,content_ltks,q_*_vec,...}],"embedding_token_consumption":N}  tokenizer.py:203
   ▼
Pipeline.run() 返回末尾组件 output() 的 dict（chunks）
   ▼
DataflowService.run_dataflow  dataflow_service.py:94-185
   _embed_chunks() → _process_chunks() → _insert_chunks() → ES/Infinity 索引（"Index"在这层，不在 rag/flow）
```

---

## 七、对照 ai_assistant

| RAGFlow | 你的 ai_assistant | 差距 |
|---------|------------------|------|
| 阶段即组件（File/Parser/Chunker/Tokenizer） | 一个大 pipeline 函数 | ❌ 阶段耦合 |
| DSL 描述串联方式 | 代码写死顺序 | ⚠️ 换流程要改代码 |
| 每组件独立校验 + 进度回调 | 无 | ⚠️ 无法定位卡在哪阶段 |
| `_ERROR` 输出短路而非抛异常 | 抛异常全崩 | ⚠️ 单阶段失败无法路由 |
| FromUpstream 输入契约 | dict 随手传 | ⚠️ 字段错误运行时才炸 |
| compiler 知识编译（RAPTOR） | 无 | 概念参考 |

**落地优先级**：
- **P0**：**阶段即函数、数据契约化**——解析/切块/向量各一个纯函数，输入输出用 dataclass/字典 schema 固定，每个阶段可单测。
- **P1**：阶段级进度回调——每阶段报进度+错误信息，前端能定位"卡在解析还是卡在向量化"。
- **P2**：DSL/配置化编排（可换组件顺序）。

---

## 八、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 自动注册 | `__init__`（35） | 包级扫描收集组件类 |
| DAG 构建 | `Pipeline(Graph)`（pipeline:28） | DSL → 组件实例 |
| 线性执行 | `run`（123） | downstream 展平 + invoke |
| 组件基类 | `ProcessBase`（base:26） | 灌 kwargs + 计时 + `_ERROR` |
| 数据入口 | `File`（file:31） | 文档名 / 上传对象 |
| 元数据 | `Extractor`（extractor:37） | 每 chunk LLM 提取 KV |
| 知识编译 | `Compiler`（compiler:71） | RAPTOR 树图落库 |

**一句话心法**：**流水线的本质是"把流程拆成可独立替换的组件 + 用数据契约连接"**。旧版是"一个大函数顺序执行"，新版是"每个阶段一个组件、上游 `output()` 就是下游 `kwargs`"。组件化的价值不在并行，在**可替换、可观测、可测试**。
