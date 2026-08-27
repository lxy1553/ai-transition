# 深挖：Agent 核心组件实现（base / LLM / Message / Retrieval）

> 深挖 12_01 讲画布引擎怎么调度。本篇回答"**几个核心组件内部到底怎么实现**"——LLM 怎么流式输出、检索怎么把引用挂回画布、答案怎么拼装。
> 核心认知：**组件基类双结构（参数对象 + 运行时对象），`invoke` 封装异常/计时/取消；引用不直接传对象，通过 canvas 中转（add_reference → get_reference）**。
> ⚠️ 本仓库是裁剪版：Retrieval 是 ToolBase 工具（agent/tools/retrieval.py），"Answer" 由 Message 组件承担，"Generate" 拆分在 LLM 组件和 Agent 组件里。

- 源码位置：`github/project/ragflow/agent/component/{base,llm,message,begin,agent_with_tools}.py` + `agent/tools/{base,retrieval}.py` + `agent/canvas.py`
- 上游：深挖 12_01 的 Canvas 引擎（`_run_batch` 调 `invoke_async`）
- 下游：前端（message_end 事件流带引用）

---

## 三问

- **Q1 解决什么问题**：把"调 LLM / 检索知识库 / 拼答案"做成画布可拖拽的组件，且支持流式输出、引用回传、异常兜底。
- **Q2 数据流哪一环**：在线链路问答阶段 + agent 画布应用——LLM 组件是核心，Retrieval 是数据源，Message 是出口。
- **Q3 删掉会怎样**：画布应用没法调模型、没法检索、没法出答案——agent 体系全废。

---

## 一、组件基类 `ComponentBase` —— 双结构 + 统一入口 ★（base.py:43-54, 380-504）

```python
# 参数对象：声明组件全部输入/输出容器 + 兜底策略
class ComponentParamBase(ABC):
    def __init__(self):
        self.inputs = {}          # 输入变量容器 {var: {"value":...}}
        self.outputs = {}         # 输出变量容器 {var: {"value":...}}
        self.max_retries = 0
        self.delay_after_error = 2.0
        self.exception_method = None
        self.exception_default_value = None
        self.exception_goto = None
    def check(self): raise NotImplementedError(...)
```

```python
# 同步调用入口（base.py:403-415）
def invoke(self, **kwargs) -> dict[str, Any]:
    self.set_output("_created_time", time.perf_counter())
    try:
        self._invoke(**kwargs)   # 子类实现真正逻辑
    except Exception as e:
        if self.get_exception_default_value():
            self.set_exception_default_value()
        else:
            self.set_output("_ERROR", str(e))     # ★ 异常进输出，不抛
        logging.exception(e)
    self.set_output("_elapsed_time", time.perf_counter() - self.output("_created_time"))
    return self.output()
```

```python
# 异步入口（base.py:417-443）——优先协程 _invoke_async，否则 _invoke 丢线程池
async def invoke_async(self, **kwargs) -> dict[str, Any]:
    self.set_output("_created_time", time.perf_counter())
    try:
        if self.check_if_canceled("Component processing"): return
        fn_async = getattr(self, "_invoke_async", None)
        if fn_async and asyncio.iscoroutinefunction(fn_async):
            await fn_async(**kwargs)
        elif asyncio.iscoroutinefunction(self._invoke):
            await self._invoke(**kwargs)
        else:
            await thread_pool_exec(self._invoke, **kwargs)
    except Exception as e: ...
    return self.output()
```

```python
# 输入引用解析（base.py:474-504）——{cpn@var} / {sys.x} 模板替换
def get_input(self, key=None):
    for var, o in self.get_input_elements().items():
        v = self.get_param(var)
        if isinstance(v, str) and self._canvas.is_reff(v):     # 形如 {cpn@var}
            resolved = self._canvas.get_variable_value(v)      # 从画布上下文取值
            self.set_input_value(var, resolved)
        elif isinstance(v, str) and self.variable_ref_patt_re.search(v):
            kv = {k: e.get("value","") for k, e in self.get_input_elements_from_text(v).items()}
            self.set_input_value(var, self.string_format(v, kv))  # 模板替换
        else:
            self.set_input_value(var, v)
    return res
```

**作用（关键）**：组件 = "参数对象 + 运行时对象"；`invoke`/`invoke_async` 统一封装**异常/计时/取消**；`get_input` 用正则 `{cpn_id@var}/{sys.x}` 做引用解析后喂给 `_invoke`；输出统一放 `_param.outputs`。

