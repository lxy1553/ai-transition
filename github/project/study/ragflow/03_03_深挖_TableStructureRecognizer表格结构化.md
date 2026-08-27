# 深挖：TableStructureRecognizer 表格结构化（deepdoc/vision/table_structure_recognizer.py）

> 这是深挖 03_01 里 `_table_transformer_job` 调用的表格识别器——回答"**表格怎么从图片变成结构化 HTML**"。
> RAGFlow 的思路：**TSR 模型只产出结构框（行/列/表头/跨格），不识别文字；文字来自 OCR，靠 IoU 匹配把两者绑定，`construct_table` 再重建网格**。
> 这是普通 RAG 和 RAGFlow 差异最大的地方之一——表格不是"一堆文字"而是"能重建的表格"。

- 源码位置：`github/project/ragflow/deepdoc/vision/table_structure_recognizer.py`（616 行）
- 模型：`rag/res/deepdoc/tsr.onnx`（PaddleOCR 表格结构模型），domain = `"tsr"`，HF 回退
- 上游：深挖 03_01 的 `_table_transformer_job`（pdf_parser.py:470）给 OCR box 贴 R/H/C/SP 标签
- 下游：Chunker 消费 `construct_table` 产出的 HTML（深挖 04_01 的 `doc_type_kwd="table"`）

---

## 三问

- **Q1 解决什么问题**：版面分析只知道"这里是表格区域"，不知道"表格长什么样"。TSR 把表格图识别成**行、列、表头、跨格**结构，OCR 文字往里填，重建出真正的表格。
- **Q2 数据流哪一环**：解析链路——版面分析（03_02）定位表格 → TSR 识别结构 → construct_table 重建 → Chunker 当"表格块"处理。
- **Q3 删掉会怎样**：表格全被当正文文本流——列对齐、表头、数字全乱，LLM 读不懂，检索质量崩。

---

## 一、模型加载 —— `tsr.onnx`，domain="tsr"（tsr:40-51）

```python
class TableStructureRecognizer(Recognizer):
    labels = [
        "table", "table column", "table row",
        "table column header", "table projected row header", "table spanning cell",
    ]
    def __init__(self):
        try:
            super().__init__(self.labels, "tsr", os.path.join(get_project_base_directory(), "rag/res/deepdoc"))
        except Exception:
            super().__init__(self.labels, "tsr", snapshot_download(
                repo_id="InfiniFlow/deepdoc",
                local_dir=os.path.join(get_project_base_directory(), "rag/res/deepdoc")))
```

基类 `Recognizer.__init__`（recognizer.py:33-51）→ `load_model` 加载 `tsr.onnx`，记录输入输出节点 + `input_shape`。**6 个结构类别**：table / column / row / column header / projected row header / spanning cell。

---

## 二、`__call__` —— 表格图 → 结构组件框（tsr:53）

```python
def __call__(self, images, thr=0.2):
    table_structure_recognizer_type = os.getenv("TABLE_STRUCTURE_RECOGNIZER_TYPE", "onnx").lower()
    tbls = super().__call__(images, thr) if onnx  else self._run_ascend_tsr(images, thr)  # onnx/昇腾

    res = []
    for tbl in tbls:
        lts = [{"label": b["type"], "score": b["score"],
                "x0": b["bbox"][0], "x1": b["bbox"][2],
                "top": b["bbox"][1], "bottom": b["bbox"][-1]} for b in tbl]
        # ★ 对齐修正：行/表头 box 左右对齐（取均值或 min/max）
        left  = np.mean(left) if len(left) > 4 else np.min(left)
        right = np.mean(right) if len(right) > 4 else np.max(right)
        # 列 box 上下对齐（取中位数或 min/max）
        top    = np.median(top) if len(top) > 4 else np.min(top)
        bottom = np.median(bottom) if len(bottom) > 4 else np.max(bottom)
    return res     # [[{label,score,x0,x1,top,bottom},...], ...]  每张表一个列表
```

**作用**：逐表格图推理（基类 `Recognizer.__call__` 批处理 + NMS），输出**带标签的结构框**。对齐修正是让"行框对齐到同一左边界"——视觉模型的行框有误差，取多数值的均值/中位数。

