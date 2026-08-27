# 深挖：LayoutRecognizer 版面分析器（deepdoc/vision/layout_recognizer.py）

> 这是主干③/深挖03_01里 `_layouts_rec` 调用的那个 **layout 模型**——它回答"每个文字框是标题还是正文还是表格"。
> 从「页面图像」到「带 `layout_type`/`layoutno` 的 box 列表」，中间是 **ONNX 检测模型 + 坐标打标**两步。
> 本文件拆 `LayoutRecognizer` 内部：模型加载 → 批量推理 → 后处理 → 版面打标 → 垃圾过滤，外加 YOLOv10 / 昇腾两个变体。

- 源码位置：`github/project/ragflow/deepdoc/vision/layout_recognizer.py` + 基类 `deepdoc/vision/recognizer.py`
- 上游：深挖 03_01 里 `RAGFlowPdfParser._layouts_rec`（pdf_parser.py:877）调 `self.layouter(self.page_images, self.boxes, ZM, drop=drop)`
- 三变体：`LayoutRecognizer`（onnx）｜`LayoutRecognizer4YOLOv10`（YOLOv10）｜`AscendLayoutRecognizer`（昇腾 `.om`）

---

## 三问

- **Q1 解决什么问题**：OCR/抽字得到的是"一串文字框"，但不知道谁是谁——是标题、正文、表格、图、还是页眉页脚。版面分析给每个框打类别，下游才知道"表格交给表格识别、图裁成图、标题做分块锚点"。
- **Q2 数据流哪一环**：解析链路中间——上游 `__images__` 产出 OCR 框，这里打版面标签，下游 `_table_transformer_job`/`_text_merge`/`_extract_table_figure` 消费。
- **Q3 删掉会怎样**：所有框都是一个类别 → 表格当正文读、页眉页脚进知识库、图无法识别、双栏阅读顺序乱——解析质量回到"普通 RAG"。

---

## 一、模型加载 —— `layout.onnx` + ORT 会话 + 全局缓存

`LayoutRecognizer.__init__`（layout_recognizer.py:48-66）：

```python
labels = ["_background_", "Text", "Title", "Figure", "Figure caption",
          "Table", "Table caption", "Header", "Footer", "Reference", "Equation"]

def __init__(self, domain):
    self.garbage_layouts = ["footer", "header", "reference"]   # ★ 垃圾版面类别
    # ① 支持远程 DLA 服务（环境变量 DEEPDOC_URL / TENSORRT_DLA_SVR）→ 不走本地模型
    dla_url = os.environ.get("DEEPDOC_URL") or os.environ.get("TENSORRT_DLA_SVR")
    if dla_url:
        self.client = DLAClient(dla_url); return
    # ② 优先本地模型，失败回退 HuggingFace 下载
    try:
        model_dir = os.path.join(get_project_base_directory(), "rag/res/deepdoc")
        super().__init__(self.labels, domain, model_dir)
    except Exception:
        model_dir = snapshot_download(repo_id="InfiniFlow/deepdoc",
            local_dir=os.path.join(get_project_base_directory(), "rag/res/deepdoc"))
        super().__init__(self.labels, domain, model_dir)
```

实际 ONNX 会话加载在基类 `Recognizer.__init__`（recognizer.py:33-51）→ `load_model`（ocr.py:70-126）：

```python
self.ort_sess, self.run_options = load_model(model_dir, task_name)  # task_name="layout"
self.input_names  = [node.name for node in self.ort_sess.get_inputs()]
self.output_names = [node.name for node in self.ort_sess.get_outputs()]
self.input_shape  = self.ort_sess.get_inputs()[0].shape[2:4]  # 模型输入 H×W
```

```python
# ocr.py load_model 核心
# ① 拼路径 <model_dir>/layout.onnx → onnxruntime.InferenceSession
# ② CUDA 可用 → CUDAExecutionProvider（带 gpu_mem_limit 等选项），否则 CPUExecutionProvider
# ③ 模块级 loaded_models 字典缓存已加载 session（同一模型不重复加载）
```

**作用**：**11 个版面类别**（Text/Title/Figure/Table/.../Equation），模型文件 `rag/res/deepdoc/layout.onnx`。远程 DLA 服务 / 本地 / HF 下载三级回退，ORT 会话全局缓存。

---

## 二、推理主入口 `__call__` —— 批量 ONNX + 版面打标（layout_recognizer.py:68）

分两层：**① 基类 `Recognizer.__call__` 批量推理出 raw 版面框；② 对每个 OCR box 与版面框做重叠匹配、打标签**。

