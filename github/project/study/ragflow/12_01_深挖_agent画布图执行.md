# 深挖：agent/canvas 图执行引擎（DSL → Canvas → 消息流执行）

> 深挖 02_01 说"Pipeline 继承 Graph"。本篇回答"**DSL 画布到底怎么被执行起来**"——`path` 这个动态指令序列怎么推进、组件怎么并行、条件/循环/异常怎么路由。
> 核心认知：**图是静态的（components + downstream/upstream），执行是动态的（维护 path 指令序列）**。组件间传值不走消息队列，而是"每个组件把输出写进自己的 `_param.outputs`，下游 `get_input()` 时用 `{cpn@var}` 现取"。

- 源码位置：`github/project/ragflow/agent/canvas.py`（Graph 344-482 / Canvas）+ `agent/component/base.py`
- 上游：DSL JSON（画布编辑器产出）
- 下游：各组件 `_invoke`（深挖 12_02）

---

## 三问

- **Q1 解决什么问题**：把用户拖的画布（节点 + 连线）变成能执行的计算图，支持并行分支、条件跳转、循环、异常降级、取消。
- **Q2 数据流哪一环**：支撑机制——任何画布型应用（含 RAG 流水线）的执行引擎。
- **Q3 删掉会怎样**：画布型编排全废——RAGFlow 的 agent 应用、rag/flow 流水线都依赖它。

---

## 一、Canvas 类结构 —— 持有哪些状态（canvas.py:90-100 / 346-361）

```python
# Graph.__init__ —— 图的骨架状态
def __init__(self, dsl: str, tenant_id=None, task_id=None, custom_header=None):
    self.path = []                    # ★ 执行路径：待执行/已执行组件 id 序列（活指针）
    self.components = {}              # 节点表: {id: {obj, downstream, upstream, parent_id}}
    self.error = ""                   # 本轮运行错误
    self.dsl = normalize_chunker_dsl(json.loads(dsl))   # 归一化后的 DSL json
    self._thread_pool = ThreadPoolExecutor(max_workers=5)  # 同步组件线程池
    self.load()

# Canvas.__init__ —— 运行时上下文状态
self.globals = {                      # sys.* 全局变量
    "sys.query": "", "sys.user_id": tenant_id,
    "sys.conversation_turns": 0, "sys.files": [], "sys.history": [], "sys.date": ...}
self.variables = {}                   # env.* 用户自定义变量
self._run_token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}

# Canvas.load —— 会话级状态
self.history = self.dsl["history"]    # 对话历史
self.retrieval = self.dsl["retrieval"]  # 检索引用 {chunks, doc_aggs}
self.memory = self.dsl.get("memory", [])
```

**作用**：`path` 是执行引擎的"活指针"，`components` 是解析后的节点表，`globals` 是跨组件传参的全局命名空间。

## 二、图的构建 —— DSL → 组件实例 + 边（canvas.py:102-124）

```python
def load(self):
    self.components = self.dsl["components"]
    for cpn in self.components.values():
        cpn["obj"]["params"]["custom_header"] = self.custom_header
    component_params = self.validate_component_parameters(self.dsl)   # 先校验参数
    for k, cpn in self.components.items():
        cpn["obj"] = component_class(cpn["obj"]["component_name"])(self, k, component_params[k])
    self.path = self.dsl["path"]

@staticmethod
def validate_component_parameters(dsl):
    component_params = {}
    for k, cpn in dsl["components"].items():
        param = component_class(cpn["obj"]["component_name"] + "Param")()  # 同名 Param 类
        param.update(cpn["obj"]["params"]); param.check()                 # 参数校验
        component_params[k] = param
    return component_params
```

**作用**：每个 DSL 节点 `{obj:{component_name, params}, downstream, upstream}` 变成一个 `ComponentBase` 实例挂在 `components[k]["obj"]`；节点连接信息保留在 `components[k]` 字典里供引擎查表（`get_downstream()` base.py:602-604）。**边不是独立对象，就是节点自带的 downstream/upstream 数组**。

## 三、图的执行 —— `run` 主循环 ★（canvas.py:443-663）

