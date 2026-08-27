# 深挖：RAGFlowPdfParser 解析主干（deepdoc/parser/pdf_parser.py）

> 这是主干③「DeepDoc 文档解析」里 **PDF 解析器**的完整解剖——`RAGFlowPdfParser`，源码 2145 行。
> 它回答了核心问题：**一个 PDF 是怎么变成「带版面结构的 box 列表」+「表格图 + 图片」的**。
> 这也是 RAGFlow 和普通 RAG「能读到好文本」的分水岭——普通 RAG 用 pdfminer/pypdf 抽文本，RAGFlow 是「渲染 + OCR + 版面分析 + 表格结构化」四件套。

- 源码位置：`github/project/ragflow/deepdoc/parser/pdf_parser.py`
- 双路径：**全量路径 `__call__`（1744）** ｜ **批量路径 `parse_into_bboxes`（1771，按页分窗，大 PDF 用）**
- 前面版本（2.x）用 RAGFlow 传统三段式；现在引擎入口统一走 `Parser._invoke` 多引擎分派（主干③已讲）

---

## 三问

- **Q1 解决什么问题**：PDF 是「排版文件」不是「文本文件」——把 PDF 变成「**文本 + 版面位置 + 表格图 + 图片**」四类可被下游 Chunker / 检索消费的结构化输出。
- **Q2 数据流哪一环**：离线链路第②环——上游 TaskExecutor 分派解析，下游 `_extract_table_figure` 产出表格给 Chunker。
- **Q3 删掉会怎样**：表格读成乱行、双栏读成单行、图片里的字全部丢失——RAG 检索质量断崖式下跌。

---

## 一、主入口 `__call__` —— 9 步流水线（pdf_parser.py:1744）

```python
def __call__(self, fnm, need_image=True, zoomin=3, return_html=False, auto_rotate_tables=None):
    # ① 表格方向自适应默认开（可用环境变量 TABLE_AUTO_ROTATE 关掉）
    if auto_rotate_tables is None:
        auto_rotate_tables = os.getenv("TABLE_AUTO_ROTATE", "true").lower() in ("true", "1", "yes")

    self.outlines = extract_pdf_outlines(fnm)     # ② 抽目录（书签大纲）→ 后续做章节定位
    self.__images__(fnm, zoomin)                   # ③ 渲染页面为图 + 抽内嵌文字 + OCR（最重的一步）
    self._layouts_rec(zoomin)                      # ④ 版面分析：每页 → 标题/正文/表格/图/页眉页脚
    self._table_transformer_job(zoomin, auto_rotate=auto_rotate_tables)  # ⑤ 表格结构识别 + 方向校正
    self._text_merge()                             # ⑥ 同一行/同栏的碎 box 横向合并成句
    self._concat_downward()                        # ⑦ 跨页纵向拼接（阅读顺序）
    self._filter_forpages()                        # ⑧ 过滤封面页/目录页
    tbls = self._extract_table_figure(need_image, zoomin, return_html, False)  # ⑨ 抽表格图和图片 + 匹配标题
    return self.__filterout_scraps(deepcopy(self.boxes), zoomin), tbls  # ⑩ 过滤噪声块 → 返回文本+表格
```

**9 步一句话**：**渲染 → 抽字 → OCR → 版面分类 → 表格结构化 → 文本合并 → 拼页 → 去封面 → 抽表抽图 → 滤噪声**。

```
PDF 文件
  │
  ▼
③ __images__ ── 每页 render 成高清图 + pdfplumber 抽字符 + 全页 OCR（乱码页走 OCR）
  │                产出：page_images（页图） + page_chars（每页字符）+ boxes（OCR 检测框）
  ▼
④ _layouts_rec ── LayoutRecognizer（ONNX/YOLO）给每个 box 打版面类型：title/table/figure/caption/header/正文…
  ▼
⑤ _table_transformer_job ── 表格方向评估(auto_rotate) → TableStructureRecognizer 识别单元格
  │                           → 把行/列/表头/跨列标签(R/H/C/SP) 回填到 box 上
  ▼
⑥⑦ _text_merge / _concat_downward ── 水平合并同段 + 按阅读顺序排序（当前=Y 优先）
  ▼
⑧ _filter_forpages ── 干掉封面/目录/致谢页
  ▼
⑨ _extract_table_figure ── 表格和图片从 box 流里"抠"出来，各自裁成图 + 拼上标题(caption)
  │                         表格还用 TSR 重建成 HTML/JSON 结构
  ▼
⑩ __filterout_scraps ── 过滤孤字/噪点（如页面边角的页码、页码残留）
  ▼
返回：1) 正文文本（带位置标签 @@页码\t坐标##）  2) 表格/图片的 (图, 文本或结构)
```

