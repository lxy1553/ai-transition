# 深挖：Go 并行 Ingestion（internal/ingestion/）

> 深挖 11_01 讲 Python TaskExecutor 重构。本篇回答"**RAGFlow 的 Go 并行重写长什么样**"——这是对 Python `rag/flow`（管线 DSL）+ `task_executor.py`（任务执行）的 Go 移植，引入了三层 goroutine 并发。
> 核心认知：**Go 版把 DSL 编译成 eino（CloudWeGo）DAG，一次 `Workflow.Invoke` 执行；并发是分层的（任务级 worker 池 / 组件级 extractor 池 / 页级并行）**；Python 版画布逐节点调度，Go 版编译成图一次性跑。
> ⚠️ 还没全部移植：只有 `["pdf","docx","txt"]` 跑真实解析器，其余家族走 raw-text 兜底；API/前端仍是 Python。

- 源码位置：`github/project/ragflow/internal/ingestion/`（pipeline/ component/ service/ task/ wire/ knowledge_compile/）+ `agent/canvas/`（compile/checkpoint_store）
- 上游：Python API publish `ingestion_task` 到 MQ（NATS），Go `Ingestor.consumeLoop` 消费
- 下游：写 ES 索引 + NATS `PublishCompleted` + 回写 document 表

---

## 三问

- **Q1 解决什么问题**：Python 版 TaskExecutor 慢（单线程页级串行、GIL）。Go 版用 goroutine 三层并行 + 编译成 eino DAG 提升吞吐。
- **Q2 数据流哪一环**：离线链路全链路并行版——MQ 消费 → DSL 编译 → 组件链 → 索引写入。
- **Q3 删掉会怎样**：回退纯 Python——能跑但吞吐受限，这是 RAGFlow 的性能演进方向。

---

## 一、整体架构 —— 与 Python `rag/flow` 的关系

**定位**：对 Python `rag/flow/`（管线 DSL 执行）+ `rag/svr/task_executor.py`（任务执行）的 **Go 并行重写**。Python 版 `Pipeline(Graph)` 是解释器风格（async + `self._canvas` 逐节点调度）；Go 版改为 **DSL → 编译为 eino DAG → 一次性 `Workflow.Invoke`**，并在组件级、任务级、数据集级三层引入 goroutine 并发。

**子目录职责**：

| 目录 | 职责 |
|---|---|
| `pipeline/` | DSL 翻译（`UnwrapCanvasDSL`/`DecodeFromDSL`）、校验、checkpoint/resume、内置模板注册表 |
| `component/` | 各阶段组件（`file.go`/`parser.go`/`tokenizer.go`/`extractor.go`）+ `chunker/` 4 个切块变体 + `schema/` 纯 wire 类型 + `globals/` 跨组件元数据 |
| `service/` | `Ingestor` 服务编排：MQ 消费、任务状态机、worker 池 |
| `task/` | `PipelineExecutor`：加载 DSL → 跑管线 → 归一化 chunks → 写索引 |
| `wire/` | 启动期空导入触发组件注册 |
| `knowledge_compile/` | 数据集级后处理（LLM 合并去重） |

**与 Python 的对应关系**在注释里写得很清楚（component/schema/parser.go:20-21 镜像 Python 的 Pydantic schema）。

## 二、Pipeline 执行 —— DSL → eino DAG ★（pipeline/pipeline.go:143-174）

```go
func NewPipelineFromDSL(dsl []byte, taskID string, opts ...PipelineOption) (*Pipeline, error) {
	canvasDSL, err := UnwrapCanvasDSL(dsl)            // 剥掉可选 {"dsl": {...}} 信封
	cnv, err := canvas.DecodeFromDSL(canvasDSL)       // DSL map -> Canvas 图对象
	if err := ValidatePipeline(cnv); err != nil { ... }
	rawBytes, err := json.Marshal(canvasDSL)          // key 排序 -> 稳定指纹
	p := &Pipeline{taskID: taskID, canvas: cnv, rawDSL: rawBytes}
	return p, nil
}
```

```go
// 编译成 eino 工作流（pipeline.go:435-457）
var compileOpts []canvas.CompileOption
if resumable {
	compileOpts = append(compileOpts,
		canvas.WithCheckPointStore(store),
		canvas.WithCheckPointID(p.taskID),
		canvas.WithInterruptAfterNonTerminalCpn(),
	)
}
if overrideParams != nil {
	compileOpts = append(compileOpts, canvas.WithOverrideParams(overrideParams))
}
compiled, err := canvas.Compile(compileCtx, p.canvas, compileOpts...)
```

