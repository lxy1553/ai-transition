# 深挖：rag_tokenizer 分词定制（中文 + 词权重）

> 深挖 05 讲 Tokenizer 组件整体。本篇回答"**RAGFlow 的中文分词器到底是什么、和 jieba 差在哪、词权重怎么算**"。
> 核心认知：**分词器不是 jieba，而是 datrie（双数组 Trie）自研的「HUQIE」分词器**——词典 `huqie.txt`（55 万行，沿 jieba 的「词 频率 词性」格式）构建成 `.trie` 缓存；粗/细两档 token 对应 `content_ltks`/`content_sm_ltks`，检索时粗档 boost 2、细档 boost 1。
> ⚠️ 两个纠偏：`rag/nlp/rag_tokenizer.py` 只是 60 行薄封装，真身在 `infinity-sdk` 包内（`infinity/rag_tokenizer.py`，648 行）；`tokenize_and_ws` 当前版本不存在（旧版 `content_lws` 已移除，权重改为查询期 `term_weight` 现算）。
> 分词器**本身没有停用词表、没有权重**——停用词在 `term_weight` 层剔除，权重是 `term_weight.Dealer.weights()` 单独算的。

- 源码位置：`github/project/ragflow/rag/nlp/rag_tokenizer.py`（薄封装）+ `rag/nlp/{__init__,term_weight,query,synonym}.py` + 分词器真身 `infinity/rag_tokenizer.py`（infinity-sdk 0.7.3）
- 上游：深挖 04/05 的 Tokenizer 组件消费 chunk
- 下游：`content_ltks`(粗)/`content_sm_ltks`(细) 进 ES/Infinity 双 analyzer 索引 → 深挖 07_01 混合检索 `词^权重`

---

## 三问

- **Q1 解决什么问题**：中文没有天然空格分词，需要一个词典驱动的、能切出"大词又兜得住小词"的分词器，且要能领域定制。
- **Q2 数据流哪一环**：离线④ 分词与向量化——chunk 文本 → 粗/细两档 token → 索引双 analyzer。
- **Q3 删掉会怎样**：全文检索失效——`content_ltks` 空，混合检索只剩向量一路，召回断崖。

---

## 一、薄封装与真身 —— 双栈复用同一分词器

```python
# rag/nlp/rag_tokenizer.py:17,20,54-60 —— 全部转发给 infinity.rag_tokenizer
import infinity.rag_tokenizer

class RagTokenizer(infinity.rag_tokenizer.RagTokenizer):
    def tokenize(self, line: str) -> str:
        from common import settings
        if settings.DOC_ENGINE_INFINITY:   # Infinity 引擎时透传原文，tokenize 交给 C++ 侧
            return line
        else:
            return super().tokenize(line)

tokenizer = RagTokenizer()
tokenize = tokenizer.tokenize
fine_grained_tokenize = tokenizer.fine_grained_tokenize
tag = tokenizer.tag
freq = tokenizer.freq
```

**真身初始化**（`infinity/rag_tokenizer.py:76-145`）——加载/构建前缀词典 Trie：

```python
def _load_dict(self, fnm):
    ...
    k = self.key_(line[0])                               # key_ = 小写 utf-8 编码串
    F = int(math.log(float(line[1]) / self.DENOMINATOR) + 0.5)   # 频率→对数编码
    self.trie_[k] = (F, line[2])                         # 存 (log频率, 词性tag)
    self.trie_[self.rkey_(line[0])] = 1                  # 反向key，供反向最大匹配
    dict_file_cache = fnm + ".trie"
    self.trie_.save(dict_file_cache)                     # 预编译 .trie 缓存

def __init__(self, debug=False, user_dict=None):
    self.DIR_ = user_dict or 包内 huqie.txt              # 词典
    self.SPLIT_CHAR = r"([ ,\.<>/?;:'\[\]\\`!@#$%^&*\(\)\{\}\|_+=《》，。？、；‘’：“”【】~！￥%……（）——-]+|[a-zA-Z0-9,\.-]+)"
    trie_file_name = self.DIR_ + ".trie"
    if os.path.exists(trie_file_name):
        self.trie_ = datrie.Trie.load(trie_file_name)    # 优先加载 .trie 缓存
    else:
        self.trie_ = datrie.Trie(string.printable)
        self._load_dict(self.DIR_)                       # 否则现场建 Trie