---

## 二、步骤③ `__images__` —— 渲染 + 抽字 + 乱码检测 + OCR（pdf_parser.py:1608）

这是最重的一步，也是**生产级兜底最多的**一步。

```python
def __images__(self, fnm, zoomin=3, page_from=0, page_to=MAXIMUM_PAGE_NUMBER, callback=None):
    with pdfplumber.open(fnm) as pdf:
        # ① 每页渲染成高清图（分辨率 72*zoomin，默认 zoomin=3 → 216 DPI，够 OCR 用）
        self.page_images = [p.to_image(resolution=72*zoomin, antialias=True).annotated
                            for p in pdf.pages[page_from:page_to]]
        # ② 抽内嵌字符（dedupe_chars 去重叠字符）+ 只留"有颜色"的字符（滤掉背景水印层）
        self.page_chars = [[c for c in page.dedupe_chars().chars if self._has_color(c)]
                           for page in pdf.pages[page_from:page_to]]
        # ③ ★ 乱码检测：pdfplumber 抽出的字如果是乱码，整页清空 → 强制走 OCR
        for pi, page_ch in enumerate(self.page_chars):
            sample_text = "".join(c["text"] for c in (page_ch if len(page_ch)<=200 else page_ch[:200]))
            if self._is_garbled_text(sample_text, threshold=0.3):   # 策略1: PUA/CID 乱码
                self.page_chars[pi] = []
                continue
            if self._is_garbled_by_font_encoding(page_ch):          # 策略2: 子集字体 CJK→ASCII 乱码
                self.page_chars[pi] = []
```

**为什么先抽字再 OCR**：PDF 里有「文字层」，直接抽最快最准；但**文字层常是乱码**（CID 映射失败 / 字体子集加密 / 扫描件没文字层）。所以策略是：**能抽先抽，抽出来是乱码就整页转 OCR**。

```python
    # ④ 每页并发 OCR（多 GPU 时按 PARALLEL_DEVICES 分设备并发）
    async def __img_ocr(i, id, img, chars, limiter):
        self._insert_word_spaces(chars)          # ★ 从字符几何位置恢复空格（很多 PDF 不写空格，靠间隙定位）
        if limiter:
            async with limiter:                  # 每 GPU 一个信号量（背压，防止打爆显存）
                await thread_pool_exec(self.__ocr, i+1, img, chars, zoomin, id)
        ...
    for i, img in enumerate(self.page_images):
        semaphore = self.parallel_limiter[i % settings.PARALLEL_DEVICES]  # 轮流分配到各 GPU
        tasks.append(asyncio.create_task(wrapper(i, img, chars, semaphore)))
    await asyncio.gather(*tasks, return_exceptions=False)
```

**关键心法**：**OCR 是"兜底"不是"默认"**。只有抽字抽不动/抽乱才 OCR——OCR 慢一个数量级。多 GPU 时按页轮询分到 `parallel_limiter`（每 GPU 一个 `asyncio.Semaphore(1)`）。

```python
    # ⑤ 兜底：如果 OCR 结果为空且放大倍数还没到极限，自动放大 3 倍重试
    self.page_cum_height = np.cumsum(self.page_cum_height)
    if len(self.boxes) == 0 and zoomin < 9:
        self.__images__(fnm, zoomin*3, page_from, page_to, callback)   # ★ 自动放大重试
```

**生产级细节**：`zoomin=3` 渲染的图 OCR 不出任何 box？自动放大到 `zoomin*3=9`（648 DPI）重试一次。低质量扫描件的自适应。

