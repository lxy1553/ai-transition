# 深挖：TaskExecutor 重构与可观测（rag/svr/task_executor_refactor/）

> 深挖 01 讲任务怎么被消费。本篇回答"**新版 TaskExecutor 怎么把旧大文件拆成可测试的服务，怎么证明重构前后行为等价**"。
> 核心认知：**旧版 `task_executor.py`（1968 行）一个函数打到底；新版拆成 20 个模块三层结构（基础设施→服务→业务），核心是依赖注入（TaskContext）+ 可观测（RecordingContext）**。
> `TE_RUN_MODE` 三态开关让新旧两条路径能并行跑、逐键对比——这是"大重构不改行为"的完整样板。

- 源码位置：`github/project/ragflow/rag/svr/task_executor.py` + `task_executor_refactor/`（task_handler/task_manager/task_context/chunk_service/embedding_service/dataflow_service/recording_context/comparator/...）
- 上游：深挖 01 的 Redis 消费循环（collect → handle_task）
- 下游：进度回调 `set_progress` → `TaskService.update_progress`，写 ES

---

## 三问

- **Q1 解决什么问题**：旧版一个 1968 行的文件承担 7+ 职责，不可单测、不可插桩、重构不敢动。新版要"拆开 + 可观测 + 证明等价"。
- **Q2 数据流哪一环**：离线链路全部——任务消费→路由→分块→向量化→索引→后处理，贯穿深挖 01/03/04/05。
- **Q3 删掉会怎样**：退化成不可维护的大文件——任何改动都要人肉回归，重构停止。

---

## 一、拆分映射 —— 旧函数 → 新模块

| 旧版函数（task_executor.py） | 新版模块 | 职责 |
|---|---|---|
| `collect()`/`handle_task()`/`do_handle_task()` | `task_manager.py` + `task_handler.py` | 任务消费与路由 |
| 参数散落 task dict | `task_context.py` | TaskContext（属性访问 + 限流器 + 回调） |
| `build_chunks()` 内联 | `chunk_service.py` + `chunk_builder.py` + `chunk_post_processor.py` | 分块/后处理 |
| `embedding()` | `embedding_service.py` + `embedding_utils.py` | 向量化 |
| `insert_chunks()` | `chunk_service.py` | 索引写入 |
| `run_dataflow()` | `dataflow_service.py` | 数据流管道 |
| `run_raptor_for_kb()` | `raptor_service.py` + `raptor_utils.py` | RAPTOR |
| 新增 | `recording_context.py` / `write_operation_interceptor.py` / `comparator.py` / `report_generator.py` | 可观测/对比 |

## 二、TaskManager —— 依赖注入 ★（task_manager.py:43-106）

```python
class TaskManager:
    @classmethod
    async def run_refactored_task(cls, task, chat_limiter, minio_limiter, chunk_limiter,
                                  embed_limiter, kg_limiter, set_progress, has_canceled,
                                  billing_hook=None) -> None:
        with recording_context_manager(_NULL_RECORDING_CONTEXT):   # 生产用 Null，零内存开销
            task_context = TaskContext(
                task=task,
                limiters=TaskLimiters(chat=chat_limiter, minio=minio_limiter,
                                      chunk=chunk_limiter, embed=embed_limiter, kg=kg_limiter),
                callbacks=TaskCallbacks(progress=set_progress, has_canceled=has_canceled),
                recording_context=_NULL_RECORDING_CONTEXT,
            )
            handler = TaskHandler(ctx=task_context, billing_hook=billing_hook)
            await handler.handle_task()
```

**作用（关键）**：所有执行资源（5 个信号量限流器 + 进度/取消回调）**依赖注入**进 `TaskContext`。对比旧版直接引用全局 `chat_limiter`/`set_progress`——**"全局状态 → 依赖注入"是核心改进**，服务层不再碰全局，可单测。

## 三、新旧切换开关 `TE_RUN_MODE`（task_executor.py:1757-1775）