```go
// 执行（pipeline.go:525-543）——整张 DAG 一次 Invoke 跑完
func (p *Pipeline) runPlain(runCtx context.Context, current map[string]any, compiled *canvas.CompiledCanvas, ...) (map[string]any, error) {
	out, err := compiled.Workflow.Invoke(runCtx, current)
	...
	return finalizeResult(current, out, runState), nil
}
```

**作用**：DSL → Canvas 对象 → 编译成 eino `compose.Runnable`。组件节点由全局注册表 factory 构建（runtime.ComponentFactory，runtime/component.go:51），节点 body 由 canvas 框架 `realComponentBody` 包裹（负责 `TrackProgress`/`TrackElapsed`）。内置 13 个管线模板 `//go:embed template/ingestion_pipeline_*.json`，`LoadBuiltinDSL` 按 `parser_id`（如 `"general"`，别名 `"naive"`）加载。

## 三、checkpoint/resume —— 断点怎么存、怎么恢复 ★（pipeline.go:552-616）

```go
func (p *Pipeline) runResumable(...) (map[string]any, error) {
	cpID := compiled.CheckPointID
	const maxResumeRounds = 1000
	for round := 0; round < maxResumeRounds; round++ {
		resumeID := ""
		if tracker != nil {
			if id, ok, _ := tracker.GetInterruptID(ctx, cpID); ok && id != "" { resumeID = id }
		}
		if resumeID == "" { resumeID = localInterruptID }
		if resumeID != "" {
			runCtx = compose.ResumeWithData(runCtx, resumeID, nil)   // ★ 从 checkpoint 恢复图输入
			invokeInput = nil
		}
		out, invokeErr := compiled.Workflow.Invoke(runCtx, invokeInput, compose.WithCheckPointID(cpID))
		if invokeErr == nil {
			return finalizeResult(current, out, runState), nil
		}
		if !canvas.IsInterruptError(invokeErr) { ... MarkFailed ... }
		id := canvas.FirstInterruptID(canvas.ExtractInterruptContexts(invokeErr))
		localInterruptID = id
		if tracker != nil { _ = tracker.AttachInterrupt(ctx, cpID, id) }   // 持久化崩溃恢复点
	}
	return current, fmt.Errorf("pipeline: run exceeded max resume rounds ...")
}
```

```go
// checkpoint 存 Redis（agent/canvas/checkpoint_store.go:34-36）
const checkpointKeyPrefix = "agent:cp:"
// 完整 key = "agent:cp:{id}"，TTL 24h
```

**DSL 变更防护**（pipeline.go:312-371 `guardDSLChange`）：用 `dslFileFingerprint`（sha256 全量 DSL）和 `overrideFingerprint`（运行期 override）对比 checkpoint 旁挂的 `cpID:dsl`/`cpID:ovf` 键，变了就 `store.Delete` 掉过期 checkpoint 并重跑。

**作用（关键）**：对应 Python 的"可重跑"——Go 用 **eino 的 interrupt-after-node + Redis checkpoint + RunTracker 持久化 interrupt id** 实现。每个非终态节点跑完 interrupt，下一轮自动 `ResumeWithData(nil)` 续跑；**DSL/解析配置改了就不续跑旧断点**。

## 四、组件接口 —— 极简签名 + globals 传元数据（runtime/component.go:40-51）

```go
type Component interface {
	Invoke(ctx context.Context, db *gorm.DB, inputs map[string]any) (map[string]any, error)
}
type ComponentFactory func(name string, params map[string]any) (Component, error)
```

```go
// 注册（component/tokenizer.go:873-884）
func init() {
	c := &TokenizerComponent{}
	runtime.MustRegister(ComponentNameTokenizer, runtime.CategoryIngestion,
		func(_ string, params map[string]any) (runtime.Component, error) {
			return NewTokenizerComponent(params)
		},
		runtime.Metadata{Version: "1.0.0", Inputs: c.Inputs(), Outputs: c.Outputs()})
}
```