---

## 三、步骤④ `_layouts_rec` —— 版面分析（pdf_parser.py:877）

```python
def _layouts_rec(self, ZM, drop=True):
    # 调用 LayoutRecognizer（ONNX 模型）→ 给每个 box 打 layout_type
    self.boxes, self.page_layout = self.layouter(self.page_images, self.boxes, ZM, drop=drop)
    # ★ 累计 Y 坐标：把每页的 top/bottom 加上前面所有页的高度 → 全局统一坐标系
    for i in range(len(self.boxes)):
        self.boxes[i]["top"] += self.page_cum_height[self.boxes[i]["page_number"] - 1]
        self.boxes[i]["bottom"] += self.page_cum_height[self.boxes[i]["page_number"] - 1]
```

**作用**：这是 DeepDoc 的灵魂。LayoutRecognizer 识别出**每个 box 是标题 / 正文 / 表格 / 图 / 表标题 / 页眉页脚**，产出 `page_layout`（每页的版面对象）。之后：
- **表格** box → 交给步骤⑤做表格结构化
- **图** box → 裁剪成图片
- **标题** box → 留给 Chunker 做标题层级（分块锚点）

**关键心法**：普通 RAG「一行一行读 PDF」在这里变成「**理解版面后再读**」——双栏论文、带表带图的报告，阅读顺序不会乱。

配套 **`_assign_column`（885）**：用 **KMeans + 轮廓系数**自动判断每页是几栏（1 栏/2 栏/3 栏），再按栏分配 `col_id`——**双栏 PDF 的阅读顺序问题**的解法。

```python
for k in range(1, max_try+1):
    km = KMeans(n_clusters=k, n_init="auto")
    labels = km.fit_predict(x0s)                      # 按每行起始 x 聚类
    score = silhouette_score(x0s, labels)             # 轮廓系数：几类的分群最清晰
    if score > best_score: best_k = k
global_cols = Counter(page_cols.values()).most_common(1)[0][0]  # 全篇多数票定栏数
```

---

## 四、步骤⑤ `_table_transformer_job` —— 表格结构识别 + 方向校正（pdf_parser.py:470）

```python
def _table_transformer_job(self, ZM, auto_rotate=True):
    # ① 从版面里筛出所有表格，裁出表格图（四周留 MARGIN=10 像素）
    for p, tbls in enumerate(self.page_layout):
        tbls = [f for f in tbls if f["type"] == "table"]
        for tb in tbls:
            table_img = self.page_images[p].crop((left, top, right, bott))
            if auto_rotate:
                # ★ ② 表格方向评估：试多个旋转角，选分数最高的
                best_angle, rotated_img, scores = self._evaluate_table_orientation(table_img)
                imgs.append(rotated_img)              # 喂给 TSR 的是"摆正后的表格图"
            else:
                imgs.append(table_img)

    # ③ TableStructureRecognizer（TSR）识别单元格 → 产出 header/row/column/spanning 组件
    recos = self.tbl_det(imgs)

    # ④ 把 TSR 组件的坐标从"旋转后图空间"映射回"原页空间"
    _map_tsr_component_to_page_space(component, table_pos)
    #   组件 x0/top 等用 _map_clockwise_rotated_point_to_original 反旋转，再加累计页高

    # ⑤ ★ 给表格区域里的文本 box 打标签：R(行)/H(表头)/C(列)/SP(跨列)
    rows   = gather(r".* (row|header)")
    headers = gather(r".*header$")
    spans  = gather(r".*spanning")
    for b in self.boxes:
        if b.get("layout_type", "") != "table": continue
        ii = Recognizer.find_overlapped_with_threshold(b, rows, thr=0.3)
        if ii is not None: b["R"] = ii               # 属于哪一行
        ii = Recognizer.find_overlapped_with_threshold(b, headers, thr=0.3)
        if ii is not None: b["H"] = ii               # 是不是表头
        ii = Recognizer.find_horizontally_tightest_fit(b, clmns)
        if ii is not None: b["C"] = ii               # 属于哪一列
        ii = Recognizer.find_overlapped_with_threshold(b, spans, thr=0.3)
        if ii is not None: b["SP"] = ii              # 是否跨列
```