```python
run_mode = os.environ.get("TE_RUN_MODE", "0")
if run_mode == "1":  # dry run 对比模式
    set_recording_context(RecordingContext())
    await do_handle_task(task)                                    # 先跑旧版，记录结果
    await TaskManager.dry_run_task(task, get_recording_context(), ...)  # 再跑新版，比较
elif run_mode == "0":  # 新版 refactor（默认）
    set_recording_context(NullRecordingContext())
    await TaskManager.run_refactored_task(...)
else:                 # 旧版
    await do_handle_task(task)
```

**作用**：三态——`"1"` dry-run 对比（旧版跑一遍记录 + 新版跑一遍比较），`"0"` 新版（默认），其他 旧版。**切换由环境变量控制，不动代码**。

新版路由（task_handler.py:207-312）：`_bind_embedding_model()` + `_init_kb()` 后按 `task_type` 分派——`memory` / `dataflow` / `raptor` / `graphrag` / `mindmap` / `wiki` / `skill` / `structure_merge` / 标准分块。

标准分块管线 `_run_standard_chunking_impl`（task_handler.py:568-698）五阶段：

```python
chunks = await chunk_service.build_chunks(binary, on_chunking_start)     # ①解析+分块+后处理
token_count, vector_size = await embedding_service.embed_chunks(chunks, ...)  # ②向量化
toc_thread = asyncio.create_task(..._build_toc...)                       # ③TOC 后台线程
insert_result = await chunk_service.insert_chunks(...)                   # ④索引写入（含母块）
await post_processor.process_table_parser_metadata(task_doc_id, chunks)   # ⑤表元数据后处理
DocumentService.increment_chunk_num(task_doc_id, task_dataset_id, ...)    # ⑥计数
ctx.progress_cb(prog=1.0, msg="Task done ({:.2f}s)".format(task_time_cost))
```

**作用**：阶段边界不变（分块→向量化→索引→后处理），但每段可独立测试、可插桩记录。

## 四、母块 `_create_mother_chunks` —— 抽成纯函数 ★（chunk_service.py:272-306）

```python
@classmethod
def _create_mother_chunks(cls, chunks: List[Dict]) -> List[Dict]:
    mothers = []; mother_ids = set()
    for ck in chunks:
        mom = ck.get("mom") or ck.get("mom_with_weight") or ""
        if not mom: continue
        mom_id = xxhash.xxh64(mom.encode("utf-8")).hexdigest()   # ★ 内容哈希作 id（幂等）
        ck["mom_id"] = mom_id
        if mom_id in mother_ids: continue                         # 同摘要去重
        mother_ids.add(mom_id)
        mom_ck = copy.deepcopy(ck)
        mom_ck["id"] = mom_id
        mom_ck["content_with_weight"] = mom
        mom_ck["available_int"] = 0                              # ★ 标记不可检索
        allowed_fields = ["id","content_with_weight","doc_id","docnm_kwd","kb_id",
                          "available_int","position_int","create_timestamp_flt","page_num_int","top_int"]
        for fld in list(mom_ck.keys()):
            if fld not in allowed_fields: del mom_ck[fld]         # 白名单瘦身
        mothers.append(mom_ck)
    return mothers
```

**作用**：母块 = 摘要字段（`mom`/`mom_with_weight`）去重后的独立 summary 块。与旧版内联段逻辑一致（同样的 `xxhash.xxh64`、`available_int=0`、白名单），**差异在组织方式**——旧版构建和写库混在一个函数里不可单测，新版拆成纯函数 `_create_mother_chunks` + `_insert_mother_chunks` + `_insert_main_chunks`。

## 五、可观测 `RecordingContext` ★（recording_context.py:135-246）

```python
def record(self, key, value):          # 覆盖式记录中间结果
    self._data[key] = value

def save_func_return_value(self, func_name, return_value):   # 追加式记录函数返回值（写操作）
    if func_name not in self._data: self._data[func_name] = []
    self._data[func_name].append(return_value)

@contextmanager
def measure(self, name):               # 手动计时上下文
    start = time.perf_counter()
    try: yield
    finally:
        self.records.append((name, time.perf_counter() - start))
```

