# 主干 ②：Pipeline 编排 + 组件抽象（Flow）

> 这是 RAGFlow 的「可编排 ingestion pipeline」骨架——把"解析→分块→分词→向量化"拆成**可拖拽的 DAG 组件**。
> 对照 Vanna 的「Tool 抽象」：Vanna 抽象的是"工具"，RAGFlow 抽象的是"处理组件"。

## 三问

- **Q1 解决什么问题**：把离线链路的每一步（File/Parser/Chunker/Tokenizer...）抽象成统一组件，用 DSL 描述它们的连接关系，可拖拽、可复用、可观测。
- **Q2 数据流哪一环**：离线链路中间——上游 TaskExecutor 拉起 `pipeline.run()`，组件串起来把原始文档变成 chunks。
- **Q3 删掉会怎样**：ingestion 退化成硬编码函数调用，换解析顺序/加步骤都要改代码。

---

## 一、三个核心类的关系

```
Pipeline(Graph)          ← 组件图的执行引擎（DAG 拓扑执行）
   │  持有 self.path（执行路径）、self.components（组件字典）
   │
   ├── File(ProcessBase)      ← 第一个组件：取文档
   ├── Parser(ProcessBase)    ← 解析
   ├── Chunker(ProcessBase)   ← 分块
   ├── Tokenizer(ProcessBase) ← 分词 + embedding
   └── Extractor/Compiler...  ← 更多组件
        ▲
        │ 都继承自
   ProcessBase(ComponentBase)  ← 组件基类：统一 invoke 包装（超时/异常/回调）
```

**核心**：`Pipeline` 只认「组件接口」，不认具体组件——这正是 Vanna 学的「可插拔」在 RAG 链路的体现。

---

## 二、组件基类 ProcessBase（rag/flow/base.py）

```python
class ProcessParamBase(ComponentParamBase):
    def __init__(self):
        super().__init__()
        self.timeout = 100000000       # 组件执行超时
        self.persist_logs = True       # 是否持久化日志

class ProcessBase(ComponentBase):
    def __init__(self, pipeline, id, param: ProcessParamBase):
        super().__init__(pipeline, id, param)
        # ★ 把 callback 绑定到当前组件 id，进度回调会带上组件名
        if hasattr(self._canvas, "callback"):
            self.callback = partial(self._canvas.callback, id)

    async def invoke(self, **kwargs) -> dict[str, Any]:
        """统一包装子类的 _invoke：记录耗时 + 超时 + 异常兜底"""
        self.set_output("_created_time", time.perf_counter())
        for k, v in kwargs.items():
            self.set_output(k, v)                    # 上游输出 → 本组件输入
        try:
            await asyncio.wait_for(self._invoke(**kwargs), timeout=self._param.timeout)
            self.callback(1, "Done")                 # 成功回调
        except Exception as e:
            # 有默认值 → 用默认值兜底；否则记录 _ERROR
            if self.get_exception_default_value():
                self.set_exception_default_value()
            else:
                self.set_output("_ERROR", str(e))
            self.callback(-1, str(e))                # 失败回调
        self.set_output("_elapsed_time", time.perf_counter() - self.output("_created_time"))
        return self.output()

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10 * 60)))
    async def _invoke(self, **kwargs):
        raise NotImplementedError()                   # 子类实现真正逻辑
```

**作用（这段是精华）**：
1. **统一生命周期**：每个组件都是 `invoke() → _invoke()`，`invoke` 统一做「计时、传参、超时、异常兜底、回调」，子类只需写 `_invoke`。
2. **超时两层**：`asyncio.wait_for(timeout)` + `@timeout` 装饰器双保险。
3. **异常兜底**：组件挂了可以配 `get_exception_default_value()` 返回默认值继续跑，或者写 `_ERROR` 让 pipeline 感知。
4. **可观测**：`_created_time` / `_elapsed_time` / callback 进度，每一步耗时、进度都能追踪。

**对照 Vanna**：这就是 Vanna `Tool.execute()` 的"生产级版本"——Vanna 的 execute 只有权限+校验，RAGFlow 的 invoke 多了**超时、异常兜底、耗时追踪、进度回调**。

---

## 三、第一个组件 File（rag/flow/file.py）—— 数据读取

```python
class File(ProcessBase):
    component_name = "File"

    async def _invoke(self, **kwargs):
        if self._canvas._doc_id:
            # ① 知识库里已有文档：按 doc_id 从 DB 查
            e, doc = DocumentService.get_by_id(self._canvas._doc_id)
            self.set_output("name", doc.name)
        else:
            # ② 直接上传的文件：从 kwargs 拿
            file = kwargs.get("file")[0]
            self.set_output("name", file["name"])
            self.set_output("file", file)
        self.callback(1, "File fetched.")
```