---

## 三、标题判定 `is_caption` / 单元格分类 `blockType`（tsr:113/125）

```python
@staticmethod
def is_caption(bx):
    patt = [r"[图表]+[ 0-9:：]{2,}",
            r"(?i)Fig\.?\s*\d+", r"(?i)Figure\s+\d+", r"(?i)Table\s+\d+"]
    if any([re.match(p, bx["text"].strip()) for p in patt]) or bx.get("layout_type", "").find("caption") >= 0:
        return True
    return False
```

```python
@staticmethod
def blockType(b):
    patt = [
        ("^(20|19)[0-9]{2}[年/-][0-9]{1,2}[月/-][0-9]{1,2}日*$", "Dt"),   # 日期
        (r"^第*[一二三四1-4]季度$", "Dt"),
        ("^[0-9.,+%/ -]+$", "Nu"),        # 纯数字
        (r"^[0-9A-Z/\._~-]+$", "Ca"),     # 编码/序号
        (r"^[A-Z]*[a-z' -]+$", "En"),     # 英文单词
        (r"^[0-9.,+-]+[0-9A-Za-z/$￥%<>（）()' -]+$", "NE"),  # 数字+混合
        (r"^.{1}$", "Sg"),                # 单字符
    ]
    for p, n in patt:
        if re.search(p, b["text"].strip()): return n
    tks = [t for t in rag_tokenizer.tokenize(b["text"]).split() if len(t) > 1]
    if len(tks) > 3:  return "Tx" if len(tks) < 12 else "Lx"   # 文本 / 长文本
    if len(tks) == 1 and rag_tokenizer.tag(tks[0]) == "nr": return "Nr"  # 人名
    return "Ot"
```

**作用**：`is_caption` 摘出"表 1-2 / Figure 3"标题行；`blockType` 把单元格归为日期/数字/编码/英文/混合/文本等**语义类型**——**数字表 vs 文本表的表头判定策略不同**（见第 4 点）。

---

## 四、`construct_table` —— 用 R/H/C/SP 重建网格 ★（tsr:156-353）

### 输入：已贴标签的 OCR box（来自 `_table_transformer_job`）

```python
# pdf_parser.py:595-636 给表格区每个文本 box 打的标签：
#   R  → 行号（匹配 ".* (row|header)" 组件）
#   H  → 表头（匹配 ".*header$" 组件）
#   C  → 列号（匹配 "table column" 组件，find_horizontally_tightest_fit）
#   SP → 跨行跨列（匹配 ".*spanning" 组件）
```

### 核心：按 R 分行、按 C 分列，填二维网格（176-219）

```python
# ① 行优先排序 → 切出 rows
rowh = [b["R_bott"] - b["R_top"] for b in boxes if "R" in b]
rowh = np.min(rowh) if rowh else 0
boxes = Recognizer.sort_R_firstly(boxes, rowh / 2)
boxes[0]["rn"] = 0; rows = [[boxes[0]]]; btm = boxes[0]["bottom"]
for b in boxes[1:]:
    b["rn"] = len(rows) - 1
    lst_r = rows[-1]
    if lst_r[-1].get("R","") != b.get("R","") or (b["top"] >= btm - 3 and lst_r[-1].get("R","-1") != b.get("R","-2")):
        btm = b["bottom"]; b["rn"] += 1; rows.append([b]); continue   # 新行
    btm = (btm + b["bottom"]) / 2.0; rows[-1].append(b)               # 归入当前行

# ② 列优先排序 → 切出 cols（跨页表先按页、再列）
boxes = Recognizer.sort_C_firstly(boxes, colwm/2)

# ③ 填网格 tbl[行][列]
tbl = [[[] for _ in range(len(cols))] for _ in range(len(rows))]
for b in boxes: tbl[b["rn"]][b["cn"]].append(b)
```

### 表头判定（336-348）：行内 H 标签占比 > 50%

