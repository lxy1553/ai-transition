# 主干 ①：离线任务调度（TaskExecutor）

> 这是 RAG 离线链路的**入口**——文档上传后，谁把它拉起来解析？就是这里。
> 对照你上一个问题「RAG 离线链路第一步：数据读取」，TaskExecutor 就是那个"消费事件 → 拉数据"的调度器。

## 三问

- **Q1 解决什么问题**：把"用户上传文档"这个动作，变成"一条异步任务"，排队、限流、分发到正确的解析器执行。
- **Q2 数据流哪一环**：离线链路最前端——文档落 MinIO → 写 MySQL → 发 Redis 队列 → 这里消费。
- **Q3 删掉会怎样**：文档上传后没人处理，知识库永远是空的。

---

## 一、整体交互图

```
① 用户上传文档 (api/)
  │  存 MinIO → 写 MySQL(document/task 表) → 发 Redis 队列(stream)
  ▼
② collect()   —— 从 Redis 队列拉一条任务消息
  │  queue_consumer(svr_queue_name, consumer_group, consumer_name)
  │  先补 unacked(未确认) 消息 → 再消费新消息
  ▼
③ do_handle_task(task)  —— 任务分发器
  │  按 task_type 分派：dataflow / raptor / graphrag / memory / 普通解析
  ├─ dataflow → run_dataflow()   (新的编排式 pipeline)
  └─ 普通     → 绑定 embedding → init_kb → build_chunks → insert_chunks
  ▼
④ 产出：chunks 写入文档库(ES/Infinity) + 向量
```

---

## 二、每一步代码详解

### ① collect()（task_executor.py:220）—— 消费 Redis 队列

```python
async def collect():
    svr_queue_names = settings.get_svr_queue_names(TASK_TYPE)

    redis_msg = None
    # ★ 优先补消费"未确认"(unacked) 消息——上次处理中途挂掉的任务
    if not UNACKED_ITERATOR:
        UNACKED_ITERATOR = REDIS_CONN.get_unacked_iterator(
            svr_queue_names, SVR_CONSUMER_GROUP_NAME, CONSUMER_NAME)
    try:
        redis_msg = next(UNACKED_ITERATOR)
    except StopIteration:
        # ★ 没有 unacked 才消费新消息（Redis Stream 消费者组语义）
        for svr_queue_name in svr_queue_names:
            redis_msg = REDIS_CONN.queue_consumer(
                svr_queue_name, SVR_CONSUMER_GROUP_NAME, CONSUMER_NAME)
            if redis_msg:
                break

    msg = redis_msg.get_message()          # 从队列取消息体
    # 按 task_type 从 DB 查完整任务（队列里只有 id/type，明细在 MySQL）
    task = TaskService.get_task(msg["id"])

    if not task or has_canceled(task["id"]):   # 任务已取消 → ack 跳过
        redis_msg.ack()
        return None, None
    return redis_msg, task
```

**作用**：这是"**事件驱动 + 可恢复**"的数据读取。用 Redis Stream 的**消费者组**（consumer group）实现：
- 多个 worker 进程并发消费，同一消息只被一个 worker 处理。
- unacked 机制：worker 处理中途崩溃，消息不会被丢，下次重启会补消费 → **断点恢复**。

**坑（关键）**：
- 队列里只放 `{id, task_type}` 轻量消息，**明细在 MySQL**——避免队列消息过大。
- `ack` 必须显式调用，否则消息一直占着 unacked。

### ② do_handle_task()（task_executor.py:1408）—— 任务分发器

```python
async def do_handle_task(task):
    task_type = task.get("task_type", "")

    if task_type == "memory":
        await handle_save_to_memory_task(task); return      # 记忆类任务

    if task_type == "dataflow" and task.get("doc_id") == CANVAS_DEBUG_DOC_ID:
        await run_dataflow(task); return                    # Canvas 调试

    # —— 普通解析任务：先绑定 embedding 模型，确定向量维度 ——
    embd_model_config = resolve_model_config(task_tenant_id, LLMType.EMBEDDING, task_embedding_id)
    embedding_model = LLMBundle(task_tenant_id, embd_model_config, lang=task_language)
    vts, _ = embedding_model.encode(["ok"])      # ★ 编码一条，探测向量维度
    vector_size = len(vts[0])

    init_kb(task, vector_size)                   # 初始化知识库（建索引/映射）

    if task_type[:8] == "dataflow":
        await run_dataflow(task); return         # 走编排式 pipeline

    # raptor / graphrag / 普通 各自分支...
```