```python
# common/decorator.py:35-90 —— timing 装饰器真正计时
async def async_wrapper(*args, **kwargs):
    start = time.perf_counter()
    try:
        result = await func(*args, **kwargs)
        return result
    finally:
        elapsed = time.perf_counter() - start
        log.debug(f"[TIMING] {func_name} took {elapsed:.3f}s")
        if context is not None:
            context.record(f"{func_name}_time", elapsed)   # 键名如 build_chunks_time
```

**作用（关键）**：
- 两个容器：数据 `_data` + 耗时 `records`。
- `timed_with_recording` 装饰器（recording_context.py:365-419）委托 `common/decorator.timing`，旧版 `build_chunks`/`embedding`/`insert_chunks` 上的 `@timed_with_recording` 在新旧两路径下都生效。
- **隔离**：用 `contextvars.ContextVar` 隔离协程/线程（recording_context.py:314），嵌套协程不串数据。
- **零开销**：`NullRecordingContext`（261-306，`__slots__=()`）在生产注入，`record` 全部 no-op——**为了可观测不牺牲生产性能**。
- **消费端**：`Comparator` 在 dry-run 模式用 `WriteOperationInterceptor` 重放生产记录的函数返回值，`ContextComparator.compare()` 逐键比较两份 RecordingContext——**重构前后行为等价的闭环**。

## 六、进度/状态/心跳（task_service.py:377-430）

```python
if info["progress_msg"]:
    progress_msg = trim_header_by_lines((task.progress_msg or "") + "\n" + info["progress_msg"], 3000)
    cls.model.update(progress_msg=progress_msg).where(cls.model.id == id).execute()
if "progress" in info:
    prog = info["progress"]
    cls.model.update(progress=prog).where((cls.model.id == id) &
        ((prog >= 1) | ((cls.model.progress != -1) & ((prog == -1) | (prog > cls.model.progress))))).execute()
...
if info.get("progress") == -1:
    DocumentService.model.update({"progress": -1, "run": TaskStatus.FAIL.value, ...})
```

**作用**：progress_msg 追加并裁剪到 3000 行；progress 只在「≥1 或当前≠-1 且新值更大/为-1」时更新（允许从 -1 恢复、不允许倒退）；`progress==-1` 把 Document 置 `run=FAIL`。心跳 `report_status()`（task_executor.py:1824-1902）每 30s 把 worker 状态写 Redis ZSET，超 120s 无心跳清出 `TASKEXE`。

## 七、幂等/重试/恢复 ★（task_service.py:221-237 + chunk_service.py:349-380）

```python
# 重试：每次被 collect 拉到 retry_count+1，≥3 次废弃
if doc["retry_count"] >= 3:
    msg = "\nERROR: Task is abandoned after 3 times attempts."
    prog = -1
...
if docs[0]["retry_count"] >= 3:
    abort_doc_chunking_counter(docs[0]["doc_id"])
    DocumentService.update_by_id(docs[0]["doc_id"], {"progress": -1, "run": TaskStatus.FAIL.value})
    return None
```

```python
# Checkpoint：每 256 个 chunk 或最后一批才写一次 chunk_ids
checkpoint_batches = max(1, 256 // doc_bulk_size)
for b in range(0, len(chunks), doc_bulk_size):
    ...
    is_last_batch = batch_end == len(chunks)
    if is_last_batch or batch_end - last_checkpoint >= checkpoint_batches * doc_bulk_size:
        chunk_ids = [chunk["id"] for chunk in chunks[:batch_end]]
        if not await self._update_task_chunk_ids(task_id, chunk_ids):   # 写 checkpoint
            await self._rollback_insertion(...)                          # 任务已删则回滚
            return False
        last_checkpoint = batch_end
```

**作用（关键）**：
- **重试限次**：≥3 次废弃置 FAIL。
- **崩溃恢复**：`get_unacked_iterator` 先消费上次未 ack 的消息，任务结束后 `redis_msg.ack()`（task_executor.py:1810）——进程崩溃 → 消息不 ack → 下次重跑。
- **Checkpoint**：旧版每批都写 `update_chunk_ids`，新版**每 256 个 chunk 或最后一批才写一次**——减少 MySQL 事务数但保证可断点续传。
- **回滚**：`_rollback_insertion` 删 docStore 数据 + 并发删 MinIO 图片；RAPTOR 取消时 `_rollback_raptor_chunks` 只回滚带 `raptor_kwd` 的摘要块，避免下次误判 checkpoint 已完成。