**作用（关键）**：这是「**表格结构化**」——不只是把表格文字抽出来，而是重建**行(R)/列(C)/表头(H)/跨列(SP)**结构。有了这些标签：
- 后续 `construct_table` 能重建表格为 HTML 表格或 JSON（Chunker 拿到的是「结构化表格」而不是"一堆文字"）
- **`auto_rotate` 是深坑**：扫描件表格经常是歪的/横的，直接识别会全错。先试旋转角再识别，但旋转后坐标要精确反变换回原页。

---

## 五、步骤⑥⑦ 文本合并 `_text_merge` / `_concat_downward`

### `_text_merge`（969）—— 横向合并同一行

```python
def _text_merge(self, zoomin=3):
    bxs = self._assign_column(self.boxes, zoomin)     # 先分栏
    i = 0
    while i < len(bxs)-1:
        b, b_ = bxs[i], bxs[i+1]
        # 只在同页、同栏、同版面块、且 y 中心线接近（同行）时才合并
        if b["page_number"] != b_["page_number"] or b.get("col_id") != b_.get("col_id"): i += 1; continue
        if b.get("layoutno","0") != b_.get("layoutno","1") or b.get("layout_type","") in ["table","figure","equation"]: i += 1; continue
        if abs(self._y_dis(b, b_)) < self.mean_height[page-1] / 3:   # ★ y 距离 < 行高 1/3 = 同一行
            bxs[i]["text"] += b_["text"]              # 拼文本、合并边界框
            bxs[i]["x1"] = b_["x1"]; bxs[i]["bottom"] = (b["bottom"]+b_["bottom"])/2
            bxs.pop(i+1)
            continue
        i += 1
```

**作用**：OCR/抽字把一行拆成很多碎 box，按「同栏 + 同版面块 + y 中心接近」横向合并成整句。

### `_concat_downward`（1111）—— 阅读顺序（当前版本简化为排序）

```python
def _concat_downward(self, concat_between_pages=True):
    self.boxes = Recognizer.sort_Y_firstly(self.boxes, 0)   # ★ 当前实现：Y 优先排序即完成
    return
    # ↓ 以下 xgboost 判断"上下两段该不该拼"的逻辑当前版本已不执行（短路径返回）
```

**学习点**：源码里 `sort_Y_firstly` 之后直接 `return`，后面 100 行的 **xgboost 上下行拼接模型**（`updown_cnt_mdl`）是**历史遗留的死代码**——模型还在 `__init__` 里加载，但拼接路径已不再走它。这是大项目常态：**加载了但不再用的模型**。读代码时遇到 `return` 后的长块要认出来是死代码。

---

## 六、步骤⑧ `_filter_forpages` —— 过滤封面/目录（pdf_parser.py:1215）

```python
def _filter_forpages(self):
    # ① 找"目录/contents/致谢/acknowledge"页，连同其后的列表一起删
    #    目录页的条目通常以"第X章/1.2.3"开头 → 匹配前缀删掉整段目录
    # ② 兜底：找不到目录关键词时，统计每页"····"（目录点线）数量 >3 的页 → 判定为目录页删掉
    page_dirty = [0]*len(self.page_images)
    for b in self.boxes:
        if re.search(r"(··|··|··)", b["text"]):     # 目录的引导点线
            page_dirty[b["page_number"]-1] += 1
    page_dirty = set([i+1 for i,t in enumerate(page_dirty) if t>3])
```

**作用**：封面、目录、致谢页对检索没有价值（目录会被当成正文读进知识库），直接滤掉。**两种策略双保险**：识别关键词 + 识别目录点线特征。

---

## 七、步骤⑨ `_extract_table_figure` —— 抽表格抽图 + 配标题（pdf_parser.py:1287）