```

**作用**：`RagTokenizer` 薄封装只在 Infinity 引擎下透传（tokenize 交给 C++ 侧），其余走 `infinity-sdk`。真身是 **datrie 前缀词典 + 正/反向最大匹配 + DFS 最优切分**的自研分词器，词典 `huqite.txt`（格式 `金童云商 3 nr`）用对数频率编码进 Trie 并缓存成 `.trie`。**不依赖 jieba，但沿用 jieba 的词典/词性格式**（所以加用户词典零学习成本）。

## 二、`tokenize` vs `fine_grained_tokenize` —— 粗/细两档 ★（rag/nlp/__init__.py:365-372）

```python
def tokenize(d, txt, eng, language="English"):
    from . import rag_tokenizer
    rag_tokenizer.tokenizer.set_language(language)       # 切换英文词干/词形还原器
    d["content_with_weight"] = txt
    t = re.sub(r"</?(table|td|caption|tr|th)( [^<>]{0,12})?>", " ", txt)   # 去表格标签
    d["content_ltks"] = rag_tokenizer.tokenize(t)                          # ← 粗粒度
    d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])  # ← 细粒度
```

**粗 `tokenize`**（`infinity/rag_tokenizer.py:423-492`）——先切段，中文双向最大匹配 + DFS，最后 `merge_` 并大词：

```python
def tokenize(self, line: str) -> str:
    line = re.sub(r"\W+", " ", line); line = self._strQ2B(line).lower(); line = self._tradi2simp(line)
    arr = self._split_by_lang(line)          # 切成 (片段, 是否中文) 对
    for L, lang in arr:
        if not lang:                         # 英文段
            res.extend([self._normalize_token(t) for t in word_tokenize(L)])
            continue
        tks, s = self._max_forward(L); tks1, s1 = self._max_backward(L)   # 正/反向匹配
        ... while 不一致处: self.dfs_(...)   # DFS 枚举所有切分，score_ 打分选最优
    return self.merge_(res)                  # 把拆散的单字/词再并回大词
```

**细 `fine_grained_tokenize`**（`infinity/rag_tokenizer.py:494-532`）——对粗词再 DFS，取**次优切分**得到更小的子词：

```python
def fine_grained_tokenize(self, tks: str) -> str:
    for tk in tks:
        if len(tk) < 3 or re.match(r"[0-9,\.-]+$", tk): res.append(tk); continue
        self.dfs_(tk, 0, [], tkslist)                    # 对该粗词枚举所有切分
        if len(tkslist) < 2: res.append(tk); continue
        stk = self._sort_tokens(tkslist)[1][0]           # 取第 2 优 = 更细的切分
        ...
```

**索引侧两档落库**（`conf/infinity_mapping.json:17` + `rag/utils/infinity_conn.py:117-120`）：

```jsonc
// conf/infinity_mapping.json:17
"content": {"type": "varchar", "analyzer": ["rag-coarse", "rag-fine"],
            "comment": "content_with_weight, content_ltks, content_sm_ltks"}
```
```python
# rag/utils/infinity_conn.py:117-120
elif field == "content_with_weight" or field == "content_ltks":
    field = "content@ft_content_rag_coarse"   # 粗粒度 → rag-coarse
elif field == "content_sm_ltks":
    field = "content@ft_content_rag_fine"     # 细粒度 → rag-fine
```

**查询加权**（`rag/nlp/query.py:38-39`）：`"content_ltks^2", "content_sm_ltks"` —— **粗档 boost 2、细档 boost 1**。

**作用（关键）**：一次调用产出两档——`tokenize` 尽量合并出"大词"（`content_ltks` → rag-coarse），`fine_grained_tokenize` 把每个大词 DFS 切出次优"小词"（`content_sm_ltks` → rag-fine）。检索时**大词权重高（精确）、小词兜底（召回）**，这是 RAGFlow 召回质量好的地基之一。

## 三、token 带的信息 —— 词形 + 可查词性/频率，权重独立算

`tokenize` 返回**空格分隔的规范化词串**（已小写、简体、英文词干化）；词性/频率不内嵌，用独立 API 查 Trie：

```python
# infinity/rag_tokenizer.py:289-299
def freq(self, tk):
    k = self.key_(tk)
    if k not in self.trie_: return 0
    return int(math.exp(self.trie_[k][0]) * self.DENOMINATOR + 0.5)   # 解码对数频率

def tag(self, tk):
    k = self.key_(tk)
    if k not in self.trie_: return ""
    return self.trie_[k][1]                  # 词性，如 n / nr / d / ns