```python
def __call__(self, image_list, ocr_res, scale_factor=3, thr=0.2, batch_size=16, drop=True):
    # ① 批量 ONNX 推理：每页图像 → raw 版面框列表（基类实现）
    layouts = super().__call__(image_list, thr, batch_size)
    boxes = []
    page_layout = []
    for pn, lts in enumerate(layouts):
        bxs = ocr_res[pn]                       # 这一页的 OCR 文本框
        # ② raw 版面框 → 版面对象：坐标除以 scale_factor 还原到原图尺度
        lts = [
            {
                "type": b["type"], "score": float(b["score"]),
                "x0": b["bbox"][0]/scale_factor, "x1": b["bbox"][2]/scale_factor,
                "top": b["bbox"][1]/scale_factor, "bottom": b["bbox"][-1]/scale_factor,
                "page_number": pn,
            }
            for b in self._filter_garbage_layouts(lts)   # 先滤低分垃圾框
        ]
        lts = self.sort_Y_firstly(lts, np.mean([lt["bottom"]-lt["top"] for lt in lts]) / 2)  # 阅读序
        lts = self.layouts_cleanup(bxs, lts)    # 去掉同类型重叠框
        page_layout.append(lts)                 # ★ 每页版面对象 → page_layout（下游表格识别用）

        def findLayout(ty):                     # ③ 逐类型把 OCR box 匹配到版面框
            lts_ = [lt for lt in lts if lt["type"] == ty]
            i = 0
            while i < len(bxs):
                ii = self.find_overlapped_with_threshold(bxs[i], lts_, thr=0.4)  # IoU>0.4 才算命中
                if ii is None:
                    bxs[i]["layout_type"] = ""  # 匹配不到版面 = 未分类
                    i += 1; continue
                lts_[ii]["visited"] = True
                keep_feats = [                 # ★ 反例：footer 在页 90% 以下、header 在页 10% 以上
                    lts_[ii]["type"] == "footer" and bxs[i]["bottom"] < image_list[pn].size[1] * 0.9 / scale_factor,
                    lts_[ii]["type"] == "header" and bxs[i]["top"] > image_list[pn].size[1] * 0.1 / scale_factor,
                ]
                if drop and lts_[ii]["type"] in self.garbage_layouts and not any(keep_feats):
                    garbages[lts_[ii]["type"]].append(bxs[i]["text"])  # 垃圾文本收集
                    bxs.pop(i); continue        # ★ drop=True → 页眉页脚/参考文献直接删
                bxs[i]["layoutno"] = f"{ty}-{ii}"                      # 版面块号：如 "text-3"
                bxs[i]["layout_type"] = lts_[ii]["type"] if lts_[ii]["type"] != "equation" else "figure"
                i += 1

        for lt in ["footer", "header", "reference", "figure caption", "table caption",
                   "title", "table", "text", "figure", "equation"]:    # 按优先级逐类打标
            findLayout(lt)

        # ④ 无文字的 figure/equation 版面 → 补占位 box（下游要裁图）
        for ty in ["figure", "equation"]:
            for i, lt in enumerate([lt for lt in lts if lt["type"] == ty]):
                if lt.get("visited"): continue
                lt = deepcopy(lt); lt.pop("type", None); lt["text"] = ""
                lt["layout_type"] = "figure"; lt["layoutno"] = f"{ty}-{i}"
                bxs.append(lt)

        boxes.extend(bxs)
    # ⑤ ★ 跨页垃圾文本去重：同一页眉/页码文本出现 >1 次 → 全局剔除
    for k in garbages.keys():
        garbages[k] = Counter(garbages[k])
        garbag_set |= {g for g, c in garbages[k].items() if c > 1}
    ocr_res = [b for b in ocr_res if b["text"].strip() not in garbag_set]
    return ocr_res, page_layout
```

**关键点**：
1. **打标 = IoU 匹配**：`find_overlapped_with_threshold(box, 版面框, thr=0.4)`——OCR 框与版面框重叠超过阈值才命中，命中的框获得 `layout_type` + `layoutno`。
2. **按优先级逐类型打标**：footer→...→equation 顺序，先到先得，一个 box 只属于一个版面块。
3. **`layoutno` = "类型前缀-序号"**：如 `text-3`、`figure-0`——下游 `_extract_table_figure` 用它把"同一版面块的散行"归成一张表/一幅图（深挖 03_01 里的 `lout_no`）。
4. **占位 box**：版面识别出"这里是图/公式"但没有文字框时，补一个 `text=""` 的 figure box——下游才知道"这里要裁一张图"。