## 二、`LLM` 组件 —— 模型绑定 + 流式输出 ★（llm.py:93-102, 390-495）

**构造时绑定模型**：

```python
def __init__(self, canvas, component_id, param):
    super().__init__(canvas, component_id, param)
    model_types = resolve_model_type(self._canvas.get_tenant_id(), self._param.llm_id)
    model_type = "chat" if "chat" in model_types else model_types[0]
    chat_model_config = resolve_model_config(self._canvas.get_tenant_id(), model_type, self._param.llm_id)
    self.chat_mdl = LLMBundle(self._canvas.get_tenant_id(), chat_model_config,
                              max_retries=self._param.max_retries,
                              retry_interval=self._param.delay_after_error)
```

**调 chat + 引用回传**（llm.py:299-366）：

```python
msg, sys_prompt = self._sys_prompt_and_msg(
    self._canvas.get_history(self._param.message_history_window_size)[:-1], args)
if self._param.cite and self._canvas.get_reference()["chunks"]:   # ★ 引用从 canvas 取
    sys_prompt += citation_prompt(user_defined_prompt)             # 让 LLM 输出 [ID:x]
return sys_prompt, msg, user_defined_prompt
```

**流式输出**（llm.py:390-422）：

```python
async def _stream_output_async(self, prompt, msg):
    stream = self.chat_mdl.async_chat_streamly_delta(msg_fit[0]["content"], msg_fit[1:],
                                                     self._param.gen_conf(), **stream_kwargs)
    async for _, ans, _ in _stream_with_think_delta(stream, min_tokens=0):
        if self.check_if_canceled("LLM streaming"): return
        answer += ans
        yield ans                      # ★ 逐段产出
    self.set_output("content", answer)
```

**流式→下游 Message 的关键**（llm.py:471-495）：

```python
downstreams = self._canvas.get_component(self._id)["downstream"]
ex = self.exception_handler()
if any([self._canvas.get_component_obj(cid).component_name.lower() == "message"
        for cid in downstreams]) and not (ex and ex["goto"]):
    self.set_output("content", partial(self._stream_output_async, prompt, deepcopy(msg)))
    return          # ★ 不阻塞：挂 partial 生成器，Message 惰性消费
# 非流式路径
for _ in range(self._param.max_retries + 1):
    ans = await self._generate_async(msg_fit, **extra_chat_kwargs)
    if ans.find("**ERROR**") >= 0: error = ans; continue
    self.set_output("content", ans); break
```

**作用（关键）**：LLM 组件构造期用 `LLMBundle` 绑定模型，`_invoke_async` 组装带历史/引用/图像的 prompt，流式走 `async_chat_streamly_delta`；**下游是 Message 时 output 直接挂 `partial` 生成器**——实现"边生成边输出"而不阻塞整个图。

## 三、`Retrieval` 组件 —— 检索 + 引用注册（agent/tools/retrieval.py）

**参数声明**（retrieval.py:58-71）：

```python
self.similarity_threshold = 0.2
self.keywords_similarity_weight = 0.5
self.top_n = 8        # 返回给下游的 top N
self.top_k = 1024     # 召回候选池大小
self.dataset_ids = []
self.rerank_id = ""
self.empty_response = ""
```

**调检索服务**（retrieval.py:196-210）：

```python
kbinfos = await settings.retriever.retrieval(
    query, embd_mdl, [kb.tenant_id for kb in kbs], filtered_kb_ids,
    1, self._param.top_n, self._param.similarity_threshold,
    1 - self._param.keywords_similarity_weight, top=self._param.top_k,
    doc_ids=doc_ids, aggs=True, rerank_mdl=rerank_mdl, rank_feature=label_question(query, kbs))
```

**结果组装给下游**（retrieval.py:245-265）：

```python
for ck in kbinfos["chunks"]:
    if "vector" in ck: del ck["vector"]                    # 去重删向量字段
    if "content_ltks" in ck: del ck["content_ltks"]
if not kbinfos["chunks"]:
    self.set_output("formalized_content", self._param.empty_response); return
json_output = kbinfos["chunks"].copy()
self._canvas.add_reference(kbinfos["chunks"], kbinfos["doc_aggs"])   # ★ 引用注册到画布
form_cnt = "\n".join(kb_prompt(kbinfos, 200000, True))
self.set_output("formalized_content", form_cnt)    # 给 LLM 用的上下文文本
self.set_output("json", json_output)               # 给下游结构化数据
```