```

**作用**：词性/频率都来自 `huqie.txt`（第三列词性、第二列频率），对数域编码进 Trie 查询期解码。**权重不在 tokenize 里**，是 `term_weight.Dealer.weights()` 单独算的；位置是 chunk 级 PDF 坐标（`add_positions` → `page_num_int/position_int/top_int`），无 token 级位置。

## 四、term_weight —— 词权重公式，混合检索的 boost 来源 ★（term_weight.py:192-274）

```python
def weights(self, tks, preprocess=True):
    def ner(t):                       # 实体加权
        if num_pattern.match(t): return 2
        if short_letter_pattern.match(t): return 0.01
        if not self.ne or t not in self.ne: return 1
        m = {"toxic":2,"func":1,"corp":3,"loca":3,"sch":3,"stock":3,"firstnm":1}
        return m[self.ne[t]]
    def postag(t):                    # 词性加权
        t = rag_tokenizer.tag(t)
        if t in set(["r","c","d"]): return 0.3     # 代词/连词/副词 → 压低
        if t in set(["ns","nt"]): return 3         # 地名/机构名 → 抬高
        if t in set(["n"]): return 2               # 名词 → 抬高
        if re.match(r"[0-9-]+", t): return 2
        return 1
    def idf(s, N): return math.log10(10 + ((N - s + 0.5) / (s + 0.5)))
    ...
    wts = (0.3*idf1 + 0.7*idf2) * np.array([ner(t)*postag(t) for t in tt])
    tw = list(zip(tt, wts))
    S = np.sum([s for _, s in tw])
    return [(t, s/S) for t, s in tw]   # ★ 归一化到和为 1
```

**怎么进检索**（`rag/nlp/query.py:30,65,78`）：

```python
self.tw = term_weight.Dealer()                    # query.py:30
tks_w = self.tw.weights(tks, preprocess=False)    # query.py:65
q = ["({}^{:.4f}".format(tk, w) + " {})".format(syn) ...]   # query.py:78 → "词^权重" 查询串
```

**作用（关键）**：权重 = `(0.3·idf(freq) + 0.7·idf(df)) × 实体权重 × 词性权重`，归一化到和为 1。在混合检索里直接拼成 `词^权重` 的关键词 boost（深挖 07_01 的 MatchTextExpr 权重就是它）。词典 `rag/res/ner.json`（股票代码→stock 等实体类型）；`term.freq` 缺失时走 OOV 兜底 `df(t)` + 长英文 OOV 频率先验。

## 五、停用词 / 标点 / CJK 与英文分流

- **标点**：`SPLIT_CHAR` 正则把所有中/英标点当切分符，`re.sub(r"\W+", " ", line)` 先移除非词字符——标点不进词表。
- **停用词**：分词器**没有**停用词表；`term_weight.py:58-92` 内置中文功能词集合（`"请问","您","你","我","他","是","的","就"...`），在 `pretoken`（129-147）里过滤：

```python
for t in rag_tokenizer.tokenize(txt).split():
    if (stpwd and tk in self.stop_words) or (re.match(r"[0-9]$", tk) and not num):
        continue
```

- **CJK vs 英文分流**（`_split_by_lang`，400-421）：切成"中文段/非中文段"对——中文段走 datrie 词典切分（正/反向最大匹配 + DFS），英文段走 NLTK `word_tokenize` + `_normalize_token`（先 WordNet lemmatize 再 Snowball stem）。`set_language`（158-188）切换 SnowballStemmer；WordNet 词形还原只对英文启用。

## 六、预分词与领域词典增强 ★

**预分词** `pretoken`（129-147）+ `token_merge`（149-174）：正则清洗 → 滤停用词/尾部数字 → 标点 token 置 `#` → 相邻单字词并成短语（如 `多 工位` → 长词项），供查询分词用。

**领域词典增强** —— 分词器原生支持用户词典（huqie 格式：词\t频率\t词性），增量并入 Trie：

```python
# infinity/rag_tokenizer.py:147-156
def load_user_dict(self, fnm):
    try:
        self.trie_ = datrie.Trie.load(fnm + ".trie"); return
    except Exception:
        self.trie_ = datrie.Trie(string.printable)
    self._load_dict(fnm)

def add_user_dict(self, fnm):
    self._load_dict(fnm)          # 直接增量并入现有 Trie
```

**同义词扩展**（`rag/nlp/synonym.py:79-101`）：优先查 `rag/res/synonym.json`，纯英文回退 NLTK WordNet；查询侧 `FulltextQueryer.syn`（query.py:31）对关键词做同义扩展。

**作用**：领域定制三条路——**用户词典**（`RagTokenizer(user_dict=...)`/`add_user_dict()` 并进 Trie）、**同义词表**（synonym.json + WordNet）、**停用词**（term_weight 内置集合）。中文团队落地自己分词时，加行业词典是最直接的招。