```python
# run 起点：路径压入 begin，检测取消
if not is_resume:
    self.path.append("begin")
    self.retrieval.append({"chunks": [], "doc_aggs": []})
if self.is_canceled():
    raise TaskCanceledException(f"Task {self.task_id} has been canceled before starting.")

# ★ 主循环：批处理 path 上的节点
while idx < len(self.path):
    to = len(self.path)
    for i in range(idx, to):
        yield decorate("node_started", {...self.path[i]...})   # 逐个发 started 事件
    await _run_batch(idx, to)     # ★ 并发执行 [idx,to) 这一段组件
    to = len(self.path)           # 执行后 path 可能变长（下游/分支/循环）
    ...
    idx = to                      # 推进游标到新 end
```

```python
# _run_batch —— 并行执行 + 线程池
async def _run_batch(f, t):
    max_concurrency = getattr(self._thread_pool, "_max_workers", 5)
    sem = asyncio.Semaphore(max_concurrency)
    async def _invoke_one(cpn_obj, sync_fn, call_kwargs, use_async):
        async with sem:
            if use_async:
                await cpn_obj.invoke_async(**call_kwargs); return
            bound_call = partial(sync_fn, **call_kwargs)
            call_ctx = contextvars.copy_context()          # 拷贝 LLM 请求上下文
            await loop.run_in_executor(self._thread_pool, partial(call_ctx.run, bound_call))
    while i < t:
        cpn = self.get_component_obj(self.path[i])
        call_kwargs = cpn.get_input()      # 解析输入（含上游引用）
        tasks.append(asyncio.create_task(_invoke_one(cpn, cpn.invoke, call_kwargs, use_async)))
    if tasks:
        await asyncio.gather(*tasks)       # ★ 并行分支在此汇聚
```

**作用（关键）**：`path` 是执行引擎的"指令流"；`_run_batch` 把一段路径上的组件并发调度，组件完成后引擎按 `downstream`/控制流输出扩展 `path` 形成下一段路径，直到 `idx` 追到 `path` 末尾、发出 `workflow_finished`（canvas.py:873-886）。**消息传递不是队列**——每个组件把输出写进自己的 `_param.outputs`，下游在 `get_input()` 时用 `{cpn_id@var}` 引用现取。

## 四、组件生命周期 —— invoke → 输出 → 下游取用（base.py:403-504）

```python
def invoke(self, **kwargs):
    self.set_output("_created_time", time.perf_counter())
    try:
        self._invoke(**kwargs)
    except Exception as e:
        if self.get_exception_default_value():
            self.set_exception_default_value()
        else:
            self.set_output("_ERROR", str(e))     # ★ 异常进 _ERROR 输出
        logging.exception(e)
    self.set_output("_elapsed_time", time.perf_counter() - self.output("_created_time"))
    return self.output()
```

```python
def get_input(self):
    for var, o in input_elements.items():
        v = self.get_param(var)
        if isinstance(v, str) and self._canvas.is_reff(v):      # {cpn_id@var} 引用
            resolved = self._canvas.get_variable_value(v)        # 现取上游输出
            self.set_input_value(var, resolved)
        elif isinstance(v, str) and self.variable_ref_patt_re.search(v):
            ... # 文本内嵌引用模板替换
        else:
            self.set_input_value(var, v)                          # 字面量
```

**输出写入侧**：`set_output`（base.py:454-457）把值存进 `_param.outputs[key]["value"]`；**读取侧**：`canvas.get_variable_value`（canvas.py:245-266）按 `cpn_id@var_nm` 找到组件实例再调 `cpn["obj"].output(root_key)`（base.py:449-452）。**"下游怎么接上游输入" = 上游 set_output 落库 → 下游 get_input 用引用取回**。

## 五、组件注册 —— component_class 反射（component/__init__.py）

```python
def _extract_classes_from_module(module):
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and obj.__module__ == module.__name__ and not name.startswith("_"):
            __all_classes[name] = obj; globals()[name] = obj

def component_class(class_name):
    for module_name in ["agent.component", "agent.tools", "rag.flow"]:
        try:
            return getattr(importlib.import_module(module_name), class_name)
        except Exception:
            pass
    assert False, f"Can't import {class_name}"
```