**作用**：这是**数据读取**组件——对应你上一个问题「第一步：数据读取」。它统一了两种数据来源：知识库已有文档（`doc_id`）vs 新上传文件（`file`）。后续 Parser 从它的 `name`/`file` 输出里拿数据。

---

## 四、Pipeline 执行引擎（rag/flow/pipeline.py）—— DAG 拓扑执行

```python
class Pipeline(Graph):
    def __init__(self, dsl, tenant_id, doc_id, task_id, flow_id, language):
        # ★ dsl = Canvas 前端拖拽生成的组件图 JSON
        super().__init__(dsl, tenant_id, task_id)
        self._doc_id = doc_id
        ...

    def callback(self, component_name, progress, message=""):
        """组件进度回调：写 Redis 日志 + 更新任务总进度"""
        # 把 (component_name, progress, message, timestamp) 追加到 Redis 的 trace 日志
        # 计算任务总进度 = Σ(每个组件的 progress × 组件权重)
        TaskService.update_progress(self.task_id, {"progress": finished, "progress_msg": msg})
        if has_canceled(self.task_id):
            raise TaskCanceledException(message)      # ★ 取消传播

    async def run(self, **kwargs):
        # ① 没有 path → 从 "File" 组件开始（固定起点）
        if not self.path:
            self.path.append("File")
            cpn_obj = self.get_component_obj(self.path[0])
            await cpn_obj.invoke(**kwargs)

        # ② 取最后一个已跑组件，把它的下游组件追加到 path
        idx = len(self.path) - 1
        cpn_obj = self.get_component_obj(self.path[idx])
        idx += 1
        self.path.extend(cpn_obj.get_downstream())

        # ③ 拓扑执行：逐个 invoke，用上一个的输出当下一个的输入
        while idx < len(self.path) and not self.error:
            last_cpn = self.get_component_obj(self.path[idx - 1])
            cpn_obj = self.get_component_obj(self.path[idx])
            await cpn_obj.invoke(**last_cpn.output())   # ★ 上游 output → 下游 input

            if cpn_obj.error():                         # 组件报错 → 终止
                self.error = "[ERROR]" + cpn_obj.error()
                break
            idx += 1
            self.path.extend(cpn_obj.get_downstream())  # 动态扩展路径

        # ④ 结束回调 + 返回最后组件输出
        self.callback("END", 1 if not self.error else -1, ...)
        if not self.error:
            return self.get_component_obj(self.path[-1]).output()
```

**作用（这是整个编排的核心）**：
1. **DSL 驱动**：组件连接关系（谁在前谁在后）不是硬编码，而是 Canvas 前端拖出来的 DSL JSON。
2. **拓扑执行**：`get_downstream()` 动态扩展路径，相当于遍历 DAG 的拓扑序。不是固定 `File→Parser→Chunker→Tokenizer`，而是**用户怎么连，就怎么跑**。
3. **数据流传递**：`last_cpn.output() → cpn_obj.invoke(**...)`，上游组件的输出 dict 作为下游组件的输入 kwargs，数据在组件间流动。
4. **进度/取消**：每个组件 callback 都汇聚到总进度，取消随时传播（`TaskCanceledException`）。

**对照 Vanna**：`Pipeline.run()` ≈ Vanna 的 `Agent` 的 while 循环——都是"主循环"，只是 Vanna 循环的是"LLM 调工具"，RAGFlow 循环的是"组件处理数据"。

---

## 五、总结

| 概念 | 代码 | 作用 |
|------|------|------|
| ProcessBase.invoke | `base.py:41` | 统一组件生命周期（超时/异常/耗时/回调） |
| File | `file.py:31` | 数据读取组件（doc_id / file 双来源） |
| Pipeline.run | `pipeline.py:123` | DAG 拓扑执行引擎 |
| Pipeline.callback | `pipeline.py:44` | 进度汇聚 + 取消传播 |

**核心心法**：**"组件化 + DSL 编排"是生产级离线链路的骨架**。每个处理步骤是一个组件（可复用、可观测、可单独测），连接关系由 DSL 描述（可拖拽、可版本化、可灰度）。你的 ai_assistant 如果要做可配置的 RAG，就按这个思路拆：`DataSource → Parser → Chunker → Embedder → Indexer` 每个都是组件。