**作用**：
- **统一入口**：memory / dataflow / raptor / graphrag / 普通解析，全走这一个函数分派。
- **先探测向量维度**（`encode(["ok"])`）再初始化知识库——因为换 embedding 模型维度会变，索引的向量列是动态建的（`q_{dim}_vec`）。

### ③ FACTORY（task_executor.py:111）—— parser_type → 模板模块

```python
FACTORY = {
    "general": naive,                 # 通用文档
    ParserType.PAPER.value: paper,    # 论文
    ParserType.BOOK.value: book,      # 书籍
    ParserType.LAWS.value: laws,      # 法律（条款结构）
    ParserType.QA.value: qa,          # 问答对
    ParserType.TABLE.value: table,    # 表格
    ParserType.RESUME.value: resume,  # 简历
    ParserType.ONE.value: one,        # 整篇一个 chunk
    ParserType.AUDIO.value: audio,    # 音频（转写）
    ...
}
```

**作用**：这就是 README 说的「**模板化分块**」——不同文档类型用不同的解析+分块模块。用户在上传时选"论文/法律/简历"，后台就分派到不同的 `chunk()` 实现。

### ④ run_dataflow()（task_executor.py:766）—— 编排式 pipeline 的执行

```python
async def run_dataflow(task: dict):
    # ① 取 DSL：Canvas 拖拽生成的组件图（JSON）
    e, cvs = UserCanvasService.get_by_id(dataflow_id)
    dsl = cvs.dsl

    # ② 用 DSL 构建 Pipeline（组件图）
    pipeline = Pipeline(dsl, tenant_id=..., doc_id=..., task_id=..., flow_id=...)

    # ③ 跑 pipeline：Parser → Chunker → Tokenizer → Embedding 全串起来
    chunks = await pipeline.run(file=task["file"]) if task.get("file") else await pipeline.run()

    # ④ 从 pipeline 输出里取 chunks / embedding_token_consumption
    if "chunks" in chunks:
        chunks = copy.deepcopy(chunks["chunks"])
    ...
```

**作用**：这是 RAGFlow 新架构的核心——**把 ingestion 从"硬编码函数调用"升级成"DSL 驱动的组件图"**。DSL 由前端 Canvas 生成，用户可以拖拽"解析→分块→分词"的顺序。`pipeline.run()` 就是执行这个图（详见主干②）。

### ⑤ 限流器（task_executor.py:92）

```python
from rag.svr.task_executor_limiter import (
    task_limiter,     # 任务级并发限流
    chunk_limiter,    # 分块级并发限流
    embed_limiter,    # embedding 调用限流（防打爆 LLM API）
    minio_limiter,    # 对象存储 IO 限流
    kg_limiter,       # 知识图谱构建限流
)
```

**作用**：生产级的**背压控制**。多个 worker 同时跑，每个环节都有并发上限——尤其 `embed_limiter`，防止几十万 chunk 同时打 LLM embedding API（对应你上一个问题说的"限流按 token 不按请求数"）。

---

## 三、总结

| 环节 | 代码 | 对应你上一个问题的概念 |
|------|------|----------------------|
| collect() 消费队列 | `task_executor.py:220` | 事件驱动 + 变更捕获 |
| unacked 补消费 | `get_unacked_iterator` | 断点恢复 / 可重跑 |
| do_handle_task 分派 | `task_executor.py:1408` | 任务调度 |
| FACTORY 模板分派 | `task_executor.py:111` | 按文档类型分流 |
| 限流器 | `task_executor_limiter.py` | 背压 / 限流 |
| run_dataflow | `task_executor.py:766` | 编排式 pipeline |

**核心心法**：生产级离线链路的入口，不是"写个 for 循环读文件"，而是**「队列 + 消费者组 + 限流器 + 分派器」**——保证可恢复、可限流、可观测、可水平扩展。