---

## 三、基类批量推理 `Recognizer.__call__` —— preprocess → run → postprocess（recognizer.py:394）

```python
def __call__(self, image_list, thr=0.7, batch_size=16):
    batch_loop_cnt = math.ceil(float(len(images)) / batch_size)
    for i in range(batch_loop_cnt):
        inputs = self.preprocess(batch_image_list)          # ① 预处理
        for ins in inputs:
            bb = self.postprocess(                          # ③ 后处理
                self.ort_sess.run(None, {k: v for k, v in ins.items() if k in self.input_names},
                                  self.run_options)[0],     # ② ONNX 推理
                ins, thr)
            res.append(bb)
```

**预处理**（recognizer.py:271-299）—— 简单 resize 到模型输入尺寸 + 归一化：

```python
hh, ww = self.input_shape
for img in image_list:
    h, w = img.shape[:2]
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(np.array(img).astype("float32"), (ww, hh))
    img /= 255.0
    img = img.transpose(2, 0, 1)                # HWC → CHW
    img = img[np.newaxis, :, :, :].astype(np.float32)
    inputs.append({self.input_names[0]: img,
                   "scale_factor": [w / ww, h / hh]})   # ★ 缩放比，后处理还原坐标用
```

**后处理**（recognizer.py:301-386）—— 置信度过滤 → 类别 argmax → 坐标还原 → NMS：

```python
boxes = np.squeeze(boxes).T
scores = np.max(boxes[:, 4:], axis=1)
boxes = boxes[scores > thr, :]                  # ① 置信度阈值过滤
class_ids = np.argmax(boxes[:, 4:], axis=1)     # ② 每个框的类别
boxes = boxes[:, :4]
input_shape = np.array([inputs["scale_factor"][0], inputs["scale_factor"][1],
                        inputs["scale_factor"][0], inputs["scale_factor"][1]])
boxes = np.multiply(boxes, input_shape, dtype=np.float32)  # ③ 乘缩放比还原原图坐标
boxes = xywh2xyxy(boxes)                        # ④ center-wh → 左上右下
# ⑤ 每类别独立 NMS（iou 阈值 0.2）→ 输出 {type, bbox, score}
```

**作用**：检测模型输出是「中心点+宽高+各类别概率」，后处理还原成「类别 + 原图坐标 + 置信度」。**scale_factor 是关键**——模型输入固定尺寸，输出坐标要乘回缩放比才能和 OCR 框同坐标系。

---

## 四、输出结构 —— boxes + page_layout

| 输出 | 结构 | 用途 |
|------|------|------|
| `boxes`（=ocr_res） | 扁平 OCR 框列表，含 `text`/`x0`/`x1`/`top`/`bottom`/`page_number` + `layout_type`/`layoutno` | 下游文本合并、表格图提取 |
| `page_layout` | 每页版面对象列表：`{type, score, x0, x1, top, bottom, page_number}` | 下游 `_table_transformer_job` 找表格、`_extract_table_figure` 定位 |

`type` 11 类：`_background_` / `text` / `title` / `figure` / `figure caption` / `table` / `table caption` / `header` / `footer` / `reference` / `equation`。

**两个坑**：
- `equation`（公式）统一归并为 `layout_type="figure"`（layoutno 仍是 `equation-N`）——公式和图片走同一条"裁图"路径。
- 匹配不到版面的 box → `layout_type=""`，会落入 `_text_merge` 的"未分类文本"处理。

---

## 五、`drop` 参数 —— 垃圾版面过滤（layout_recognizer.py:120-129 + 170）

```python
self.garbage_layouts = ["footer", "header", "reference"]   # 垃圾类别

def _filter_garbage_layouts(self, boxes, score_thr=0.4):
    """低分的垃圾版面框直接丢弃（置信度不够，别误删正文）"""
    return [b for b in boxes if float(b["score"]) >= score_thr or b["type"] not in self.garbage_layouts]
```

```python
# __call__ 里（findLayout 内）
keep_feats = [
    lts_[ii]["type"] == "footer" and bxs[i]["bottom"] < page_h * 0.9 / scale_factor,
    lts_[ii]["type"] == "header"  and bxs[i]["top"] > page_h * 0.1 / scale_factor,
]
if drop and lts_[ii]["type"] in self.garbage_layouts and not any(keep_feats):
    garbages[lts_[ii]["type"]].append(bxs[i]["text"])
    bxs.pop(i); continue
# 之后跨页：出现次数 >1 的垃圾文本全局剔除
```