```python
def _extract_table_figure(self, need_image, ZM, return_html, need_position, separate_tables_figures=False):
    # ① 从 box 流里把 table / figure 类型的 box"抠"出来，分别归组
    while i < len(self.boxes):
        lout_no = str(b["page_number"]) + "-" + str(b["layoutno"])
        if self.boxes[i]["layout_type"] == "table":
            if re.match(r"(数据|资料|图表)*来源[:： ]", b["text"]):   # "资料来源：xxx" 不算表正文
                self.boxes.pop(i); continue
            tables[lout_no].append(self.boxes[i])    # 同一版面块的多行归到同一张表
            self.boxes.pop(i)
        if need_image and b["layout_type"] == "figure":
            figures[lout_no].append(self.boxes[i]); self.boxes.pop(i)
        i += 1

    # ② 跨页合并：同一张表被切到两页时（相邻页 + 距离近）拼回一张
    for k0, bxs0 in ...:
        if bxs[0]["page_number"] - bxs0[0]["page_number"] > 1: continue  # 只合并相邻页
        if self._y_dis(bxs0[-1], bxs[0]) > mh*23: continue
        tables[k0].extend(tables[k]); del tables[k]

    # ③ ★ 标题匹配：把 "表 1" / "Figure 3" 标题 box 用最近距离归到最近的表格/图
    for c in self.boxes:
        if not TableStructureRecognizer.is_caption(c): continue      # 正则：表/图/Figure/Table 开头
        tk, tv = nearest(tables); fk, fv = nearest(figures)          # 欧氏距离取最近
        if tv < fv and tk: tables[tk].insert(0, c)                   # 表标题插到表格最前
        elif fk: figures[fk].insert(0, c)
        self.boxes.pop(i)

    # ④ ★ 裁图 + 重建表格结构
    for k, bxs in tables.items():
        img = cropout(bxs, "table", poss)                             # 按版面 box 裁出表格图
        res.append((img, self.tbl_det.construct_table(bxs, html=return_html, is_english=self.is_english)))
        #                      ↑ TSR 把带 R/H/C/SP 标签的 box 重建为 HTML 表格 / JSON
```

**作用（关键）**：
- **表格/图片从正文里独立出来**：正文文本流、表格图、图片各走各路——下游 Chunker 可以把表格当"结构化内容"处理，而不是当纯文本。
- **标题配对**：`is_caption`（"表 1-2" / "Figure 3" / "Table 1" 正则）→ 最近距离归到最近的表/图 → **Chunker 给表格图配标题上下文**（主干④的"表格上下文"来源）。
- **`construct_table`**：用 R/H/C/SP 标签把表格重建为 HTML 表格——这是"表格能被 LLM 读"的关键（HTML 表格比纯文本好读一个量级）。

`cropout`（1386）：按版面 box 裁图，跨页的表**拼成一张竖图**（白底 `(245,245,245)` 拼接）。

---

## 八、步骤⑩ `__filterout_scraps` —— 滤噪声（pdf_parser.py:1537）

```python
def __filterout_scraps(self, boxes, ZM):
    def usefull(b):
        if b.get("layout_type"): return True                     # 有版面类型（标题/表格等）= 保留
        if width(b) > self.page_images[p-1].size[0]/ZM/3: return True  # 宽于页宽 1/3 = 正文行
        if b["bottom"]-b["top"] > self.mean_height[p-1]: return True   # 高于行高 = 保留
        return False                                             # 否则 = 孤字/噪点
    # 从每个"有用"box 出发做 DFS，把同行/同段的内容收成一行，拼上位置标签
    res.append("\n".join([c["text"] + self._line_tag(c, ZM) for c in lines]))
    return "\n\n".join(res)
```

**作用**：页面边角残留的页码、页眉碎片、孤立字符会被滤掉，只留"有版面类型 / 够宽 / 够高"的有用块。每行文本末尾附 `_line_tag`（位置标签）。

---

## 九、批量路径 `parse_into_bboxes` —— 大 PDF 按页分窗（pdf_parser.py:1771）

全量路径 `__call__` 一次把整本 PDF 渲染进内存——**几百页的 PDF 会爆内存**。批量路径按页分窗：