```python
hdset = set([])
for i in range(len(tbl)):
    cnt, h = 0, 0
    for j, arr in enumerate(tbl[i]):
        if not arr: continue
        cnt += 1
        if max_type == "Nu" and arr[0]["btype"] == "Nu": continue   # 数字表：纯数字格不算表头
        if any([a.get("H") for a in arr]) or (max_type == "Nu" and arr[0]["btype"] != "Nu"): h += 1
    if h / cnt > 0.5: hdset.add(i)     # ★ 表头行
```

### 跨行跨列 + 渲染

```python
# __cal_spans 用 SP box 的 H_left/H_right/H_top/H_bott 与行列几何中心算 colspan/rowspan
if html:
    return TableStructureRecognizer.__html_table(cap, hdset, TableStructureRecognizer.__cal_spans(boxes, rows, cols, tbl, True))
return TableStructureRecognizer.__desc_table(cap, hdset, TableStructureRecognizer.__cal_spans(boxes, rows, cols, tbl, False), is_english)
```

**作用（关键）**：
- **TSR 结构框 + OCR 文字，靠标签绑定**：`R`/`C` 决定每个字在哪行哪列，`H` 决定表头，`SP` 决定跨格——**视觉模型只出结构，文字靠 OCR 填进去**。
- **数字表 vs 文本表**：数字表（`max_type=="Nu"`）里"纯数字格不算表头"——因为数字表第一行经常是数字不是列名，用 `blockType` 区分。
- **两种输出**：`html=True` → `<table>` HTML（给 LLM 读）；`html=False` → 纯文本键值行（给 VLM/精简场景）。

---

## 五、HTML 输出 `__html_table`（tsr:356）

```python
def __html_table(cap, hdset, tbl):
    html = "<table>"
    if cap: html += f"<caption>{cap}</caption>"
    for i in range(len(tbl)):
        row = "<tr>"
        for j, arr in enumerate(tbl[i]):
            if arr is None: continue
            if not arr:
                row += "<td></td>" if i not in hdset else "<th></th>"   # 空单元格
                continue
            txt = " ".join([c["text"] for c in Recognizer.sort_Y_firstly(arr, h)])  # 同格多 box 按 Y 拼接
            sp = ""
            if arr[0].get("colspan"): sp = "colspan={}".format(arr[0]["colspan"])
            if arr[0].get("rowspan"): sp += " rowspan={}".format(arr[0]["rowspan"])
            row += f"<th {sp} >{txt}</th>" if i in hdset else f"<td {sp} >{txt}</td>"
        if row != "<tr>": row += "</tr>"
        else: row = ""
        html += "\n" + row
    return html + "\n</table>"
```

**输出形如**：
```html
<table>
<caption>表1</caption>
<tr><th >列名</th></tr>
<tr><td colspan=2 rowspan=2 >合并格</td><td >值</td></tr>
</table>
```
表头行用 `<th>`，跨行列加 `colspan`/`rowspan`。**这个 HTML 直接进 chunk 的 `text`**（深挖 04_01），LLM 读它比读乱文字好一个量级。

---

## 六、方向自适应 `_evaluate_table_orientation`（pdf_parser.py:367）

```python
rotations = [(0,"original"), (90,"rotate_90"), (180,"rotate_180"), (270,"rotate_270")]
for angle, name in rotations:
    rotated_img = table_img if angle == 0 else table_img.rotate(-angle, expand=True)
    ocr_results = self.ocr(np.array(rotated_img))
    if ocr_results:
        scores = [conf for _, (_, conf) in ocr_results]
        avg_score = sum(scores) / len(scores)
        total_regions = len(scores)
        # ★ 综合分 = 平均置信度 × (1 + 0.1×区域数加成) —— 区域越多+置信越高=越像正方向
        combined_score = avg_score * (1 + 0.1 * min(total_regions, 50) / 50)
        ...
        if combined_score > best_score:
            best_score, best_angle, best_img = combined_score, angle, rotated_img
# ★ 保守阈值：非0°必须比0°高0.2 且 0°得分<0.8 才采用旋转
if best_angle != 0 and score_0 is not None:
    if not (best_score - score_0 > 0.2 and score_0 < 0.8):
        best_angle, best_img = 0, table_img
return best_angle, best_img, results
```