**作用（关键）**：Retrieval 用 `settings.retriever.retrieval()` 检索，结果 `add_reference` 注册进画布、渲染成 `formalized_content`（含 ID 编号）文本输出，供 LLM 引用生成 `[ID:x]`。

## 四、`Message`（Answer）—— 拼装答案 + 消费流式生成器 ★（message.py:188-288）

**非流式**（Jinja2 沙箱渲染模板）：

```python
def _invoke(self, **kwargs):
    rand_cnt = random.choice(self._param.content)
    if self._param.stream and not self._is_jinjia2(rand_cnt):
        self.set_output("content", partial(self._stream, rand_cnt))  # 流式挂生成器
        return
    rand_cnt, kwargs = self.get_kwargs(rand_cnt, kwargs, downloads=downloads)
    template = _jinja2_sandbox.from_string(rand_cnt)
    content = template.render(kwargs)          # Jinja2 渲染
    self.set_output("content", content)
    self._convert_content(content)             # 支持导出 md/html/pdf/docx/xlsx
```

**流式拼装**（message.py:188-248）——把模板按 `{...}` 引用切片，逐个解析变量，**若是 partial 生成器就异步迭代拼接**：

```python
async def _stream(self, rand_cnt: str):
    for r in re.finditer(self.variable_ref_patt, rand_cnt, flags=re.DOTALL):
        all_content += rand_cnt[s:r.start()]; yield rand_cnt[s:r.start()]
        s = r.end(); exp = r.group(1)
        v = self._canvas.get_variable_value(exp)          # 取 {cpn@var} 的值
        if isinstance(v, partial):                        # ★ LLM 给的流式生成器
            iter_obj = v()
            if inspect.isasyncgen(iter_obj):
                async for t in iter_obj: all_content += t; yield t
            else:
                for t in iter_obj: all_content += t; yield t
            self.set_input_value(exp, cnt); continue
        yield v; all_content += v
    self.set_output("content", all_content)
```

**引用最终回传**（canvas.py:1067-1077）：

```python
def _build_message_end(self, cpn_obj) -> dict:
    message_end = {}
    ...
    if self._has_reference():
        message_end["reference"] = self.get_reference()   # {"chunks": {...}, "doc_aggs": {...}}
    return message_end
```

**作用（关键）**：Message（Answer）负责最终拼装——普通模板走 Jinja2 渲染，流式场景**把模板切块、逐个解析 `{cpn@var}` 并消费 LLM 的 `partial` 生成器边收边发**；答案里的 `[ID:x]` 引用由 LLM 生成、结构化引用由 canvas `_build_message_end` 附带回传。

## 五、组件参数声明 + 自动注册（base.py:202-353 + component/__init__.py:26-60）

```python
# 工具组件：ToolMeta 字典声明 parameters（既是 function-call schema，也驱动画布表单）
def get_meta(self):
    params = {k: {"type": p["type"], "description": p["description"]} for k, p in self.meta["parameters"].items()}
    return {"type": "function", "function": {
        "name": function_name, "description": desc,
        "parameters": {"type": "object", "properties": params,
                       "required": [k for k,p in self.meta["parameters"].items() if p["required"]]}}}

# 校验：check() + ComponentParamBase.check_* 静态方法
def check(self):                       # duckduckgo.py:54-56
    self.check_positive_integer(self.top_n, "Top N")
    self.check_valid_value(self.channel, "Web Search or News", ["text", "news"])

# 工厂：component_class(name) 从三个包反查类
def component_class(class_name):
    for module_name in ["agent.component", "agent.tools", "rag.flow"]:
        try:
            return getattr(importlib.import_module(module_name), class_name)
        except Exception: pass
    assert False, f"Can't import {class_name}"
```

**作用**：参数声明 = `*Param` 类里类属性带默认值（工具类走 `ToolMeta.parameters`），`get_input_form()` 输出输入字段 schema，`check()` 运行时校验，`__init__.py` 自动注册 + `component_class()` 工厂供 DSL/前端反查。

## 六、运行时上下文 —— 引用跨组件传递 ★（canvas.py:245-318, 1041-1059）