```python
def parse_into_bboxes(self, fnm, callback=None, zoomin=3, from_page=0, to_page=MAXIMUM_PAGE_NUMBER):
    batch_size = max(1, int(os.getenv("PDF_PARSER_PAGE_BATCH_SIZE", "50")))  # 每窗 50 页，可配
    if effective_to_page - from_page <= batch_size:
        # 页数少 → 直接走全量
        return self._parse_loaded_window_into_bboxes(zoomin, callback=callback)
    # 页数多 → 分批：每窗只渲染 50 页 → 解析 → 把坐标平移回全局
    for page_from in range(from_page, effective_to_page, batch_size):
        self.__images__(fnm, zoomin, page_from=page_from, page_to=page_to, callback=None)
        chunk_boxes = self._parse_loaded_window_into_bboxes(zoomin)
        all_boxes.extend(self._to_global_boxes(chunk_boxes))    # ★ 窗口内坐标 → 全局坐标
        callback(...)                                           # 进度回调
    return all_boxes
```

```python
def _parse_loaded_window_into_bboxes(self, zoomin=3, callback=None):
    self._layouts_rec(zoomin);            callback(0.63, "Layout analysis")
    self._table_transformer_job(zoomin, auto_rotate=...);  callback(0.83, "Table analysis")
    self._text_merge(); self._concat_downward(); self._naive_vertical_merge(zoomin)
                                          callback(0.92, "Text merged")
    tbls, figs = self._extract_table_figure(True, zoomin, True, True, True)  # 表格/图单独返回
    # ★ 把表格/图作为"box"插回正文流的正确位置（最近矩形距离找插入点）
    insert_table_figures(tbls, "table")
    insert_table_figures(figs, "figure")
    for b in self.boxes:
        b["position_tag"] = self._line_tag(b, zoomin)          # 位置标签 @@页码\tx y w h##
        b["image"] = self.crop(b["position_tag"], zoomin)      # 每个 box 裁出对应图片
        b["positions"] = [pos for pos in extract_positions(b["position_tag"])]
    return deepcopy(self.boxes)
```

**作用**：
- **内存可控**：`PDF_PARSER_PAGE_BATCH_SIZE`（默认 50 页）一窗一窗解析，`_to_global_boxes` 把窗口坐标平移到全局页码。
- **回调式进度**：每个阶段 `callback(0.63/0.83/0.92/1.0)` → 前端进度条"版面分析 63% / 表格分析 83%"（主干③里看到的进度来源）。
- **表格/图以"box"形态插回正文流**：保持阅读顺序，同时保留图片。
- **`position_tag`**：`@@页码\tx0 y0 x1 y1##` 格式的位置标签随文本一起返回 → 前端"引用高亮 + 点开看原文"的数据基础。

---

## 十、`crop` —— 按位置裁图 + 上下文留白（pdf_parser.py:1946）

```python
def crop(self, text, ZM=3, need_position=False):
    poss = self.extract_positions(text)      # 解析位置标签
    # ★ 在裁剪区域上下各加 120px 留白 —— 给 chunk 图带上"上文/下文"视觉上下文
    poss.insert(0, ([first_page_idx], pos[1], pos[2], max(0, pos[3]-120), max(pos[3]-GAP, 0)))
    poss.append(([last_page_idx], pos[1], pos[2], min(h, pos[4]+GAP), min(h, pos[4]+120)))
    # 跨页时：本页底部裁 + 下一页顶部裁，拼成一张竖图，留白用半透明黑叠加标记
```

**作用**：每个文本 chunk 都会裁一张"带上下文的图"（上下各多 120px）——这是主干④"媒体 chunk 附加上下文"的视觉部分。

---

## 十一、生产级兜底清单（全篇最值钱的部分）