**作用**：字符串节点类型直接反射成 Python 类——**新增组件只要在对应目录建文件并定义同名类即自动注册**。

## 六、异常/重试 —— 组件出错怎么办 ★（base.py:49-53 + canvas.py:799-852）

```python
# 参数对象预置兜底策略
self.max_retries = 0
self.delay_after_error = 2.0
self.exception_method = None
self.exception_default_value = None
self.exception_goto = None

# 引擎消费错误
if cpn_obj.error():
    ex = cpn_obj.exception_handler()
    if ex and ex["goto"]:                     # 出错跳转到指定节点
        self.path.extend(ex["goto"]); other_branch = True
    elif ex and ex["default_value"]:          # 出错降级输出默认值
        yield decorate("message", {"content": ex["default_value"]})
    else:
        self.error = cpn_obj.error()          # 无兜底 → 记录错误
if self.error:
    logging.error(f"Runtime Error: {self.error}")
    break                                     # 终止主循环
```

**作用**：组件异常被 `invoke` 捕获写入 `_ERROR` 输出，引擎检测到后按参数策略三选一——**跳 `exception_goto` 节点 / 输出 `exception_default_value` / 置 `self.error` 终止**。取消机制独立：`is_canceled`（base.py:389-401）通过 Redis `{task_id}-cancel` 标志（canvas.py:332-341）在组件内部主动抛 `TaskCanceledException`。

## 七、特殊组件 —— begin / Message / iterate / 条件 ★

**begin**（begin.py:36-67）——入口，把用户输入灌进 outputs：

```python
def _invoke(self, **kwargs):
    merged_inputs = self._merge_runtime_inputs(kwargs.get("inputs", {}))
    for k, v in merged_inputs.items():
        v = self._resolve_input_value(v, layout_recognize)
        self.set_output(k, v)      # 用户输入 → 输出槽，下游 {begin@xxx} 可引用
```

**Message（answer）**（message.py:65-66）——终端输出，产出 `content` 可能是 `partial`（惰性生成器），canvas 后处理专门对它做流式事件切句、TTS 合成（canvas.py:669-789）：

```python
if cpn_obj.component_name.lower() == "message":
    if cpn_obj.get_param("auto_play"):
        tts_mdl = LLMBundle(self._tenant_id, ...)
    if isinstance(cpn_obj.output("content"), partial):
        stream = cpn_obj.output("content")()
        async for ev in _stream_events():
            yield ev                     # 逐 token 发 message 事件
    else:
        yield decorate("message", {"content": cpn_obj.output("content")})
```

**iterate（循环）**（iteration.py:48-61 + iterationitem.py:59-98）——容器 + 游标：

```python
# Iteration 容器：找到子节点 IterationItem
def get_start(self):
    for cid in self._canvas.components.keys():
        if self._canvas.get_component(cid)["obj"].component_name.lower() != "iterationitem": continue
        if self._canvas.get_component(cid)["parent_id"] == self._id: return cid

# IterationItem 每轮取一项、暴露别名
current_item = arr[self._idx]
self.set_output("item", current_item)
self.set_output("result", current_item)     # 兼容别名 @result
self.set_output("index", self._idx)
self._idx += 1
def end(self): return self._idx == -1       # 越界 = 遍历结束
```

引擎在 canvas.py:835-838 消费 `end()`：遍历结束把路径指向容器下游（跳出循环）；未结束靠 `downstream` 回到 iterationitem 继续下一轮。

**if-else（条件）**（categorize.py:143-150 + switch.py:86-92）——都把"下一步走哪个分支"写进 `_next` 输出：

```python
# Categorize：LLM 分类后把命中类别绑定的目标 id 放进 _next
max_category = max(category_counts.items(), key=lambda x: x[1])[0]
cpn_ids = self._param.category_description[max_category]["to"]
self.set_output("category_name", max_category)
self.set_output("_next", cpn_ids)

# Switch：规则命中，兜底走 end_cpn_ids（ELSE）
if res and all(res):
    self.set_output("_next", cond["to"]); return
self.set_output("_next", self._param.end_cpn_ids)

# 引擎：只扩展命中的分支
elif cpn_obj.component_name.lower() in ["categorize", "switch"]:
    _extend_path(cpn_obj.output("_next"))
```

