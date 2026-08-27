# 深挖：Go 原生 PDF 解析（internal/deepdoc/parser/）

> 深挖 13_01 讲 Go ingestion 整体。本篇回答"**Go 版的 PDF 解析器内部怎么实现、和 Python DeepDoc 差在哪**"。
> 核心认知：**Go 版用 Rust FFI（pdf_oxide）抽字符、pdfium（C++）渲染 OCR 底图、页级 worker 并行**；与 Python 版**刻意对齐**——注释直接点名 Python 文件/行号，还锁定了必须 100% 对齐的表格 PDF。
> ⚠️ 两处与任务描述的差异：`internal/cpp/` 不存在（真正的 C++ 绑定在 `internal/binding/cpp/`，且是 tokenizer/NER/stemmer 与 PDF 无关）；真正的分词在 C++ `internal/binding/cpp/tokenizer.cpp`，`chunk/` 包不做 token 计数（按 rune 窗口）。

- 源码位置：`github/project/ragflow/internal/deepdoc/parser/`（pdf/ docx/ + type/）+ `internal/parser/parser/`（parse_result/docx_parser/pdf_parser_common）+ `internal/parser/chunk/`
- 上游：深挖 13_01 的 Parser 组件 → 页级 worker 池
- 下游：typed `ParseResult` → chunk.Run（rune 窗口切块）→ 索引

---

## 三问

- **Q1 解决什么问题**：Python 版 PDF 解析单线程页级串行慢。Go 版用页级 worker 池并行 + Rust/C++ 原生库提速。
- **Q2 数据流哪一环**：离线链路解析阶段——Go 版 Parser 逐页抽字符/渲染/OCR/DLA，文档级合并成 Sections。
- **Q3 删掉会怎样**：Go ingestion 只有 DOCX 能用——PDF 回退 Python 或 raw-text 兜底，吞吐和精度都掉。

---

## 一、整体 —— 原生库 + CGO 接线

用到的原生库（go.mod）：`pdf_oxide`（Rust FFI，抽字符/渲染）、`office_oxide`（Rust FFI，读 docx）、libpdfium（C++ 静态库，渲染+书签）。**CGO 边界按 `//go:build cgo` 分叉**。

```go
// pdfoxide_bridge.go:19-25 —— 把 pdf_oxide 适配成统一 PDFEngine 接口
func NewEngine(pdfBytes []byte) (pdf.PDFEngine, error) {
	eng, err := pdfoxide.NewEngine(pdfBytes)
	if err != nil { return nil, err }
	return &PDFOxideEngine{Inner: eng}, nil
}

// parse_cgo.go:26-37 —— CGO 入口 Parse，把引擎所有权转交给结果（供后续按需裁剪图片）
func (p *Parser) Parse(ctx context.Context, data []byte, docAnalyzer pdf.DocAnalyzer) (*pdf.ParseResult, error) {
	engine, err := NewEngine(data)
	res, err := p.ParseRaw(ctx, engine, docAnalyzer)
	if err != nil { _ = engine.Close(); return nil, err }
	return res, nil
}
```

```go
// pdfium/pdfium.go:9-45 —— import "C" 直接接 pdfium C API
/*
#cgo LDFLAGS: -lm -lpthread -ldl
typedef struct FPDF_DOCUMENT__ { int unused; } *FPDF_DOCUMENT;
extern void          FPDF_InitLibrary(void);
extern FPDF_DOCUMENT FPDF_LoadMemDocument(...);
extern int           FPDF_RenderPageBitmap(...);
*/
import "C"
```

**作用**：`pdf_oxide`（Rust）负责所有文本/字符提取，接口统一后上层只面对 `PDFEngine`；pdfium 只做两件事——**高质量光栅化（供 OCR/DLA）和书签抽取**，文本仍走 pdf_oxide。非 CGO 构建由 `parse_nocgo.go:29-34` 直接返回 `"deepdoc/pdf: cgo required"`。

## 二、单页流水线 —— 抽字符 → 渲染 → OCR/DLA ★（parser.go:188-224）

```go
chars, extractErr := engine.ExtractChars(pg)          // 每字形细粒度字符
medianH := util.MedianCharHeight(chars)
pageImg, renderErr := p.renderPageToImage(ctx, engine, pg)   // 216 DPI
if pageImg != nil && renderErr == nil {
	ocrBoxes, updatedChars, ocrUsed = p.processPageBoxes(ctx, pageImg, chars, pg, ...)
	annotated, pageTables, dlaRegions = p.enrichOnePageWithDeepDoc(ctx, pageImg, ocrBoxes, ...)
}
```