**作用**：歪表/横表在 TSR 前先摆正——**4 个角度各 OCR 一次，用「识别置信度 × 区域数」当方向打分**。区域多且置信高 = 字多且清楚 = 越像正方向。加**保守阈值**（非 0° 必须显著更优）防把正表误转。选定角度后由 `_table_transformer_job` 存进 `table_rotations`，TSR/OCR 坐标再经 `_map_clockwise_rotated_point_to_original`（458-468）映射回原页空间。

---

## 七、数据流转示意

```
PDF 表格区域 (crop 图)
  │
  ▼  _evaluate_table_orientation (pdf_parser.py:367) —— 0/90/180/270° OCR 打分选最佳旋转
  ▼  TableStructureRecognizer.__call__ (tsr:53) —— tsr.onnx 批推理 + NMS
  │      输出: [{label,score,x0,x1,top,bottom}], label ∈ {column/row/header/spanning}
  ▼  _table_transformer_job (pdf_parser.py:470) —— TSR 组件映射回页坐标
  │      给每个 OCR 文本 box 贴 R(row)/H(header)/C(column)/SP(spanning) 标签
  ▼  construct_table (tsr:156)
  │      sort_R_firstly 分行 → sort_C_firstly 分列 → tbl[行][列] 网格
  │      → __cal_spans 算 rowspan/colspan → 表头行判定（H/btype 占比）
  ├─ html=True  → __html_table (tsr:356) → <table><th><td colspan.. rowspan..>
  └─ html=False → __desc_table (tsr:400) → ["表头：值; 表头2：值2", ...] 键值行
```

**要点**：**TSR 只出结构框不认字**；文字靠 OCR，靠 `_table_transformer_job` 的 IoU 匹配（行/表头/跨格 thr=0.3）+ 列紧贴匹配绑定；`construct_table` 据此重建 HTML。

---

## 八、对照 ai_assistant

| RAGFlow | 你的 ai_assistant | 差距 |
|---------|------------------|------|
| TSR 结构识别 + OCR 绑定 | 表格当纯文本 | ❌ 表格读不懂 |
| `<table>` HTML 重建（含 colspan/rowspan） | 无 | ⚠️ 跨行跨列丢失 |
| 表头判定（数字表/文本表分策略） | 无 | ⚠️ 表头当普通行 |
| 表格方向自适应 | 无 | ⚠️ 歪表全乱 |
| blockType 单元格语义分类 | 无 | 概念参考 |

**落地优先级**：
- **P0**：轻量方案——**识别出"这是表格区域"，整块转 Markdown 表格**（用 `|` 列分隔 + 检测分隔线）。不需要 TSR 模型，30 行代码，LLM 立刻能读。
- **P1**：表头判定——数字表/文本表分策略，表格转出来语义才对。
- **P2**：完整 TSR（需 onnx 模型 + 训练数据）——高价值文档（财报/台账）才值得。

---

## 九、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 模型加载 | `__init__`（40） | tsr.onnx + 6 类结构标签 |
| 结构识别 | `__call__`（53） | 表格图 → 行/列/表头/跨格框 |
| 标题/类型 | `is_caption`/`blockType`（113/125） | 摘标题 + 单元格语义分类 |
| 网格重建 | `construct_table`（156） | R 分行 C 分列填网格 |
| 表头判定 | hdset（336） | H 占比 >50% 判表头 |
| 跨行跨列 | `__cal_spans`（499） | SP → colspan/rowspan |
| HTML 输出 | `__html_table`（356） | `<table><th><td colspan..>` |
| 方向校正 | `_evaluate_table_orientation`（pdf:367） | 4 角 OCR 打分 + 保守阈值 |

**一句话心法**：**表格结构化 = 视觉出结构（行/列/表头/跨格）+ OCR 填文字 + 标签绑定 + 网格重建**。RAGFlow 把"识别表格"拆成"识别结构"和"识别文字"两步各用一个模型，再用几何匹配合起来——模块边界清晰，任意一步可替换。