---

## 八、数据流示意

```
DSL json {components:{begin:{obj,downstream,upstream},...}, path, globals}
   │  normalize_chunker_dsl() 归一化
   ▼
Graph.__init__ (canvas.py:90)
   │  Graph.load (canvas.py:102): 每个节点 component_class(name)(canvas,id,Param)
   ▼
Canvas 图: components = {begin:{obj:Begin, downstream:[retrieval_0], upstream:[]}, ...}
   │  Canvas.run (canvas.py:443) → _run_impl (canvas.py:484)
   ▼
path 初始化: [begin]
   │  while idx < len(path):
   ├─ _run_batch (canvas.py:560): 对 path 片段 [idx,to) 并发 invoke
   │     └─ 每个组件 get_input() 解析 {上游id@var} → 取上游 _param.outputs
   │     └─ 组件 _invoke() 写结果到自己的 set_output()
   ├─ 后处理 (canvas.py:665):
   │     出错?  →  goto/default_value/self.error(终止)
   │     条件?  →  _extend_path(_next)   (Categorize/Switch)
   │     循环?  →  iterationitem.end() 跳出 | iteration.get_start() 进入
   │     普通?  →  _extend_path(downstream)  ← 消息流在此延展
   ├─ idx = to  (canvas.py:853) 推进游标
   ▼
idx 追上 path 末尾 → yield workflow_finished (canvas.py:874-886)
```

---

## 九、对照 ai_assistant

| RAGFlow | 你的 ai_assistant | 差距 |
|---------|------------------|------|
| `path` 动态指令序列推进 | 硬编码 if/else 顺序 | ⚠️ 流程写死在代码里 |
| `_run_batch` 并发执行一段路径 | 串行执行 | ⚠️ 并行分支不可用 |
| 组件输出落 `_param.outputs` + 引用现取 | 变量直传 | 概念参考 |
| 异常三选一（goto/default/终止） | 抛异常全崩 | ⚠️ 单组件失败无法路由 |
| Categorize/Switch 条件分支 | 无 | ⚠️ 无法按内容分流 |
| Iterate/Loop 循环容器 | 无 | ⚠️ 批量处理要手写循环 |
| Redis `{task_id}-cancel` 取消 | 无 | ⚠️ 长任务无法中断 |

**落地优先级**：
- **P0**：**错误路由**——组件失败不抛死，输出 `_ERROR` 后按策略跳转/给默认值/终止。这是智能体稳定性的第一课。
- **P1**：**条件分支**——用 LLM 分类（Categorize）或规则（Switch）决定走哪条下游路径。
- **P2**：循环容器（Iterate）+ 并行分支。

---

## 十、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 图骨架 | `Graph.__init__`（90） | path/components/error |
| 运行时上下文 | `Canvas.__init__`（346） | globals/variables/token 计费 |
| DSL 实例化 | `load`（102） | 节点→组件实例 + 参数校验 |
| 主循环 | `run`/`_run_impl`（443/484） | 批处理 path + 扩展 |
| 并发调度 | `_run_batch`（560） | 线程池 + asyncio gather |
| 传值 | set_output / get_input | 输出表 + `{cpn@var}` 引用 |
| 异常路由 | canvas:799-852 | goto / default / 终止 |
| 取消 | Redis flag（332） | `{task_id}-cancel` |
| 条件/循环 | Categorize/Switch/Iterate | `_next` / `end()` 控制流 |

**一句话心法**：**画布执行 = "静态图 + 动态 path 指令序列"**。图只描述"有哪些节点、谁连谁"，执行器维护一条 `path` 指令流，一段一段并发跑、跑完按 downstream/分支/循环语义扩展 path——**组件间不传消息对象，只写自己的输出表、下游引用现取**。这个模式让"拖画布"变成"改一条指令流"，复杂控制流（分支/循环/异常/取消）全在这条流上表达。