**页级 OCR 策略选择**（parser.go:311-359）——干净内嵌字 → `ocrMergeChars`；扫描/乱码 → `ocrDetectAndRecognize`：

```go
hasCleanChars := len(chars) > 0 && !isScanNoise && !util.IsGarbledPage(chars)
if hasCleanChars {
	ocrBoxes = p.ocrMergeChars(ctx, pageImg, chars, docAnalyzer, pg)
} else {
	ocrBoxes = p.ocrDetectAndRecognize(ctx, pageImg, docAnalyzer, pg, label)
}
```

**作用**：先抽内嵌字符，再渲染 216 DPI 做 OCR/DLA。字符提取走 Rust `pdf_oxide`（每字形细粒度），渲染走 pdfium；OCR/DLA/TSR 都在**页级 worker 内完成**，`pageResult` 按页号收集避免乱序。

## 三、文档级版面合并 ★（parser.go:513-541）

```go
boxes = lyt.DedupIdenticalText(boxes)
boxes = lyt.DedupSubstringOverlaps(boxes)
boxes = lyt.AssignColumn(boxes)
boxes = lyt.TextMerge(boxes, medianHeights)
boxes = lyt.FinalReadingOrderMerge(boxes)
boxes = lyt.NaiveVerticalMerge(boxes, medianHeights, medianWidths, pageEnglish)
result.Tables = tbl.MergeTablesAcrossPages(result.Tables, nil)
boxes = tbl.ExtractTableAndReplace(boxes, result.Tables)
result.Sections = lyt.BoxesToSections(boxes, result.PageHeight)
result.Sections = tbl.MergeCaptions(result.Sections, result.Figures())
```

**作用**：`buildLayout` 是文档级**唯一合并点**——对应 Python 的 TextMerge/NaiveVerticalMerge/表格替换。页 worker 只产出独立产物，杜绝共享态竞争。

## 四、与 Python DeepDoc 的差异 ★

1. **并发模型**：Go 用 `runPageWorkers`（parser.go:373-431）走进程级 worker pool（`parserPageWorkerPool`，GOMAXPROCS*2），页级并行 + 每页 zoom 重试；Python 单线程按页串行。
2. **OCR 解耦**：OCR 推理通过 `doctype.DocAnalyzer` 接口（type/types.go:275-281：`DLA/TSR/OCRDetect/OCRRecognize/Health`）解耦，并用信号量限流（parser_concurrency.go:191-228）。
3. **坐标校正**：`pdf_oxide_engine.go:39-174` 手动处理 `/Rotate`（字节扫描 `/Rotate` + 与 pdfium 尺寸比对）和 CropBox 偏移，把 pdf_oxide 原始坐标对齐到 pdfium 的"旋转后"坐标；Python pdfplumber 内部自动翻 Y 轴。
4. **渲染**：默认走 pdfium（renderer_pdfium.go:15-36，AA/hinting 对扫描件 OCR 更准），非 CGO 退回引擎自带 `RenderPageImage`。

**OCR 检测框**用 `WarpCrop` 透视去斜 + 旋转识别（parser_ocr.go:15-96），坐标从像素除以 `DlaScale=3` 回到 PDF point——**保证和字符路径同一坐标系**。

## 五、DOCX 解析 —— office_oxide 读 docx

```go
// docx/reader.go:18-43 —— 打开 → ToIRJSON() → 展平成文档顺序 block
func ExtractRawBlocks(data []byte) ([]RawBlock, error) {
	doc, err := officeOxide.OpenFromBytes(data, "docx")
	irJSON, err := doc.ToIRJSON()
	for _, sec := range ir.Sections {
		for _, el := range sec.Elements {
			blocks = append(blocks, irElementToBlock(el)) // paragraph/table/image
		}
	}
}

// docx/parser.go:52-60 —— 映射成共享 doctype.Section
func Parse(data []byte, cfg doctype.ParserConfig) (*doctype.ParseResult, error) {
	blocks, err := ExtractRawBlocks(data)
	return &doctype.ParseResult{Sections: blocksToSections(blocks)}, nil
}
```

类型化解析器 `internal/parser/parser/docx_parser.go:70-165` 直接用同一库：`outputFormat=="json"` → `buildDOCXJSONSections`（{text, doc_type_kwd} items）；否则 `doc.ToMarkdown()`。