**关键设计**：因为 Go 的 eino 只把组件**显式输出**传给下一节点（不像 Python `ProcessBase.invoke` 自动把每个 kwarg 并进输出），所以跨节点共享的运行级元数据放进 workflow 级 `CanvasState.Globals` 袋子（component/globals/globals.go:60-69，白名单 `name/doc_id/bucket/path/file/tenant_id/kb_id/lang`），组件用 `globals.GlobalOrInput(ctx, inputs, key, def)` 读——**恢复 Python 的全局可见语义**。

## 五、并发模型 —— 三层 goroutine 并行 ★（service/ingestion_service.go:443-471）

**(a) 任务级（Ingestor worker 池）**：

```go
func (e *Ingestor) startWorkerPool() {
	e.workerOnce.Do(func() {
		for i := int32(0); i < e.maxConcurrency; i++ {   // 默认 runtime.NumCPU()
			e.workerWg.Add(1)
			go e.workerLoop(i)
		}
	})
}
func (e *Ingestor) workerLoop(id int32) {
	for {
		select {
		case <-e.ctx.Done(): return
		case taskCtx := <-e.taskChan: e.executeTask(e.ctx, taskCtx)   // channel 背压
		}
	}
}
```

**(b) 组件级（Extractor LLM 并发限流）**（component/extractor.go:103-118）：

```go
var extractorPool = utility.NewWorkerPool[extractorJob, struct{}](
	extractorConcurrency(),               // 默认 10，读 MAX_CONCURRENT_CHATS
	extractorConcurrency()*4,
	func(_ context.Context, j extractorJob) (struct{}, error) { return struct{}{}, j() },
)
```

**(c) 解析器内页级并行**（internal/deepdoc/parser/pdf/parser_concurrency.go:96-107）：

```go
func parserPageWorkerPool() *utility.WorkerPool[pageTask, pageResult] {
	pagePoolOnce.Do(func() {
		workers := runtime.GOMAXPROCS(0) * 2
		pagePool = utility.NewWorkerPool(workers, workers*pageWorkerQueueFactor,
			func(ctx context.Context, task pageTask) (pageResult, error) {
				return task.parser.processPage(ctx, task.engine, task.pageNumber, ...)
			})
	})
	return pagePool
}
```

**(d) 数据集级（knowledge compile）**（knowledge_compile/pool.go:47-67）——池大小 = vCPU，`KC_COMPILE_CONCURRENCY` 可调。

**(e) 刻意"不 fan-out"的地方**：embedding 按**批量**而非并发（component/tokenizer.go:58-61 "embedding calls batched, not fanned"），一次 `Encode([]string)` 打满一批。

**作用（关键）**：所有池用统一 `utility.WorkerPool` 实现（internal/utility/workerpool.go:89 `NewWorkerPool(workers, queueSize, handler)`）。**任务级 worker 池 + 组件级 extractor 池 + 页级并行**三层叠加，embedding 故意用批量压满而不是并发打散。

## 六、和 Python 主路径的取舍 —— 哪些 Go 重写、哪些还依赖 Python ★

**Go 已重写（live）**：
- DSL 执行引擎：`Pipeline(Graph)` → Go `pipeline.Pipeline`（eino DAG + interrupt/resume）
- 任务执行器：`task/pipeline_executor.go`（`runPipelineWithDSL` pipeline_executor.go:627，含索引写入 `chunk_index_writer`、debug 模式、operation log）
- 五个组件：File / Parser / Tokenizer / Chunker（4 变体）/ Extractor
- 内嵌 DSL 模板 13 个 + checkpoint/resume（Redis + eino）
- 数据集级知识编译后处理（knowledge_compile/）

**仍依赖 Python 侧**：
- **API 服务器 / 前端 / 画布编辑**：仍是 Python Quart；Python 把 `ingestion_task` publish 到 MQ（NATS `tasks.RAGFLOW`），Go `Ingestor.consumeLoop`（ingestion_service.go:186）消费。取消信号复用 Python 写的 Redis flag `{task_id}-cancel`
- **未移植的解析家族降级**（component/parser.go:44-61）：Go 当前只对 `["pdf","docx","txt"]`（cmd/ragflow_server.go:567）跑真实解析器（cgo pdfium/pdf_oxide、office_oxide）；**其余家族走 raw-text 兜底**（把二进制按 UTF-8 切片成页）
- **tokenizer 底层**仍是同一套 C++ 绑定（`internal/tokenizer` 调 `rag_tokenizer` 的 cgo 绑定），不是纯 Go 重写
- **Python 的 `image2id` MinIO 上传**未移植，由单独 side-effect 组件负责