---

## 七、数据流示意

```
文本 "南京市长江大桥是南京的标志性建筑"
 │  rag/nlp/__init__.py:365  tokenize(d, txt, eng, language)
 ├─ set_language(language)                    # 切换 Snowball/WordNet
 ├─ content_with_weight = 原文
 ├─ 去<table>标签 → 空格
 ├─ content_ltks = rag_tokenizer.tokenize(t)      ◄─ 粗粒度 (rag-coarse)
 │     去\W标点 → 全角转半角 → 小写 → 繁转简
 │     _split_by_lang → 中文段: datrie正/反向最大匹配 + DFS最优 + merge_并大词
 │                    英文段: word_tokenize → lemmatize → Snowball stem
 └─ content_sm_ltks = fine_grained_tokenize(content_ltks)  ◄─ 细粒度 (rag-fine)
       对 len≥3 粗词再 DFS，取次优切分 → 更小子词
 │
 ▼ 索引侧  (conf/infinity_mapping.json:17 + infinity_conn.py:117-120)
 content@ft_content_rag_coarse  ← content_ltks       (查询 boost ^2)
 content@ft_content_rag_fine    ← content_sm_ltks    (查询 boost ^1)
 │
 ▼ 查询侧  (rag/nlp/query.py FulltextQueryer)
 查询文本 → rag_tokenizer.tokenize 切词
         → term_weight.Dealer.weights()   (0.3·idf(freq)+0.7·idf(df)) × ner × postag → 归一化
         → 拼 "词^权重" → synonym.lookup() 同义扩展
         → MatchTextExpr(["title_tks^10","content_ltks^2","content_sm_ltks",...], q)
             = 关键词权重混合检索（权重 = 查询 boost）
```

---

## 八、对照 ai_assistant

| RAGFlow | 你的 ai_assistant | 差距 |
|---------|------------------|------|
| datrie 自研分词器（双数组 Trie） | jieba | ⚠️ jieba 速度/词典可控性一般 |
| 粗/细两档 + 双 analyzer | 单档 | ⚠️ 召回兜底缺失 |
| 粗 ^2 / 细 ^1 加权 | 无 | ⚠️ 大词不突出 |
| `term_weight` IDF×实体×词性 | 无权重 | ⚠️ 关键词平分秋色 |
| 用户词典增量并入 Trie | jieba.load_userdict | 概念同构 |
| 同义词扩展 synonym.json+WordNet | 无 | ⚠️ 查询改写单一 |
| 停用词在权重层剔除 | 无/简单 | 概念参考 |

**落地优先级**：
- **P0**：**粗/细两档**——大词进主字段（高权重），子词进兜底字段。jieba 也能做（`jieba.cut` 全模式 vs 精确模式），双 analyzer 索引。
- **P1**：**词权重**——IDF×词性（地名/机构名抬高、代词/副词压低），检索时 `词^权重`。
- **P2**：用户词典 + 同义词表 + 停用词表统一定制（行业落地最直接）。

---

## 九、总结

| 环节 | 代码 | 作用 |
|------|------|------|
| 薄封装 | `rag_tokenizer.py:17` | 转发/Infinity 透传 |
| 词典构建 | `_load_dict`（inf:76） | huqie.txt → datrie .trie 缓存 |
| 粗分词 | `tokenize`（inf:423） | 正/反向匹配 + DFS + merge_ |
| 细分词 | `fine_grained_tokenize`（inf:494） | 取次优切分 → 子词 |
| 两档入口 | `rag/nlp/__init__.py:365` | content_ltks / content_sm_ltks |
| 双 analyzer | `infinity_mapping.json:17` | rag-coarse / rag-fine |
| 权重 | `term_weight.py:192` | (0.3·idf+0.7·idf)×ner×postag |
| 停用词 | `term_weight.py:58` | 功能词集合过滤 |
| 用户词典 | `load_user_dict`/`add_user_dict` | huqie 格式增量并入 |
| 同义词 | `synonym.py:79` | synonym.json + WordNet |

**一句话心法**：**RAGFlow 的分词 = 词典 Trie（粗）+ 次优切分（细）+ 查询期权重**。真身是 datrie 自研分词器而非 jieba，但沿 jieba 的词典格式让人零成本定制；精髓是"**粗档保精确、细档保召回、权重放大关键实体**"——分词不是拿 jieba 一 cut 完事，而是按"大词/小词/权重"三层设计。