| 兜底 | 代码位置 | 解决什么 |
|------|---------|---------|
| 乱码检测策略1 | `_is_garbled_text`（282） | pdfplumber 抽出的字是 PUA/CID 乱码 → 整页转 OCR |
| 乱码检测策略2 | `_is_garbled_by_font_encoding`（317） | 子集字体把 CJK 映射成 ASCII 标点 → 转 OCR |
| 空格恢复 | `_insert_word_spaces`（227） | PDF 不写空格、靠字符间隙定位 → 从几何位置补空格（CJK 跳过） |
| 字符级乱码 | `_is_garbled_char`（254） | 单个字符落在私用区/替换符 → OCR 框清空重 OCR |
| OCR 代表不了的语言 | `_ocr_can_represent`（202） | OCR 模型只认 CJK+拉丁，西里尔文页 OCR 只出乱码 → 跳过不硬来 |
| 自动放大重试 | `__images__` 末尾（1741） | OCR 空结果时 zoomin 3→9 重试一次 |
| 全页 OCR 失败兜底 | `_has_color` 过滤 | 只取"有颜色"的字符，滤掉背景水印层 |
| 表格方向校正 | `_evaluate_table_orientation`（367） | 歪表/横表先旋转再识别 |
| 多 GPU 背压 | `parallel_limiter` | 每 GPU 一个信号量，防显存打爆 |
| 目录页过滤 | `_filter_forpages` | 关键词 + 点线特征双策略 |
| 噪声过滤 | `__filterout_scraps` | 页码/页眉残片/孤字 |
| 分窗内存控制 | `parse_into_bboxes` | 大 PDF 按页批处理 |

**核心心法**：**文档解析 90% 的工作是"兜底"**。抽字抽不动 → OCR；OCR 出了乱码 → 清空重来；重来不行 → 放大分辨率。**每一层都假设上层会失败**。

---

## 十二、对照 ai_assistant

| RAGFlow | 你的 ai_assistant | 差距 |
|---------|------------------|------|
| PDF 渲染 + OCR + 版面分析 | 用 pdf 库直接抽文本 | ⚠️ 扫描件/图片型 PDF 读不出来 |
| 版面分类（标题/表格/图/正文） | 不区分，全当正文 | ⚠️ 双栏乱序、标题不识别 |
| 表格结构化（R/H/C + HTML 重建） | 表格当纯文本 | ⚠️ 表格 LLM 读不懂 |
| 乱码检测 + OCR 兜底 | 抽到乱码就乱码入库 | ❌ 该加检测 |
| 表格/图片独立 + 配标题 | 图片直接丢 | ❌ 图片知识完全丢失 |
| 位置标签 @@page## | 无 | ❌ 无法引用定位 |

**落地优先级**：
- **P0**：加「乱码检测 → OCR 兜底」——只抽文字层，乱码会无声污染知识库。
- **P1**：版面分析（标题识别）——分块时按标题切，检索质量显著提升。
- **P2**：表格结构化——先从「把表格转成 Markdown 表格」开始（比完整 TSR 简单得多），LLM 立刻能读。

---

## 十三、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 主入口 | `__call__`（1744） | 9 步流水线：渲染→抽字→OCR→版面→表格→合并→拼页→滤封面→抽表抽图→滤噪声 |
| 渲染+抽字 | `__images__`（1608） | 页转图 + 抽字符 + 乱码检测 + 多 GPU OCR |
| 版面分析 | `_layouts_rec`（877） | layout_type 分类 + 全局累计坐标 |
| 分栏 | `_assign_column`（885） | KMeans 自动判栏数（双栏阅读顺序） |
| 表格结构化 | `_table_transformer_job`（470） | 方向校正 + TSR + R/H/C/SP 标签 |
| 文本合并 | `_text_merge`（969） | 同行碎 box 横向合并 |
| 滤封面 | `_filter_forpages`（1215） | 目录/封面/致谢过滤 |
| 抽表抽图 | `_extract_table_figure`（1287） | 表/图独立 + 标题配对 + 跨页合并 |
| 滤噪声 | `__filterout_scraps`（1537） | 孤字/页眉残片过滤 |
| 批量路径 | `parse_into_bboxes`（1771） | 大 PDF 按页分窗 + 坐标平移 + 进度回调 |
| 裁图 | `crop`（1946） | 位置标签 + 带上下文的裁图 |

**一句话心法**：**DeepDoc 把 PDF 当成"排版文档"而不是"文本文件"**——渲染成图、OCR 兜底、版面分类、表格结构化、位置留档，五件事做完，下游 Chunker 和检索拿到的才是"结构化的知识"而不是"一串文字"。这是普通 RAG 和高质 RAG 的分水岭。