**作用**：双层防误删——
- **低分垃圾框**（score<0.4 的 footer/header/reference）直接在版面层丢弃；
- **高分但确实在页眉页脚区**的 OCR 框，`drop=True` 时删除并收集文本，**跨页出现>1次再全局剔除**（页码/页眉这种"每页重复"的文本一次清除）。

**`keep_feats` 是反例保护**：footer 在页面 90% 以下、header 在页面 10% 以上 → 说明它不在典型页眉页脚区（可能是正文里的"脚注块"），**保留**。防止误删正文。

---

## 六、YOLOv10 变体 `LayoutRecognizer4YOLOv10`（layout_recognizer.py:189-263）

只重写 `preprocess`/`postprocess`，复用基类 `__call__` 批量循环。差异：

```python
# 预处理：letterbox 居中填充（不是直接 resize）
img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
img = cv2.copyMakeBorder(img, top, bottom, left, right,
                         cv2.BORDER_CONSTANT, value=(114, 114, 114))   # ★ 114 灰边填充
img /= 255.0; img = img.transpose(2, 0, 1); img = img[np.newaxis, :, :, :].astype(np.float32)
inputs.append({self.input_names[0]: img,
               "scale_factor": [shape[1]/ww, shape[0]/hh, dw, dh]})    # ★ 额外带填充量 dw/dh
```

```python
# 后处理：YOLOv10 原生输出 [N,6]=[x1,y1,x2,y2,score,cls]
thr = 0.08
boxes = np.squeeze(boxes); scores = boxes[:, 4]
boxes = boxes[scores > thr, :]
class_ids = boxes[:, -1].astype(int)          # ★ 类别在最后一列（不用 argmax）
boxes = boxes[:, :4]
boxes[:, 0] -= inputs["scale_factor"][2]; boxes[:, 2] -= inputs["scale_factor"][2]  # ★ 先减 padding
boxes[:, 1] -= inputs["scale_factor"][3]; boxes[:, 3] -= inputs["scale_factor"][3]
boxes = np.multiply(boxes, input_shape, dtype=np.float32)             # 再乘缩放
# 逐类 nms(boxes, scores, 0.45)   ← NMS 阈值 0.45（onnx 版 0.2）
```

**差异总结**：
| | onnx 版 | YOLOv10 版 |
|--|--------|-----------|
| 预处理 | 直接 resize | letterbox 居中 + 114 灰边 |
| 输出格式 | 中心点wh + 各类别概率 | `[x1,y1,x2,y2,score,cls]` |
| 类别 | argmax | 输出自带 cls 列 |
| 坐标还原 | 乘 scale_factor | 先减 padding 再乘缩放 |
| NMS 阈值 | 0.2 | 0.45 |
| 置信度阈值 | 0.2（__call__ 参数） | 固定 0.08 |

---

## 七、昇腾变体 `AscendLayoutRecognizer`（layout_recognizer.py:266-488）

```python
# 推理后端不同：不用 onnxruntime，用 ais_bench InferSession 加载 .om 模型
from ais_bench.infer.interface import InferSession
self.session = InferSession(device_id, model_path)          # rag/res/deepdoc/layout.om
output = self.session.infer(feeds=[ins["image"]], mode="static")[0]
```

**接口不变**（`__call__(image_list, ocr_res, scale_factor, thr, batch_size, drop)` 签名与返回结构一致），只是：
- `__call__` 整体重写，不复用基类（自己分 batch + 单图 infer）；
- 垃圾文本正则更强（额外匹配 `^•+$`、`^数字1-2位(/或of)数字$`、长 URL）；
- 页面高度用 `image_list[pn].shape[0]`（ndarray），onnx 版用 `.size[1]`（PIL）。

**作用**：**同一套下游逻辑，换个推理后端**——昇腾芯片跑 `.om` 离线模型，接口完全兼容。这就是"可插拔"在模型层的体现。

---

## 八、基类排序核心 `sort_Y_firstly`（recognizer.py:53-62）

```python
@staticmethod
def sort_Y_firstly(arr, threshold):
    def cmp(c1, c2):
        diff = c1["top"] - c2["top"]
        if abs(diff) < threshold:           # ★ top 差小于阈值 = 同一阅读行
            diff = c1["x0"] - c2["x0"]      #    → 回退按 x0（同行内从左到右）
        return diff
    return sorted(arr, key=cmp_to_key(cmp))
```

**作用**：**双栏/多栏排序的核心**——先按 `top`（从上到下）；两框 top 差小于阈值（同一行）就按 `x0`（从左到右）。整页就是"从上到下、行内从左到右"的人类阅读序，天然处理左右栏并列排版。调用时阈值 = 版面框平均高度一半（layout_recognizer.py:98）。

