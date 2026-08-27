# 主干 ③：DeepDoc 文档解析（Parser + deepdoc）

> 这是 RAGFlow 的**立身之本**——"Quality in, quality out" 的来源。
> 对照你上一个问题「第一步：数据读取 → 第二步：解析清洗」，DeepDoc 就是那个"生产级解析"的完整实现。

## 三问

- **Q1 解决什么问题**：把复杂非结构化文档（PDF/Word/Excel/图片）变成**结构化**的「文本块 + 表格 + 图片描述」，而不是简单抽一堆文本。
- **Q2 数据流哪一环**：离线链路第二步——上游 File 拿到原始文件，这里解析成 chunks 的原料。
- **Q3 删掉会怎样**：只能抽纯文本，双栏 PDF 混乱、表格变乱码、扫描件全丢 → RAG 质量上限被锁死。

---

## 一、DeepDoc 的核心思路（先理解再读代码）

普通 RAG 解析 PDF = 抽文本。DeepDoc 解析 PDF = **先"看"版面，再"理解"结构**：

```
PDF 每一页
  │
  ├─ 版面分析 (layout_recognizer)     → 识别哪些是标题/正文/表格/图片/页眉页脚
  ├─ 文本检测+OCR (ocr.py)           → 扫描件/图片里的文字
  ├─ 表格结构识别 (table_structure)   → 表格的"行×列"结构 → 转 HTML/Markdown
  ├─ 阅读顺序合并 (_text_merge)       → 双栏/多栏按"人类阅读顺序"拼接
  └─ 图表分离 (_extract_table_figure) → 表格/图片单独拎出来，附上说明
```

产出：`sections`（文本块，带位置）+ `tables`（结构化表格）。

---

## 二、Parser 组件（rag/flow/parser/parser.py）—— 分派到解析引擎

### ① _invoke()（parser.py:1393）—— 按文件后缀分派

```python
async def _invoke(self, **kwargs):
    function_map = {
        "pdf": self._pdf,          # PDF → _pdf
        "markdown": self._markdown,
        "text&code": self._code,
        "html": self._html,
        "spreadsheet": self._spreadsheet,   # Excel
        "slides": self._slides,             # PPT
        "doc": self._doc, "docx": self._docx,   # Word
        "image": self._image, "audio": self._audio,
        "video": self._video, "email": self._email, "epub": self._epub,
    }

    # ① 从上游 File 组件拿文件名 + 内容
    name = from_upstream.name
    if self._canvas._doc_id:
        blob = settings.STORAGE_IMPL.get(b, n)   # 从 MinIO 拉原始文件
    else:
        blob = FileService.get_blob(...)

    # ② 按文件名后缀匹配到对应 parser，丢进线程池执行
    for p_type, conf in self._param.setups.items():
        if from_upstream.name.split(".")[-1].lower() not in conf.get("suffix", []):
            continue
        await thread_pool_exec(function_map[p_type], name, blob, **kwargs)
        break
```

**作用**：一个 `Parser` 组件统一处理 13 种文件类型，按后缀分派。新增格式只需加一个 `_xxx` 方法 + 注册进 function_map。

### ② _pdf()（parser.py:334）—— 多引擎可插拔

```python
def _pdf(self, name, blob, **kwargs):
    conf = self._param.setups["pdf"]
    raw_parse_method = conf.get("parse_method", "")   # 用户选的解析引擎

    # ★ 按用户选择分派到不同解析引擎，全部输出统一的 bboxes 结构
    if parse_method.lower() == "deepdoc":
        pdf_parser = RAGFlowPdfParser()               # 自研（默认）
        bboxes = pdf_parser.parse_into_bboxes(blob, callback=self.callback)

    elif parse_method.lower() == "plain_text":
        pdf_parser = PlainParser()                    # 纯文本（快，无版面分析）
        lines, _ = pdf_parser(blob)

    elif parse_method.lower() == "mineru":
        # MinerU：外部 OCR 模型，返回 (text, layout_type, positions)
        pdf_parser = ocr_model.mdl
        lines, _ = pdf_parser.parse_pdf(filepath=name, binary=blob, parse_method="pipeline")
        # 统一转成 bbox 结构 {text, layout_type, positions, image}

    elif parse_method.lower() == "docling":
        pdf_parser = DoclingParser()                  # IBM Docling 引擎
        ...
```

**作用（关键）**：**多解析引擎可插拔**——同一个 `_pdf`，按配置选 deepdoc / plain_text / MinerU / Docling / PaddleOCR / SoMark / Mistral OCR，输出统一成 `bboxes` 结构。这就是"换引擎不改主流程"（对照 Vanna 的可插拔）。

---

## 三、DeepDoc 核心：RAGFlowPdfParser（deepdoc/parser/pdf_parser.py）

> **深挖版**见 `03_01_深挖_DeepDoc_PDF解析器主干.md`（9 步流水线 + 乱码兜底 + 表格结构化 + 批量分窗全解）。这里只讲骨架。

### ① 版面分析 _layouts_rec（pdf_parser.py:877）