---

## 八、数据流转示意

```
任务队列(Redis Stream, 消费组 SVR_CONSUMER_GROUP)
   │  collect() 先取 unacked 再队尾   (task_executor.py:220)
   ▼
handle_task()  [TE_RUN_MODE 三态开关]  (task_executor.py:1745)
   ├─ "1" → do_handle_task(生产记录) + TaskManager.dry_run_task(对比)  ← 可观测闭环
   └─ "0" → TaskManager.run_refactored_task(task, limiters, cb)        (task_manager.py:58)
               │  TaskContext(依赖注入：5 限流器 + progress_cb + has_canceled + recording_context)
               ▼
            TaskHandler.handle()  ── task_type 路由  (task_handler.py:207)
               ├─ dataflow → DataflowService.run_dataflow
               ├─ raptor  → RaptorService.run_raptor_for_kb
               ├─ graphrag→ run_graphrag_for_kb
               └─ 标准分块 → _run_standard_chunking_impl (task_handler.py:568)
                    ① ChunkService.build_chunks       (chunk_limiter)
                    ② EmbeddingService.embed_chunks    (embed_limiter; 0.7~0.9 进度)
                    ③ TOC 异步线程
                    ④ ChunkService.insert_chunks → _create_mother_chunks(母块)
                                                  → _insert_mother/_insert_main（checkpoint 写 chunk_ids）
                    ⑤ PostProcessor.process_table_parser_metadata
                    ⑥ DocumentService.increment_chunk_num
                    ⑦ progress_cb(1.0, "Task done")
               ▼
            Redis 消息 ack (task_executor.py:1810)
```

---

## 九、对照 ai_assistant

| RAGFlow | 你的 ai_assistant | 差距 |
|---------|------------------|------|
| 依赖注入（TaskContext 装限流器+回调） | 全局变量直取 | ❌ 不可单测 |
| RecordingContext + Null 零开销 | 无 | ⚠️ 无法观测链路耗时 |
| dry-run 新旧对比闭环 | 无 | ⚠️ 重构不敢动 |
| checkpoint 分批续传 | 全量重跑 | ⚠️ 长任务崩了白干 |
| 重试限次（3 次废弃）+ unacked 恢复 | 无 | ⚠️ 崩溃丢任务 |
| 回滚（写了一半删干净） | 无 | ⚠️ 半成品污染知识库 |

**落地优先级**：
- **P0**：**依赖注入**——把限流器/回调装进一个 Context 对象传给各服务，别在服务里 `from settings import` 全局。这是你单测的第一步。
- **P1**：**checkpoint 续传**——写库按批次记录已写 chunk id，崩溃后跳过已写的。
- **P2**：RecordingContext 可观测——每阶段 `record(key, val)`，耗时/中间产物都能查。

---

## 十、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 依赖注入 | `TaskManager.run_refactored_task`（task_manager:43） | 限流器/回调装进 TaskContext |
| 新旧切换 | `TE_RUN_MODE`（task_executor:1757） | 三态：对比/新版/旧版 |
| 任务路由 | `TaskHandler.handle`（task_handler:207） | task_type 分派 |
| 母块 | `_create_mother_chunks`（chunk_service:272） | xxhash 幂等 id + available_int=0 |
| 可观测 | `RecordingContext`（recording_context:135） | 数据 + 耗时双容器 |
| 零开销 | `NullRecordingContext`（261） | 生产 no-op |
| 进度 | `TaskService.update_progress`（task_service:377） | 只进不退 + 3000 行裁剪 |
| 恢复 | checkpoint（chunk_service:349） | 每 256 批写一次 chunk_ids |
| 回滚 | `_rollback_insertion`（chunk_service:431） | 删 ES + 并发删 MinIO |

**一句话心法**：**大重构的命根子是"可对比"**——依赖注入让服务可单测，RecordingContext 让每步可观测，`TE_RUN_MODE="1"` 让新旧并行跑逐键比对。拆文件是表象，**"证明重构没改行为"才是目的**。