```python
# 全局上下文 globals
self.globals = {
    "sys.query": "", "sys.user_id": tenant_id, "sys.conversation_turns": 0,
    "sys.files": [], "sys.history": [], "sys.date": ...}

# 变量读写：cpn@var → 定位组件取 output(var)；无 @ → 读 globals
def get_variable_value(self, exp):
    exp = exp.strip("{").strip("}").strip(" ")
    if exp.find("@") < 0: return self.globals[exp]
    cpn_id, var_nm = exp.split("@", 1)
    cpn = self.get_component(cpn_id)
    root_key = var_nm.split(".", 1)[0]
    root_val = cpn["obj"].output(root_key)
    rest = var_nm.split(".", 1)[1] if len(var_nm.split(".", 1)) > 1 else ""
    if not rest: return root_val
    return self.get_variable_param_value(root_val, rest)

# 引用注册与读取
def add_reference(self, chunks, doc_infos):
    if not self.retrieval: self.retrieval = [{"chunks": {}, "doc_aggs": {}}]
    r = self.retrieval[-1]
    for ck in chunks_format({"chunks": chunks}):
        cid = hash_str2int(ck["id"], 500)
        if cid not in r: r["chunks"][cid] = ck
    for doc in doc_infos:
        if doc["doc_name"] not in r: r["doc_aggs"][doc["doc_name"]] = doc

def get_reference(self):
    if not self.retrieval: return {"chunks": {}, "doc_aggs": {}}
    return self.retrieval[-1]
```

**作用（关键）**：组件间通过 canvas 共享上下文——`globals` 存 `sys.*`，`get/set_variable_value` 按 `cpn_id@var` 读写任意组件输出，检索/搜索调用 `add_reference` 注册 chunk 引用、LLM/Agent 用 `get_reference()` 消费并生成 `[ID:x]` 引用。

---

## 七、数据流示意（引用链路）

```
Retrieval.add_reference(chunks, doc_aggs) → canvas.retrieval[-1]
   │
   ▼
LLM._prepare_prompt_variables → get_reference() → citation_prompt → 输出 [ID:x]
   │   （下游是 message → 挂 partial 流式生成器）
   ▼
Message._stream 消费 LLM 的 partial 生成器拼装答案，逐 token yield
   │
   ▼
canvas._build_message_end 附 reference {"chunks":{}, "doc_aggs":{}} → message_end 事件 → 前端
```

---

## 八、对照 ai_assistant

| RAGFlow | 你的 ai_assistant | 差距 |
|---------|------------------|------|
| 参数对象 + 运行时对象双结构 | 一个类塞所有 | ⚠️ 参数校验和逻辑耦合 |
| `invoke` 封装异常/计时/取消 | 裸调 LLM | ⚠️ 失败无兜底 |
| 流式：LLM 挂 partial + Message 惰性消费 | 等完整响应 | ⚠️ 首字延迟高 |
| 引用经 canvas 中转（add/get_reference） | 无引用体系 | ❌ 答案无出处 |
| `[ID:x]` citation_prompt 引用格式 | 无 | ⚠️ RAG 无引用不可信 |
| Jinja2 沙箱模板渲染 | f-string 手拼 | ⚠️ 模板不可配置 |
| ToolMeta 声明 parameters 驱动表单 | 无 | 概念参考 |

**落地优先级**：
- **P0**：**引用体系**——检索结果记录来源，LLM prompt 里要求 `[ID:x]`，答案附引用。这是 RAG 和"套壳对话"的分界线。
- **P1**：**流式输出**——LLM 响应按 token 吐给前端，用生成器/SSE。
- **P2**：异常兜底（goto/default）+ 组件参数校验。

---

## 九、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 参数对象 | `ComponentParamBase`（base:43） | inputs/outputs + 兜底策略 |
| 同步入口 | `invoke`（403） | 异常/计时封装 |
| 异步入口 | `invoke_async`（417） | 协程/线程池 + 取消 |
| 引用解析 | `get_input`（474） | `{cpn@var}` 模板替换 |
| LLM 绑定 | `LLM.__init__`（llm:93） | LLMBundle + max_retries |
| 流式输出 | `_stream_output_async`（llm:390） | 逐段 yield + partial 挂载 |
| 检索 | `Retrieval._invoke_async`（retrieval:196） | retrieval + add_reference |
| 答案拼装 | `Message._stream`（message:188） | 切块解析 + 消费生成器 |
| 引用回传 | `_build_message_end`（canvas:1067） | reference 附到 message_end |

**一句话心法**：**组件式 AI 应用 = 基类封装横切关注点（异常/计时/取消/引用解析）+ 组件只写业务逻辑**。流式的精髓是"LLM 输出挂成 partial 生成器，Message 惰性消费"，引用的精髓是"检索注册、LLM 消费、答案回传"都在画布上下文中流转，**组件间永远不直接传对象**。