```python
def _layouts_rec(self, ZM, drop=True):
    """用版面模型识别每一页的布局：标题/正文/表格/图片/页眉页脚"""
    # 把 PDF 每页渲染成图片 → 送版面识别模型 → 得到带 label 的 boxes
    # label: "title" / "text" / "table" / "figure" / "header" / "footer"
```

### ② 阅读顺序合并 _text_merge（pdf_parser.py:969）

```python
def _text_merge(self, zoomin=3):
    """把版面识别的 boxes 按'人类阅读顺序'合并成文本段落"""
    # 关键：双栏 PDF 不能按坐标顺序硬拼，要识别栏结构，左栏读完读右栏
```

**作用**：这就是你上一个问题里说的「**双栏 PDF 顺序读会左右混在一起**」——DeepDoc 专门解决它。

### ③ 表格结构识别 + 分离（pdf_parser.py:1287）

```python
def _extract_table_figure(self, need_image, ZM, return_html, ...):
    """把表格/图片从文本流里单独拎出来"""
    # 表格 → TableStructureRecognizer 识别行列 → 转 HTML 表格
    # 图片 → 裁出来，交给 VLM 生成描述
```

### ④ OCR（pdf_parser.py:771 + vision/ocr.py）

```python
# deepdoc/vision/ocr.py:488 —— PaddleOCR 封装
class OCR:
    def __init__(self, model_dir=None):
        # 加载 TextDetector(文字检测) + TextRecognizer(文字识别) 两个模型
    def __call__(self, img): ...   # 图片 → 文字

# deepdoc/vision/table_structure_recognizer.py:30 —— 表格结构
class TableStructureRecognizer(Recognizer):
    def __call__(self, images, thr=0.2):
        # 识别表格：行线、列线、单元格合并 → 返回结构化的行×列
    def construct_table(boxes, is_english=False, html=True, ...):
        # 结构化的行×列 → HTML/Markdown 表格字符串
```

---

## 四、模板层：naive.py 的 Pdf/Docx 类（rag/app/naive.py）

### by_deepdoc（naive.py:116）—— 解析入口

```python
def by_deepdoc(filename, binary=None, from_page=0, to_page=MAXIMUM_PAGE_NUMBER,
               lang="Chinese", callback=None, pdf_cls=None, **kwargs):
    pdf_parser = pdf_cls() if pdf_cls else Pdf()     # 默认用 Pdf 类
    # ① 解析：得到 sections(文本块) + tables(表格)
    sections, tables = pdf_parser(filename if not binary else binary,
                                  from_page=from_page, to_page=to_page, callback=callback)
    # ② 表格/图片用 VLM 生成语义描述（增强）
    tables = vision_figure_parser_pdf_wrapper(tbls=tables, sections=sections, ...)
    return sections, tables, pdf_parser
```

### Pdf 类（naive.py:719）

```python
class Pdf(PdfParser):
    def __call__(self, filename, binary=None, ...):
        # 调 deepdoc 的 RAGFlowPdfParser，返回 sections + tables
        # 每条 section 是 (text, 元数据)；每条 table 是 (html_table, 位置)
```

**作用**：`rag/app/naive.py` 的 `Pdf/Docx/Markdown` 类是对 deepdoc 的**二次封装**，把 deepdoc 的底层输出，规整成「离线分块」要用的 `sections + tables` 格式。模板层（naive/paper/laws）都在这一层做各自的解析。

---

## 五、解析引擎清单（多引擎可插拔）

| 引擎 | 代码 | 特点 | 适用场景 |
|------|------|------|---------|
| DeepDoc（自研） | `RAGFlowPdfParser` | 版面分析+OCR+表格，质量最高 | 默认，复杂文档 |
| PlainParser | `PlainParser` | 只抽文本，最快 | 简单纯文本 PDF |
| MinerU | `by_mineru` | 外部 OCR 模型（LLMBundle） | 扫描件、公式 |
| Docling | `by_docling` | IBM 开源，版面理解强 | 结构化文档 |
| PaddleOCR | `by_paddleocr` | 国产 OCR，中文强 | 中文扫描件 |
| SoMark / Mistral OCR | `by_somark` / `by_mistral_ocr` | 多模态 OCR | 复杂版面 |

---

## 六、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| Parser._invoke | `parser.py:1393` | 按后缀分派 13 种文件类型 |
| Parser._pdf | `parser.py:334` | 多引擎可插拔（deepdoc/mineru/docling...） |
| RAGFlowPdfParser._layouts_rec | `pdf_parser.py:877` | 版面分析（标题/正文/表格/图） |
| RAGFlowPdfParser._text_merge | `pdf_parser.py:969` | 双栏阅读顺序合并 |
| TableStructureRecognizer | `table_structure_recognizer.py:30` | 表格行×列结构化 |
| OCR | `ocr.py:488` | 扫描件/图片文字识别 |
| by_deepdoc | `naive.py:116` | 解析入口 + VLM 图表增强 |

**核心心法**：**"解析"不是抽文本，是"结构化"**。高质量 RAG 的分水岭在于：能不能把 PDF 的版面/表格/图片都理解对。你的 ai_assistant 如果只 `read_file()` 读文本，遇到 PDF 就废了——该引入 deepdoc 式的「版面分析 + 表格结构化 + OCR」。