---

## 七、数据流示意

```
[DSL JSON] (template/ingestion_pipeline_general.json 或用户画布 canvas.DSL)
   │  UnwrapCanvasDSL + DecodeFromDSL + ValidatePipeline         pipeline.go:143-174
   ▼
[canvas.Canvas] (File -> Parser:HipSignsRhyme -> TokenChunker:... )
   │  canvas.Compile(WithCheckPointStore, WithCheckPointID=taskID,
   │                 WithInterruptAfterNonTerminalCpn, WithOverrideParams=ParserConfig)
   ▼
[eino compose.Runnable[map,map]]  (每节点 = runtime.Component{Invoke}; 注册于 wire.go 空导入)
   │  SeedIngestionGlobals → CanvasState.Globals{name,tenant_id,kb_id,lang,...}
   ▼
[Run]  resumable? ──否──▶ runPlain: Workflow.Invoke(inputs)            pipeline.go:481,525
   │        └────是──▶ guardDSLChange(sha256 指纹 vs cpID:dsl/cpID:ovf)
   │                     runResumable 循环: InterruptID → ResumeWithData → Invoke(cpID)
   │                     (eino checkpoint 字节 → Redis agent:cp:{taskID}, TTL 24h)
   ▼
[组件链] File → Parser(页级并行 GOMAXPROCS*2 池 + deepInf 限流8)
              → Chunker(4 变体) → Tokenizer(C++ tokenize + embedding 批量)
              → Extractor(extractorPool 有界池并发 LLM)
   ▼
[task.PipelineExecutor.processOutput]  pipeline_executor.go:221
   NormalizeChunks → ProcessChunksForPipeline → chunk_index_writer(engine.InsertChunks)
   → PublishCompleted(NATS) → knowledge_compile Consumer 数据集级合并去重
   ▼
[service.Ingestor]  completeTask/MarkCompleted → Ack/Nack MQ; docState 回写 document 表
```

---

## 八、对照 ai_assistant

| RAGFlow | 你的 ai_assistant | 差距 |
|---------|------------------|------|
| DSL → eino DAG 一次 Invoke | 代码顺序执行 | ⚠️ 无法编译成图执行 |
| 三层 goroutine 并发 | 串行处理 | ⚠️ 吞吐上不去 |
| worker 池 + channel 背压 | 无 | ⚠️ 高并发会雪崩 |
| eino interrupt + Redis checkpoint 续跑 | 全量重跑 | ⚠️ 长任务崩了白干 |
| DSL 指纹 guard 过期 checkpoint | 无 | ⚠️ 配置变更后误续跑 |
| embedding 批量压满 | 逐条调用 | ⚠️ 慢 |
| raw-text 兜底 | 无 | 概念参考 |

**落地优先级**：
- **P0**：**worker 池 + 批量**——任务用有界 worker 池 + channel 背压，LLM/embedding 调用批量压满。这是 Python 也能抄的。
- **P1**：**checkpoint 续跑**——DSL/配置指纹变了就作废旧断点（Go 版的 guardDSLChange 思路）。
- **P2**：编译成图执行（eino 等）——吞吐瓶颈明确时才值得。

---

## 九、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| DSL 解析 | `NewPipelineFromDSL`（pipeline:143） | DSL → Canvas + 指纹 |
| 编译 | `canvas.Compile`（pipeline:435） | Canvas → eino Runnable |
| 执行 | `runPlain`（525） | 一次 Invoke |
| 续跑 | `runResumable`（552） | interrupt + ResumeWithData |
| 存储 | `checkpoint_store.go:36` | Redis `agent:cp:{id}` |
| 组件 | `Component.Invoke`（runtime:44） | `inputs map → outputs map` |
| 并发 | 三层 worker 池 | 任务/组件/页级 |
| 路由 | `guardDSLChange`（312） | 指纹作废旧断点 |

**一句话心法**：**Go 重写的精髓不是"用 Go"，而是"编译成图 + 分层并发"**——DSL 编译成 eino DAG 一次跑完（对比 Python 逐节点调度），checkpoint 用 interrupt + Redis 续跑，并发三层（任务/组件/页）各配 worker 池。**迁移是渐进式的**：先 `["pdf","docx","txt"]` 三个格式，其余 raw-text 兜底，API/前端留 Python——能跑的通量优先于全量移植。