配套工具（同一基类）：
- `sort_X_firstly`（64）：先 x 后 y —— 表格列序。
- `overlapped_area`（106）：重叠面积占比。
- `layouts_cleanup`（124）：剔除同类型重叠框。
- `find_overlapped_with_threshold`（254）：二分加速的版面打标匹配（thr=0.4）。

---

## 九、数据流转示意

```
页面图像 (image_list) + OCR 文本框 (ocr_res)
  │
  ▼
LayoutRecognizer.__call__ (layout_recognizer.py:68)
  │  基类 Recognizer.__call__ (recognizer.py:394) —— 按 batch_size=16 分片
  ▼
preprocess (recognizer.py:271 / YOLOv10:212)
  BGR→RGB → resize/letterbox → /255 → HWC→CHW → NCHW (+scale_factor)
  ▼
onnxruntime: ort_sess.run(None, {...}, run_options)  (recognizer.py:411, CUDA/CPU provider)
  ▼
postprocess (recognizer.py:301 / YOLOv10:237)
  置信度过滤 → argmax类别 / 原生cls → ×scale_factor 还原 → xywh2xyxy → 逐类NMS
  ▼
每页 raw 版面框 → /scale_factor → sort_Y_firstly → layouts_cleanup   (layout_recognizer.py:86-99)
  ▼
findLayout 逐类型(footer→header→…→figure→equation) (layout_recognizer.py:135)
  每个 OCR box: find_overlapped_with_threshold(0.4) 匹配版面框
  → 命中: 打 layout_type + layoutno
  → 命中垃圾 且 drop=True: 删除 + 收集文本
  → 未命中: layout_type=""
  ▼
无文字 figure/equation → 补占位 box | 跨页垃圾文本去重 (出现>1次剔除)
  ▼
返回 (boxes=ocr_res, layouts=page_layout)
```

---

## 十、对照 ai_assistant

| RAGFlow | 你的 ai_assistant | 差距 |
|---------|------------------|------|
| LayoutRecognizer（ONNX/YOLO 版面分类） | 无 | ❌ 需要轻量版面分类 |
| 11 类版面：标题/正文/表格/图/页眉页脚 | 全当正文 | ⚠️ 标题识别对分块最关键 |
| drop + 跨页垃圾去重 | 页眉页脚进知识库 | ⚠️ 该过滤 |
| 占位 box（无文字的图/公式） | 图直接丢 | ❌ 图片知识丢失 |
| 双后端可插拔（onnx/昇腾） | 单实现 | 概念参考 |

**落地优先级**：
- **P0**：**标题识别**——这是版面分析里性价比最高的一环。不一定要上完整版面模型，先做一个"字体大小/加粗/居中的标题启发式"或轻量分类，分块质量立刻提升。
- **P1**：页眉页脚过滤——按「顶部/底部固定区域 + 跨页重复文本」两个特征，10 行代码就能去掉大量噪声。
- **P2**：完整版面模型（PaddleOCR 的 PP-Layout / 小 YOLO）——等前两步验证了价值再上。

---

## 十一、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 模型加载 | `__init__` + `load_model` | `layout.onnx` + ORT + 全局缓存 + DLA/HF 回退 |
| 批量推理 | 基类 `__call__`（394） | preprocess → run → postprocess |
| 预处理 | `preprocess`（271） | resize + /255 + CHW + scale_factor |
| 后处理 | `postprocess`（301） | 置信度过滤 + 类别 + 坐标还原 + NMS |
| 版面打标 | `__call__`（68） | IoU 匹配 + layout_type/layoutno + 垃圾过滤 |
| 垃圾过滤 | `drop` + `_filter_garbage_layouts` | 页眉页脚/参考文献删除 + 跨页去重 |
| 阅读序 | `sort_Y_firstly`（53） | Y 优先、同行按 x0——双栏正确顺序 |
| YOLOv10 | `LayoutRecognizer4YOLOv10`（189） | letterbox + 原生 [N,6] 输出 |
| 昇腾 | `AscendLayoutRecognizer`（266） | `.om` + InferSession，接口不变 |

**一句话心法**：**版面分析 = 检测模型（"哪儿有什么"）+ 坐标打标（"文字框属于哪块"）**。检测模型输出 raw 框，靠 scale_factor 还原坐标、靠 IoU 阈值和 OCR 框对齐、靠类型优先级和 drop 规则过滤垃圾——四层加工把"图像里的区域"变成"带语义的文本框"。