## 六、parser 类型化输出 —— 统一契约（parse_result.go:48-90）

```go
type ParseResult struct {
	OutputFormat string            // "json"/"markdown"/"text"/"html"，Err 时为空
	File map[string]any            // 富化后的文件元数据（outline/page_count）
	JSON []map[string]any          // json 家族：PDF 是 {text, doc_type_kwd} 数组
	Markdown string; Text string; HTML string
	Err error
}
type ParseResultProducer interface {
	ParseWithResult(ctx context.Context, filename string, data []byte) ParseResult
}
```

```go
// pdf_parser_common.go:337-381 —— deepdoc 的 doctype.ParseResult → typed JSON
func pdfParseResultToJSONWithOptions(filename string, parsed *deepdoctype.ParseResult, opts pdfPostProcessOptions) ParseResult {
	applyPDFPostProcess(&processed, opts)          // 排序/去TOC/去页眉/多栏重排/doc_type_kwd
	items := pdflayout.SectionsToJSON(processed.Sections)
	return ParseResult{
		OutputFormat: "json",
		File: map[string]any{"name": filename, "page_count": len(processed.PageHeight), "outline": outlinesToFileMeta(processed.Outlines)},
		JSON: items,
	}
}
```

**作用**：`ParseWithResult` 是每个 parser 家族唯一结构化出口，`GetParser(fileType)` 按文件类型返回实现。PDF 的 typed 输出是 `[]map[string]any`（每条含 `text`、`doc_type_kwd`、可选 `image`/`layout`/`positions`）。

## 七、分块 —— `chunk/` 的 rune 窗口切块（split.go:25-31, 93-114, 214-251）

```go
type SplitOperator struct { strategy string; boundaries []string; keepSeparators bool; chunkSize int; overlap int }

switch o.strategy {
case "sentence":  ctx.SplitChunks = o.splitSentences(text)
case "char":      ctx.SplitChunks = o.splitByChar(text)
case "paragraph": ctx.SplitChunks = o.splitByParagraph(text)
case "length":    ctx.SplitChunks = o.splitByLength(text)   // ★ 按 rune 计数的定长窗口
default:          ctx.SplitChunks = o.splitSentences(text)
}
```

```go
func (o *SplitOperator) splitByLength(text string) []ChunkData {
	step := chunkSize - overlap
	runes := []rune(text)                                // ★ 按 rune（非字节），多字节/中文安全
	for start := 0; start < len(runes); start += step {
		end := min(start+chunkSize, len(runes))
		chunks = append(chunks, ChunkData{Content: string(runes[start:end]), ...})
	}
}
```

**作用**：`splitByLength` 是 `chunk_token_num` 定长窗口的 Go 版近似（**非真正 token 计数**）；`delim.go:17-25` 的 backtick 包裹分隔符逻辑是对 Python `TokenChunker` 自定义分隔符的 parity。**真正的分词（rag_tokenizer 语义）在 C++ `internal/binding/cpp/tokenizer.cpp`，chunk 包不做 token 计数**。

## 八、和 Python 版的对齐（parity）★

```go
// parity_lock.go:9-27 —— 锁定必须达到 100% 网格对齐的表格 PDF
func parityLockedGridPDFs() map[string]bool {
	return map[string]bool{"06_table_content.pdf": true, "18_table_caption.pdf": true}
}
```

```go
// pipeline_parity_test.go:1-60（//go:build cgo && manual）—— 三阶段对齐 harness
// Phase 1 (char→section assembly) expects CharSim 100%.
// Phase 2 (DLA/TSR replay) ... additionally checked by grid against output/py/ocr/tables/.
// Phase 3 (OCR replay) feeds Python's raw per-page OCR detect results ...
//   textSim==100% -> PASS | table PDF, gridSim==100% -> GRID_OK
```

**作用（关键）**：读 Python dump 的 charspy + DLA/TSR/OCR 中间结果，通过 `replayCtxKey`（table_extract.go:14-33 的 `pageNumCtxKey/tableIdxCtxKey/ocrBoxIdxCtxKey`）把推理调用路由回 Python 的中间产物，让 Go 的版面/表格装配逻辑与 Python **逐项比对**。被锁定的 PDF 若 gridSim 掉下 100% 测试直接报错（防回归护栏）。

**其余刻意对齐点**（注释直接点名 Python 文件/行号）：
- `type/types.go:260-270`：`GarbageLayoutScoreThreshold=0.4`、"footer/header/reference" 垃圾布局——"Mirrors Python's garbage gate in `deepdoc/vision/layout_recognizer.py:97`"（深挖 03_02）
- `parser_ocr.go:256-268`：`sortCharsYFirstly` —— "Matching Python `Recognizer.sort_Y_firstly` in `recognizer.py:26-33`"
- `pdf_postprocess.go:13-16`：去页眉正则 `(?i)header|footer|number` —— "mirrors `rag/flow/parser/parser.py:754`"
- `docx_parser.go:68-69`：JSON/Markdown 路径分别 "mirrors python `parser.py:_docx()` / `naive.py: Docx() → naive_merge_docx()`"

---

## 九、数据流示意

```
PDF bytes
  → pdfoxide.NewEngine()              pdfoxide_bridge.go:19
  → Parser.Parse()                    parse_cgo.go:26
  → Parser.processPage() ×N workers   parser.go:179
      ├─ ExtractChars (pdf_oxide, /Rotate+CropBox 校正)
      ├─ RenderPage (pdfium 216 DPI)
      ├─ processPageBoxes → OCR (ocrMergeChars / ocrDetectAndRecognize)
      └─ enrichOnePageWithDeepDoc → DLA/TSR 表格
  → assembleDocument + buildLayout    parser.go:439/502
  → doctype.ParseResult{Sections, Tables, Outlines, Engine}
  → applyPDFPostProcess + SectionsToJSON    pdf_parser_common.go:337
  → typed ParseResult{OutputFormat:"json", JSON:[{text, doc_type_kwd, ...}], File}

DOCX bytes
  → officeOxide.OpenFromBytes + ToIRJSON     docx_parser.go:71
  → buildDOCXJSONSections                    docx_ir.go:232
  → typed ParseResult{OutputFormat:"json", JSON:[{text, doc_type_kwd, image}]}

两者汇合
  → chunk.Run(text, opts) preprocess→split→postprocess   execute.go:23
  → ChunkContext.ResultChunks = []ChunkData{Content, Size, Metadata}
```

---

## 十、对照 ai_assistant

| RAGFlow | 你的 ai_assistant | 差距 |
|---------|------------------|------|
| Rust/C++ FFI 原生库 | 纯 Python 库 | ⚠️ 慢格式（PDF）性能瓶颈 |
| 页级 worker 并行 | 逐页串行 | ⚠️ 长 PDF 慢 |
| 干净内嵌字 → OCR 二选一 | 无 OCR 判断 | ⚠️ 扫描件/乱码无兜底 |
| 坐标校正（/Rotate + CropBox） | 无 | ⚠️ 旋转 PDF 坐标错位 |
| parity 测试锁 100% 对齐 | 无 | ⚠️ 重构无法证明等价 |
| rune 窗口切块（多字节安全） | 字节切块 | ⚠️ 中文切碎 |

**落地优先级**：
- **P0**：**页级并行**——解析 PDF 按页分线程/协程，收集时按页号排序。纯 Python 也能上（`concurrent.futures`）。
- **P1**：**clean-char vs OCR 判断**——内嵌字干净就走字符，扫描件/乱码走 OCR。
- **P2**：parity 对齐测试——新老解析器对同一批文档逐页比对相似度，锁回归。

---

## 十一、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 引擎适配 | `pdfoxide_bridge.go:19` | pdf_oxide → PDFEngine |
| CGO 入口 | `parse_cgo.go:26` | Parse 传引擎所有权 |
| 单页流水线 | `processPage`（parser:179） | 抽字/渲染/OCR/DLA |
| OCR 策略 | parser:311-359 | clean-char vs 扫描 |
| 版面合并 | `buildLayout`（parser:513） | 唯一文档级合并点 |
| 坐标校正 | `pdf_oxide_engine.go:39` | /Rotate + CropBox |
| 类型化输出 | `ParseResult`（parse_result:48） | OutputFormat + JSON |
| 切块 | `splitByLength`（split:214） | rune 窗口 + overlap |
| parity | `pipeline_parity_test.go` | 三阶段逐项比对 |

**一句话心法**：**Go 原生解析 = 原生库（Rust 抽字 + C++ 渲染）+ 页级并行 + 与 Python 逐项对齐**。真正难的从来不是"用 Go 重写解析"，而是"**重写后行为和旧版一模一样**"——所以 RAGFlow 用 parity 测试锁 100% 对齐、用 GarbageLayout/去页眉正则逐点镜像 Python 实现。换语言是手段，**行为等价才是目的**。
