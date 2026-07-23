---
source: learning
source_label: 学习复习计划
category: LLM与AI工程
count: 33
generated: 2026-07-23T15:44:23.593415

---

## 📑 目录

1. [1. RAG 解决了什么问题？（20min）](#1.-rag-解决了什么问题（20min）)
2. [2. 请讲讲RAG 全链路详解：从文档到问答中的RAG 的核心步骤（1.5h）](#2.-请讲讲rag-全链路详解：从文档到问答中的rag-的核心步骤（1.5h）)
3. [3. 请讲讲RAG 全链路详解：从文档到问答中的要求](#3.-请讲讲rag-全链路详解：从文档到问答中的要求)
4. [4. 请讲讲RAG 全链路详解：从文档到问答中的动手练习：构建一个最小 RAG 系统（1.5h）](#4.-请讲讲rag-全链路详解：从文档到问答中的动手练习：构建一个最小-rag-系统（1.5h）)
5. [5. 请讲讲RAG 全链路详解：从文档到问答中的RAG 的常见陷阱](#5.-请讲讲rag-全链路详解：从文档到问答中的rag-的常见陷阱)
6. [6. 请讲讲featureservice 和 ruleengine 作为依赖注入中的FastAPI 的核心特性](#6.-请讲讲featureservice-和-ruleengine-作为依赖注入中的fastapi-的核心特性)
7. [7. 请讲讲featureservice 和 ruleengine 作为依赖注入中的在 AI/ML 系统中的具体作用](#7.-请讲讲featureservice-和-ruleengine-作为依赖注入中的在-ai/ml-系统中的具体作用)
8. [8. 为什么选 FastAPI 而不是 Flask？](#8.-为什么选-fastapi-而不是-flask)
9. [9. 什么是向量数据库？（20min）](#9.-什么是向量数据库（20min）)
10. [10. 请说说主流向量数据库对比（15min）](#10.-请说说主流向量数据库对比（15min）)
11. [11. 请详细讲解核心概念与原理（40min）](#11.-请详细讲解核心概念与原理（40min）)
12. [12. 请举例说明动手实战：用 Chroma 搭建 RAG 知识库（1h）如何实现？](#12.-请举例说明动手实战：用-chroma-搭建-rag-知识库（1h）如何实现)
13. [13. 请讲讲向量数据库：从概念到实战中的进阶：Milvus 生产部署](#13.-请讲讲向量数据库：从概念到实战中的进阶：milvus-生产部署)
14. [14. 面试官问：常见问题你会怎么回答？](#14.-面试官问：常见问题你会怎么回答)
15. [15. 请说说主流 LLM API 对比（15min）](#15.-请说说主流-llm-api-对比（15min）)
16. [16. 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的API 调用的四种模式（1h）](#16.-请讲讲llm-api-调用：从-prompt-到-function-calling中的api-调用的四种模式（1h）)
17. [17. 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的输出](#17.-请讲讲llm-api-调用：从-prompt-到-function-calling中的输出)
18. [18. 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的Token 管理与成本控制](#18.-请讲讲llm-api-调用：从-prompt-到-function-calling中的token-管理与成本控制)
19. [19. 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的动手练习](#19.-请讲讲llm-api-调用：从-prompt-到-function-calling中的动手练习)
20. [20. 面试官问：常见问题你会怎么回答？](#20.-面试官问：常见问题你会怎么回答)
21. [21. 什么是微调？（20min）](#21.-什么是微调（20min）)
22. [22. 请讲讲PyTorch 微调：从原理到 LoRA中的PyTorch 基础：训练三板斧（40min）](#22.-请讲讲pytorch-微调：从原理到-lora中的pytorch-基础：训练三板斧（40min）)
23. [23. 请讲讲PyTorch 微调：从原理到 LoRA中的LoRA：高效微调（1h）](#23.-请讲讲pytorch-微调：从原理到-lora中的lora：高效微调（1h）)
24. [24. 请说说LoRA 参数选择指南](#24.-请说说lora-参数选择指南)
25. [25. 请讲讲PyTorch 微调：从原理到 LoRA中的动手练习](#25.-请讲讲pytorch-微调：从原理到-lora中的动手练习)
26. [26. 面试官问：常见问题你会怎么回答？](#26.-面试官问：常见问题你会怎么回答)
27. [27. 为什么需要 LangChain（20min）](#27.-为什么需要-langchain（20min）)
28. [28. 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangChain 核心概念（40min）](#28.-请讲讲langchain-/-langgraph：llm-应用开发框架实战中的langchain-核心概念（40min）)
29. [29. 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangGraph：状态机工作流（1h）](#29.-请讲讲langchain-/-langgraph：llm-应用开发框架实战中的langgraph：状态机工作流（1h）)
30. [30. 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangGraph 的进阶功能](#30.-请讲讲langchain-/-langgraph：llm-应用开发框架实战中的langgraph-的进阶功能)
31. [31. 请说说LangChain vs LangGraph 选择指南](#31.-请说说langchain-vs-langgraph-选择指南)
32. [32. 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的动手练习（1h）](#32.-请讲讲langchain-/-langgraph：llm-应用开发框架实战中的动手练习（1h）)
33. [33. 面试官问：常见问题你会怎么回答？](#33.-面试官问：常见问题你会怎么回答)



# 学习复习计划 · LLM与AI工程

> 共 33 题

---

## 1. RAG 解决了什么问题？（20min）

> ID: `L079`

### 1.1 LLM 的三个"不知道"


```text
问题 1: "什么是 night_ops_ratio_30d？"
  LLM 知识截止在训练数据 — 不知道你这个项目的特定概念

问题 2: "截至昨天，各渠道通过率是多少？"
  LLM 不知道实时数据 — 知识库是静态的

问题 3: "user_000042 为什么被拒？"
  LLM 没有企业内部数据的访问权限 — 这是隐私数据

```text
### 1.2 RAG 的解决方案


```text
用户提问
  │
  ▼
┌─────────────────┐
│  1. 检索阶段      │  ← 从知识库中找出最相关的文档片段
│  向量搜索          │
│  Top-K 检索        │
└────────┬────────┘
         │  "相关文档片段"
         ▼
┌─────────────────┐
│  2. 增强阶段      │  ← 把检索结果 + 用户问题 拼成 Prompt
│  Prompt 构造       │
│  Context 注入      │
└────────┬────────┘
         │  "完整 Prompt"
         ▼
┌─────────────────┐
│  3. 生成阶段      │  ← LLM 基于 Context 回答问题
│  LLM 回答         │
│  引用来源          │
└─────────────────┘

```text

---

---

## 2. 请讲讲RAG 全链路详解：从文档到问答中的RAG 的核心步骤（1.5h）

> ID: `L080`

### 2.1 文档切片（Chunking）— 最重要但最容易被忽略


```python
# 为什么切片策略比向量模型更重要？

# 错误做法: 按固定长度切（500字一刀）
# 正文: "特征分为三类: 申请画像、行为衍生、还款表现。
#        申请画像包括 apply_amount_avg, monthly_income..."
# 切片1: "特征分为三类: 申请画像、行为衍生、还款表现。申请画像包括"
# 切片2: "apply_amount_avg, monthly_income..."
# ❌ 检索到切片2 → LLM 不知道这是"申请画像"的一部分 → 回答不完整

# 正确做法: 按语义边界切
# YAML: 每个顶级 key 一个 chunk
# SQL:  每个 CREATE TABLE 一个 chunk
# MD:   每个 ## 标题一个 chunk

```text
**不同文档类型的切片策略**：


```python
def chunk_document(file_path: str) -> list[dict]:
    """根据文件类型选择不同的切片策略"""
    if file_path.endswith('.yaml'):
        # YAML: 按顶级 key 切
        with open(file_path) as f:
            data = yaml.safe_load(f)
        return [
            {"text": yaml.dump({k: v}), "metadata": {"key": k, "source": file_path}}
            for k, v in data.items()
        ]

    elif file_path.endswith('.sql'):
        # SQL: 按 CREATE TABLE 切
        with open(file_path) as f:
            content = f.read()
        stmts = [s.strip() for s in content.split(';') if 'CREATE TABLE' in s]
        return [
            {"text": s, "metadata": {"type": "ddl", "source": file_path}}
            for s in stmts
        ]

    elif file_path.endswith('.md'):
        # Markdown: 按 ## 标题切
        with open(file_path) as f:
            content = f.read()
        chunks = re.split(r'\n## ', content)
        return [
            {"text": f"## {chunk}", "metadata": {"source": file_path}}
            for chunk in chunks if chunk.strip()
        ]

    else:
        # 其他: 按段落切（每段至少 100 字）
        ...

```text
### 2.2 向量化（Embedding）


```python
def embed_chunks(chunks: list[dict], embedding_model: str = "text-embedding-3-small"):
    """
    将文本片段转为向量。

    为什么向量？因为文本不能直接做相似度搜索。
    向量化的目标是: 语义相近的文本 → 向量距离近 → 检索准确

    三种选择:
    1. OpenAI text-embedding-3-small  — 性价比最高, 1536 维
    2. BAAI/bge-large-zh              — 中文场景最强开源
    3. text-embedding-3-large         — 精度最高, 3072 维
    """
    import openai

    texts = [chunk["text"] for chunk in chunks]
    response = openai.embeddings.create(
        model=embedding_model,
        input=texts
    )
    embeddings = [item.embedding for item in response.data]

    # 每个 chunk 带上 embedding 和 metadata
    for i, chunk in enumerate(chunks):
        chunk["embedding"] = embeddings[i]

    return chunks

```text
### 2.3 向量检索（Similarity Search）


```python
import numpy as np

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度 — 衡量两个向量的方向一致性"""
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search(query: str, chunk_embeddings: list[dict],
           query_embedding_model: str = "text-embedding-3-small", k: int = 3):
    """
    检索最相关的 K 个文档片段。

    Step 1: 用户问题 → 向量
    Step 2: 向量 vs 所有 chunk → 算相似度
    Step 3: 排序 → 取 Top-K

    为什么用余弦相似度不是欧氏距离？
    余弦: 只关心方向 — 适合检索语义相似的文本
    欧氏: 关心距离 — 不适合高维向量（维度灾难）
    """
    # Step 1: 用户问题向量化
    query_vector = embed_chunks([{"text": query}])

    # Step 2: 算相似度
    results = []
    for chunk in chunk_embeddings:
        score = cosine_similarity(query_vector, chunk["embedding"])
        results.append({"text": chunk["text"], "score": score,
                        "metadata": chunk.get("metadata", {})})

    # Step 3: 取 Top-K
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]

```text
### 2.4 Prompt 构造 + LLM 回答


```python
def build_rag_prompt(query: str, retrieved_chunks: list[dict]) -> str:
    """构造 RAG 的 Prompt — 把检索结果作为 Context 注入"""
    context = "\n\n".join(
        f"[来源: {chunk['metadata'].get('source', 'unknown')}]\n{chunk['text']}"
        for chunk in retrieved_chunks
    )

    return f"""请根据以下文档内容回答问题。如果文档中没有相关信息，请明确说"未找到相关信息"。

---

## 3. 请讲讲RAG 全链路详解：从文档到问答中的要求

> ID: `L081`

1. 基于参考文档回答，不要自行编造
2. 引用具体来源（文件名）
3. 如果文档内容不足以回答，说出来"""


def rag_answer(query: str, chunk_embeddings: list[dict]):
    """完整的 RAG 流程: 检索 → 增强 → 生成"""
    # Step 1: 检索 Top-3
    top_chunks = search(query, chunk_embeddings, k=3)

    # Step 2: 构造 Prompt
    prompt = build_rag_prompt(query, top_chunks)

    # Step 3: LLM 生成
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0  # RAG 场景不需要"创意"，需要"精确"
    )

    return response.choices[0].message.content

```text
### 2.5 重排序（Re-ranking）— 进阶优化


```python
# 为什么需要重排序？
# 向量检索的 Top-K 可能有"语义相似但不回答问题"的 chunk
# 重排序用更强的模型（Cross-Encoder）重新打分

def rerank(query: str, candidates: list[dict]) -> list[dict]:
    """
    用 Cross-Encoder 重排序。

    对比:
    向量检索（Bi-Encoder）: 快但浅 — 一次 embedding 全部存储
    重排序（Cross-Encoder）: 慢但准 — 每对(query, chunk)一起过模型
    """
    from sentence_transformers import CrossEncoder

    model = CrossEncoder('BAAI/bge-reranker-v2-m3')

    pairs = [(query, c["text"]) for c in candidates]
    scores = model.predict(pairs)

    for i, c in enumerate(candidates):
        c["rerank_score"] = float(scores[i])

    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    return candidates

```text

---

---

## 4. 请讲讲RAG 全链路详解：从文档到问答中的动手练习：构建一个最小 RAG 系统（1.5h）

> ID: `L082`

```python
"""
练习目标: 为项目的 Schema 文档构建 RAG 查询系统。

知识库: config/schemas/dws_wide_table.yaml
         config/rules/credit_policy.yaml
问题: "night_ops_ratio_30d 超过多少算异常？"

要求:
1. 实现文档切片（按 YAML 顶级 key 切）
2. 实现向量化（可以用 OpenAI API 或 sentence-transformers 本地模型）
3. 实现向量检索（余弦相似度，Top-3）
4. 实现 Prompt 构造 + LLM 回答
5. 验证回答质量
"""

import yaml
import numpy as np

# 这里简化: 用简单的关键词匹配替代向量检索（不需要 API key）
class MiniRAG:
    """最小 RAG 系统 — 用关键词匹配替代向量检索"""

    def __init__(self, docs_dir: str):
        self.chunks = []
        self._load_docs(docs_dir)

    def _load_docs(self, docs_dir):
        """加载 YAML 文档，按顶级 key 切分"""
        from pathlib import Path
        for yaml_file in Path(docs_dir).glob("*.yaml"):
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            for key, value in data.items():
                self.chunks.append({
                    "text": yaml.dump({key: value}),
                    "metadata": {"source": str(yaml_file), "key": key}
                })

    def search(self, query: str, k: int = 3) -> list[dict]:
        """用关键词匹配检索（生产中用向量检索）"""
        query_words = set(query.lower().split())
        scored = []
        for chunk in self.chunks:
            text_lower = chunk["text"].lower()
            # 计算关键词命中数量
            hits = sum(1 for w in query_words if w in text_lower)
            scored.append({"text": chunk["text"], "score": hits,
                           "metadata": chunk["metadata"]})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    def answer(self, query: str) -> str:
        # 1. 检索
        top = self.search(query)

        # 2. 构造 Prompt
        context = "\n\n".join(c["text"] for c in top)
        prompt = f"根据以下文档回答:\n{context}\n\n问题: {query}"

        # 3. 如果是生产环境，这里调用 LLM
        # 演示: 返回检索到的文档作为模拟回答
        return f"检索到 {len(top)} 个相关文档片段:\n\n" + context


# 测试
rag = MiniRAG("credit_risk_control_system/config/schemas")
result = rag.answer("什么是 night_ops_ratio_30d？")
print(result)

```text

---

---

## 5. 请讲讲RAG 全链路详解：从文档到问答中的RAG 的常见陷阱

> ID: `L083`

| 陷阱 | 表现 | 解决方案 |
|------|------|---------|
| 检索了但没用 | LLM 忽略检索结果 | 在 Prompt 里强调"根据文档回答" |
| 切片太碎 | 丢失上下文 | 按语义边界切，500-1000 字 |
| Top-K 太大 | Context 太长，模型丢失重点 | K=3-5，结合 rerank |
| 向量不匹配 | query 和文档语义不对齐 | 用相同的 embedding 模型 |
| 知识库过时 | LLM 回答过时信息 | 定期重建索引 |

---

## 6. 请讲讲feature_service 和 rule_engine 作为依赖注入中的FastAPI 的核心特性

> ID: `L092`

### 1. 极致的性能
FastAPI 底层基于 **Starlette**（Web 框架）和 **Pydantic**（数据校验）。
它的异步能力（async/await）使其性能与 Node.js 和 Go 相当，远超传统 Flask/Django。
在信贷风控这种需要 50ms 级低延迟推理的场景中，异步特性可以保证在等待 Redis 特征查询或远程模型调用时，不阻塞其他请求。

### 2. 自动生成交互式文档
只要定义了 Pydantic 模型和路由，FastAPI 就会自动生成 **Swagger UI** 和 **ReDoc** 两份交互式 API 文档。
开发人员、测试人员、甚至业务方都可以直接在网页上测试接口，极大降低沟通成本。

### 3. 基于类型提示的数据校验
通过 Python 的类型注解（Type Hints），FastAPI 可以在请求进来时自动校验参数类型、范围、格式，并将请求体自动解析为 Pydantic 对象。
这不仅减少了手动写校验代码的繁琐，还提供了编辑器自动补全和静态检查。

### 4. 依赖注入系统
FastAPI 内置了强大的依赖注入机制，可以将数据库连接、模型加载、特征服务客户端等公共依赖，以声明式的方式注入到路由函数中，代码解耦且易于测试。

### 5. 原生支持 WebSocket、后台任务、中间件
这使得它可以胜任实时数据推送、异步日志上报等需求。

---

---

## 7. 请讲讲feature_service 和 rule_engine 作为依赖注入中的在 AI/ML 系统中的具体作用

> ID: `L093`

结合我们之前的信贷风控架构，FastAPI 被用来构建**模型推理服务**和**决策网关**：

### 1. 模型推理 API
它将训练好的模型（评分卡、XGBoost、PyTorch）封装为 RESTful 接口：

```python
from fastapi import FastAPI
from pydantic import BaseModel
import joblib

app = FastAPI()
model = joblib.load("scorecard.pkl")

class LoanRequest(BaseModel):
    age: int
    income: float
    credit_score: int
    # ... 其它特征字段

@app.post("/predict")
async def predict(request: LoanRequest):
    features = [[request.age, request.income, request.credit_score]]
    score = model.predict(features)[0]
    return {"score": float(score), "decision": "PASS" if score > 600 else "REJECT"}

```text
当上游业务系统发起 HTTP 请求时，FastAPI 自动校验字段类型、缺失值，省去大量手工判断。

### 2. 集成特征获取与规则引擎
实际生产推理往往需要先获取在线特征，再过黑名单，然后调用模型。这些逻辑可以通过 FastAPI 的依赖注入优雅组织：

```python
from fastapi import Depends
# feature_service 和 rule_engine 作为依赖注入
@app.post("/credit/apply")
async def apply(
    req: ApplyRequest,
    features = Depends(feature_service),
    rules = Depends(rule_engine)
):
    # 1. 黑名单检查
    if rules.check_blacklist(req.user_id):
        return {"decision": "REJECT", "reason": "命中黑名单"}
    # 2. 获取特征并打分
    feats = await features.get_online(req.user_id)
    score = model.predict(feats)
    # 3. 返回决策
    ...

```text
### 3. 高性能异步处理
在线推理时，服务往往要并发请求多个服务（如 Redis 查用户画像、HTTP 调三方征信），
使用 `async/await` 可以让这些 I/O 操作并发执行，大幅降低单次请求的总耗时。

### 4. 接口文档与团队协作
信贷风控涉及数据、算法、后端、产品等多个角色。
FastAPI 自动生成的文档就是一份“活的接口规范”，所有人都能直观看到需要传哪些参数、参数含义、返回格式，且可以在文档页直接调试。

---

---

## 8. 为什么选 FastAPI 而不是 Flask？

> ID: `L094`

| 维度 | FastAPI | Flask |
|------|---------|-------|
| 异步支持 | 原生 async/await，性能高 | 需额外扩展（gevent/asyncio） |
| 数据校验 | 自动基于 Pydantic，类型安全 | 需手动写校验逻辑或插件 |
| API 文档 | 自动生成 Swagger/ReDoc | 需额外安装 flasgger 等 |
| 性能 | 接近 NodeJS/Go | 同步模型下并发能力受限 |
| 生态 | 完美兼容 Starlette 生态，与 Pydantic、SQLAlchemy 无缝集成 | 庞大但逐渐老旧 |

生产级 AI 应用对**低延迟、高并发、严格的输入输出定义**要求很高，FastAPI 在这些方面是当前 Python 生态的最优解。

---

**一句话**总结**：FastAPI 是现代 Python 构建高性能、类型安全 API 的事实标准，
它在 AI 系统中充当推理网关，通过异步能力、自动校验和文档生成，将模型服务化过程变得极其高效和可靠。**

---

## 9. 什么是向量数据库？（20min）

> ID: `L103`

### 1.1 关系型数据库 vs 向量数据库


```text
关系型数据库 (MySQL/PostgreSQL):
  数据: 结构化数据（行 + 列）
  查询: "SELECT * FROM users WHERE age > 18"
  比较: 精确匹配 / 范围查询

向量数据库 (Milvus/Qdrant/Chroma):
  数据: 向量（float 数组，如 [0.1, 0.2, -0.05, ..., 0.8]）
  查询: "找到和这个向量最相似的 10 个向量"
  比较: 余弦相似度 / 欧氏距离 / 内积

```text
### 1.2 向量数据库解决什么问题？


```text
传统搜索的问题:
  用户搜 "深夜操作多的用户" → MySQL 不知道你在说什么
  SQL 只能处理精确匹配: "WHERE night_ops_ratio > 0.6"

向量搜索:
  "深夜操作多的用户" → embedding → [0.3, 0.1, ...]
  → 在向量库中找相似的文档 → 找到 night_ops_ratio_30d 的定义

核心: 把"语义"变成"向量距离" — 语义相近 → 向量距离近

```text

---

---

## 10. 请说说主流向量数据库对比（15min）

> ID: `L104`

| 数据库 | 部署方式 | 性能 | 适用场景 | 学习成本 |
|--------|---------|------|---------|:-------:|
| **Chroma** | 本地文件 | 入门级 | 开发/原型验证 | ⭐ |
| **Milvus** | 分布式 | ⭐⭐⭐⭐⭐ | 生产环境/百万级+ | ⭐⭐⭐⭐ |
| **Qdrant** | Docker单机/集群 | ⭐⭐⭐⭐ | 中大规模生产 | ⭐⭐ |
| **Weaviate** | Docker | ⭐⭐⭐ | 集成度高的场景 | ⭐⭐⭐ |
| **FAISS (Facebook)** | Python库 | ⭐⭐⭐⭐⭐ | 离线大规模搜索 | ⭐⭐⭐ |
| **Pinecone** | 云托管 | ⭐⭐⭐⭐ | 不想运维的团队 | ⭐ |

---

---

## 11. 请详细讲解**核心概念**与原理（40min）

> ID: `L105`

### 3.1 Embedding 维度


```python
# 不同模型的输出维度对比

模型                    输出维度    一个 100 万条记录的索引
OpenAI text-embedding-3-small   1536    约 6 GB
OpenAI text-embedding-3-large   3072    约 12 GB
BAAI/bge-large-zh               1024    约 4 GB
BERT base                       768     约 3 GB

# 维度越高 → 表达力越强 → 存储和计算越大 → 检索越慢
# 1536 维是当前性价比最高的选择

```text
### 3.2 索引算法


```python
# 精确搜索 vs ANN（近似最近邻）

# 精确搜索（暴力搜索）:
#   O(n) — 每条查询扫描所有 100 万条向量，耗时 ~500ms
#   100% 准确，但太慢

# ANN搜索 (Approximate Nearest Neighbor):
#   O(log n) — 用索引结构加速，耗时 ~5ms
#   99% 准确（可以接受的小误差），快 100 倍

# 常用 ANN 算法:
# IVF (Inverted File Index) — 分桶搜索
# HNSW (Hierarchical Navigable Small World) — 图搜索，最推荐
# PQ (Product Quantization) — 压缩向量，减少存储

```text
### 3.3 HNSW 算法原理（面试常问）


```text
HNSW 像一个"高速公路系统":
Level 3: 只有主要城市之间有高速公路（概括信息）
Level 2: 更多城市 + 高速公路 + 省道
Level 1: 全部道路，精确到街道（详细信息）

搜索过程:
  1. 从 Level 3（概要）开始 → 找到最近的大城市
  2. 下到 Level 2 → 在区域内搜索
  3. 下到 Level 1 → 精确搜索

效果: 100 万条向量，5ms 内找到最近邻

```text

---

---

## 12. 请举例说明动手实战：用 Chroma 搭建 RAG 知识库（1h）如何实现？

> ID: `L106`

### 4.1 安装与初始化


```bash
pip install chromadb sentence-transformers

```text
### 4.2 完整代码


```python
import chromadb
from sentence_transformers import SentenceTransformer
import yaml
from pathlib import Path

class LocalKnowledgeBase:
    """基于 Chroma 的本地知识库"""

    def __init__(self, persist_dir: str = "./knowledge_base"):
        # 使用本地 embedding 模型（不需要 API key）
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

        # 持久化存储 — 下次启动不需要重建
        self.client = chromadb.PersistentClient(path=persist_dir)

        # 创建 collection（类似 MySQL 中的表）
        self.collection = self.client.get_or_create_collection(
            name="credit_risk_docs",
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )

    # ═══ 写入: 文档 → 切片 → embedding → 存储 ═══
    def add_yaml_file(self, file_path: str):
        """
        添加 YAML 文件到知识库。

        切片策略: 按顶级 key 切（每张表/每条规则一个 chunk）
        metadata 包含: 源文件、chunk 名称
        """
        with open(file_path) as f:
            data = yaml.safe_load(f)

        for key, value in data.items():
            text = yaml.dump({key: value})
            embedding = self.embedder.encode(text).tolist()

            self.collection.add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[{"source": str(file_path), "key": key}],
                ids=[f"{Path(file_path).stem}__{key}"]
            )

        print(f"  已添加 {len(data)} 个 chunk 到知识库: {file_path}")

    # ═══ 读取: 问题 → embedding → 向量检索 → Top-K ═══
    def search(self, query: str, k: int = 5) -> list[dict]:
        """
        向量检索 — 核心操作

        query_embedding: 用户的自然语言问题 → embedding
        n_results: 返回多少个最相关的文档片段
        """
        query_embedding = self.embedder.encode(query).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )

        # 格式化返回
        formatted = []
        for i in range(len(results['ids'][0])):
            formatted.append({
                "text": results['documents'][0][i],
                "score": 1 - results['distances'][0][i],  # 余弦距离 → 相似度
                "metadata": results['metadatas'][0][i],
            })
        return formatted


# ═══════════════════════════════════════════
# 使用示例
# ═══════════════════════════════════════════

def build_project_knowledge_base():
    """为项目构建完整的向量知识库"""
    kb = LocalKnowledgeBase()

    # 添加 Schema 文档
    schemas_dir = Path("config/schemas")
    for yaml_file in schemas_dir.glob("*.yaml"):
        kb.add_yaml_file(yaml_file)

    # 添加规则文档
    kb.add_yaml_file("config/rules/credit_policy.yaml")

    return kb


def demo_query():
    kb = build_project_knowledge_base()

    queries = [
        "night_ops_ratio_30d 超过多少算异常？",
        "什么情况下会被拒绝贷款？",
        "on_time_rate 新用户默认值是多少？",
    ]

    for q in queries:
        print(f"\n🔍 查询: {q}")
        results = kb.search(q, k=2)
        for r in results:
            print(f"  [相似度 {r['score']:.3f}] {r['text'][:80]}...")


if __name__ == "__main__":
    demo_query()

```text
### 4.3 查询结果示例


```text
🔍 查询: night_ops_ratio_30d 超过多少算异常？
  [相似度 0.89] type: DOUBLE | 范围: [0.0, 1.0] | >60%→高度可疑
  [相似度 0.72] aggregation: mean(event_time.hour IN [22,23,0,1,2,3,4,5])

🔍 查询: 什么情况下会被拒绝贷款？
  [相似度 0.83] id: BLACKLIST_HIT | condition: user_id_in_blacklist == True
  [相似度 0.76] id: FRAUD_SCORE_HIGH | condition: fraud_score > 0.8

```text

---

---

## 13. 请讲讲向量数据库：从概念到实战中的进阶：Milvus 生产部署

> ID: `L107`

### 5.1 Docker 部署


```bash
# docker-compose.yml
version: '3.5'
services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000

  minio:
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin

  milvus:
    image: milvusdb/milvus:v2.4.0
    depends_on: [etcd, minio]
    ports:
      - "19530:19530"

```text
### 5.2 连接 Milvus


```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

# 连接
connections.connect(host="localhost", port="19530")

# 定义 schema
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
]
schema = CollectionSchema(fields, description="知识库")

# 创建 collection
collection = Collection(name="knowledge_base", schema=schema)

# 创建索引（HNSW）
index_params = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {"M": 16, "efConstruction": 200}
}
collection.create_index(field_name="embedding", index_params=index_params)

```text

---

---

## 14. 面试官问：常见问题你会怎么回答？

> ID: `L108`

### Q1: 向量数据库能替代 MySQL 吗？


```text
不能。它们解决不同的问题:

MySQL: "user_000042 的 on_time_rate 是多少？" → 精确查询 ✅
向量库: "和'深夜高风险'这个概念最相似的文档是？" → 语义搜索 ✅

通常一起用:
  Step 1: 向量库做语义检索（找到相关的知识）
  Step 2: MySQL 做精确查询（找到具体的数据值）
  Step 3: LLM 综合回答

```text
### Q2: 100 万条向量查询需要多快？


```text
硬件: 32GB RAM, 8 核 CPU
算法: HNSW
时间: ~10ms

对比:
  精确搜索: ~500ms（慢 50 倍）
  IVF (100桶): ~30ms
  HNSW: ~5-10ms（最快，推荐）

```text
### Q3: 什么时候需要升级到 Milvus？


```text
Chroma 适合: < 10 万条，单机开发验证
Milvus 适合: > 100 万条，分布式生产
Qdrant 适合: 想用 Docker 解决的中等规模

```text

---

## 15. 请说说主流 LLM API 对比（15min）

> ID: `L109`

### 1.1 国内可用的大模型

| 模型 | API 地址 | 价格（百万 token） | 优势 | 场景 |
|------|---------|:---------------:|------|------|
| **DeepSeek V4** | api.deepseek.com | 输入 0.5元 / 输出 2元 | ⭐ 性价比极高，中文强 | 日常开发 |
| **通义千问 Qwen** | dashscope.aliyun.com | 输入 0.8元 / 输出 2元 | 阿里系集成好 | 企业场景 |
| **GLM-4** | open.bigmodel.cn | 输入 0.1元 / 输出 0.1元 | 最便宜，中文好 | 批量任务 |
| **Claude 3.5** | api.anthropic.com | 输入 3元 / 输出 15元 | 推理最强 | 复杂任务 |
| **GPT-4o** | api.openai.com | 输入 5元 / 输出 20元 | 综合最强 | 关键决策 |
| **DeepSeek R1** | api.deepseek.com | 输入 1元 / 输出 4元 | 推理链超强 | 工程分析 |

---

---

## 16. 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的API 调用的四种模式（1h）

> ID: `L110`

### 模式 1：基础 Prompt 调用


```python
from openai import OpenAI

# DeepSeek 兼容 OpenAI SDK
client = OpenAI(
    api_key="sk-your-key",
    base_url="https://api.deepseek.com"  # 改 base_url 即可切换模型
)

def chat(prompt: str, model: str = "deepseek-chat",
         temperature: float = 0.0) -> str:
    """
    temperature = 0.0 → 确定性输出（适合代码生成、SQL生成）
    temperature = 0.7 → 创意性输出（适合文案、头脑风暴）
    temperature = 1.0 → 高度随机（适合创意写作）
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一位 SQL 专家。"},  # System Prompt
            {"role": "user", "content": prompt},                    # User Message
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content

```text
### 模式 2：流式输出（Streaming）


```python
def chat_stream(prompt: str):
    """
    流式输出: 一个字一个字显示，而不是等全部生成完。

    适用于: 需要实时显示回复的场景（对话机器人、代码生成）
    不适用于: 需要完整结果再做后续处理的场景
    """
    stream = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        stream=True,  # ← 流式模式
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
            # 每次 yield 一小段文本，前端可以实时渲染

# 使用
for text in chat_stream("写一段 SQL 查询最近 7 天的通过率"):
    print(text, end="", flush=True)

```text
### 模式 3：多轮对话


```python
def multi_turn_chat():
    """
    多轮对话: 保留历史消息，让 LLM 理解上下文。

    关键: messages 列表每次增加一条 user 和 assistant 消息
    注意: 消息数越多 → token 消耗越大 → 注意窗口长度
    """
    messages = [
        {"role": "system",
         "content": "你是风控数据仓库的 AI 助手。"}
    ]

    print("开始对话（输入 'q' 退出）")
    while True:
        user_input = input("\n你: ")
        if user_input.lower() == 'q':
            break

        # 添加用户消息
        messages.append({"role": "user", "content": user_input})

        # 调用 LLM
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.0,
        )

        reply = response.choices[0].message.content
        print(f"AI: {reply}")

        # 添加助手回复（用于下一轮对话的上下文）
        messages.append({"role": "assistant", "content": reply})

        # ★ 重要: 控制消息数量
        if len(messages) > 20:  # 超过 10 轮对话
            # 丢弃最早的消息，但保留 system prompt
            messages = [messages[0]] + messages[-19:]

```text
### 模式 4：Function Calling


```python
# ★ Function Calling = 让 LLM 可以调用你的代码函数
# 这是 Agent 架构的基础 — LLM 通过 Function Calling 操作外部系统

# Step 1: 定义工具函数
def query_data_warehouse(sql: str) -> str:
    """执行 SQL 查询，返回结果。这是调用数据仓库的准入门"""
    import sqlite3
    # 这里是演示，实际连接数据仓库
    conn = sqlite3.connect(":memory:")
    try:
        cursor = conn.execute(sql)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        return f"列名: {columns}\n数据: {results[:10]}"
    except Exception as e:
        return f"SQL 错误: {e}"

def get_user_profile(user_id: str) -> str:
    """获取用户基本信息"""
    return f"用户 {user_id}: 30岁, 月收入 8000, 信用评分 672"


# Step 2: 定义函数 Schema（告诉 LLM 有哪些函数可用）
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_data_warehouse",
            "description": "执行 SQL 查询数据仓库",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL 查询语句"
                    }
                },
                "required": ["sql"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": "获取用户基本信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户 ID"
                    }
                },
                "required": ["user_id"]
            }
        }
    }
]

# Step 3: 请求 LLM 决定是否调用函数
def agent(query: str) -> str:
    """
    Function Calling 流程:
    1. 把用户问题 + tools 定义发给 LLM
    2. LLM 判断: 需要调用函数吗？
    3. 如果要 → LLM 返回函数名 + 参数
    4. 执行函数 → 结果返回 LLM → LLM 综合回答
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": query}],
        tools=tools,           # ← 告诉 LLM 有哪些工具
        tool_choice="auto",    # ← 让 LLM 自己决定是否调用
    )

    message = response.choices[0].message

    # LLM 决定调用函数
    if message.tool_calls:
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            # 执行函数
            if func_name == "query_data_warehouse":
                result = query_data_warehouse(**func_args)
            elif func_name == "get_user_profile":
                result = get_user_profile(**func_args)

            # 把函数结果发给 LLM，让它综合回答
            second_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": query},
                    message,
                    {"role": "tool", "content": result,
                     "tool_call_id": tool_call.id}
                ],
                tools=tools,
            )
            return second_response.choices[0].message.content

    # LLM 没有调用函数，直接回答
    return message.content


# 测试
print(agent("查询 2026-07-01 各渠道通过率"))
print(agent("帮我查一下 user_000042 的基本信息"))

```text

---

---

## 17. 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的输出

> ID: `L111`

只输出 SQL 代码，不要任何解释。"""

```text
### 3.2 Few-shot Prompt（少样本学习）


```python
# 给 2-3 个例子比单纯描述好 10 倍
FEW_SHOT_PROMPT = """将自然语言转为 SQL。

例子 1:
  问题: "上周哪个渠道通过率最高？"
  SQL: SELECT channel, AVG(approval_rate) as rate
       FROM ads.ads_model_monitor_daily
       WHERE dt >= '2026-06-30' AND dt <= '2026-07-06'
       GROUP BY channel ORDER BY rate DESC LIMIT 1;

例子 2:
  问题: "近 7 天平均评分是多少？"
  SQL: SELECT AVG(avg_score) FROM ads.ads_model_monitor_daily
       WHERE dt >= '2026-07-02';

现在轮到你了:
  问题: "昨天的总申请数是多少？"
  SQL: """

```text

---

---

## 18. 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的Token 管理与成本控制

> ID: `L112`

```python
# Token 计数 — 每条消息的 token 数 = 输入 token + 输出 token

def estimate_cost(prompt_tokens: int, response_tokens: int,
                  model: str = "deepseek-chat") -> float:
    """估算单次 API 调用的成本"""
    prices = {
        "deepseek-chat": {"input": 0.5, "output": 2},   # 元/百万 token
        "gpt-4o":        {"input": 5, "output": 20},
        "claude-3":      {"input": 3, "output": 15},
    }

    p = prices[model]
    input_cost = prompt_tokens / 1_000_000 * p["input"]
    output_cost = response_tokens / 1_000_000 * p["output"]
    return input_cost + output_cost

# 典型 token 消耗（中文）:
# 100 字 ≈ 130 token
# 1 轮对话 ≈ 500-1000 input token
# 1 条 SQL 生成 ≈ 50-100 output token
# 1 天 1000 次 NL2SQL 调用 ≈ 1-2 元（DeepSeek）

```text

---

---

## 19. 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的动手练习

> ID: `L113`

```python
"""
练习 1: 实现一个多轮对话的"风控分析师 AI 助手"

要求:
1. 支持连续提问（多轮对话）
2. 当用户问"查数据"时，调用函数生成 SQL 并执行
3. 当用户问"什么是 XXX"时，检索 RAG 知识库
4. 控制上下文长度不超过 10 轮

练习 2: 设计一个 NL2SQL 的 System Prompt

场景: 电商数据仓库
  表: ads.ads_daily_gmv (dt, channel, gmv, order_cnt)
  表: ads.ads_product_rank (dt, product_id, sales, category)

要求: 让用户问"昨天的 GMV""最畅销品类"等，LLM 生成正确的 SQL
"""

```text

---

---

## 20. 面试官问：常见问题你会怎么回答？

> ID: `L114`

### Q1: temperature 不同值的效果？


```text
temperature=0.0 → 每次输出完全一样（确定性的）→ SQL 生成 ✅
temperature=0.3 → 稍有变化 → 客服回复 ✅
temperature=0.7 → 富有创意 → 文案生成 ✅
temperature=1.0 → 高度随机 → 创作 ✅

```text
### Q2: System Prompt 和 User Message 有什么区别？


```text
System Prompt:  指导 LLM 行为的"指令" — 通常不被用户看到
User Message:  用户的实际问题

相当于: System = "你是一个 SQL 专家"（角色设定）
         User = "上周通过率是多少？"（具体任务）

好的 System Prompt 是 RAG 和 NL2SQL 成功的一半。

```text

---

## 21. 什么是微调？（20min）

> ID: `L115`

### 1.1 预训练 vs 微调


```text
预训练（Pre-training）:
  用海量数据（万亿 token）训练基础能力
  "学会了语法、推理、知识"
  成本: 数百万美元, 需要数千张 GPU
  只有大公司能做

微调（Fine-tuning）:
  用少量领域数据（几千条）调整模型行为
  "学会了信贷风控的术语和规则"
  成本: 几十元, 只需要 1 张消费级 GPU
  个人开发者也能做

```text
### 1.2 什么场景需要微调？


```text
场景 A: 你的项目用 LLM 做如下事 → 需要微调
  - 生成特定格式的 SQL（你的数仓有自己的列名和命名规范）
  - 识别你项目中的特定概念（night_ops_ratio, on_time_rate）
  - 模仿特定的文风（审批拒绝通知函）

场景 B: 你的项目用 RAG 就够了 → 不需要微调
  - LLM 只需回答知识库中已有的内容
  - 不需要控制输出格式
  - 不需要学习新的概念（知识库里都有）

```text
**总结：RAG 解决"知道什么"，微调解决"怎么回答"**。

---

---

## 22. 请讲讲PyTorch 微调：从原理到 LoRA中的PyTorch 基础：训练三板斧（40min）

> ID: `L116`

```python
import torch
import torch.nn as nn
import torch.optim as optim

# ═══════════════════════════════════════════
# 一个完整的 PyTorch 训练循环
# ═══════════════════════════════════════════

# Step 1: 定义模型
model = nn.Sequential(
    nn.Linear(10, 64),   # 输入 10 维 → 隐藏层 64 维
    nn.ReLU(),            # 激活函数（引入非线性）
    nn.Linear(64, 2),     # 隐藏层 64 维 → 输出 2 维（二分类）
)
# 参数总量: 10×64 + 64 + 64×2 + 2 = 642 + 128 + 2 = 834 个参数

# Step 2: 定义损失函数和优化器
criterion = nn.CrossEntropyLoss()    # 分类任务的标准损失
optimizer = optim.Adam(model.parameters(), lr=0.001)  # Adam 自适应学习率

# Step 3: 训练循环
def train_one_epoch(model, dataloader, criterion, optimizer):
    model.train()  # 切换到训练模式
    total_loss = 0

    for batch_x, batch_y in dataloader:
        # 前向传播: 计算预测值
        outputs = model(batch_x)           # 模型推断
        loss = criterion(outputs, batch_y)  # 计算损失

        # 反向传播: 计算梯度并更新参数
        optimizer.zero_grad()  # 清零梯度
        loss.backward()         # 计算梯度
        optimizer.step()        # 更新参数

        total_loss += loss.item()

    return total_loss / len(dataloader)

# Step 4: 评估
def evaluate(model, dataloader):
    model.eval()  # 切换到评估模式
    correct = 0
    total = 0

    with torch.no_grad():  # 评估时不需要梯度计算（省显存）
        for batch_x, batch_y in dataloader:
            outputs = model(batch_x)
            _, predicted = torch.max(outputs, 1)
            total += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()

    return correct / total

```text

---

---

## 23. 请讲讲PyTorch 微调：从原理到 LoRA中的LoRA：高效微调（1h）

> ID: `L117`

### 3.1 为什么需要 LoRA？


```text
全量微调的问题:
  一个大模型有 70 亿参数（7B）
  每次微调都要更新全部 70 亿参数
  -> 需要巨大显存（24GB+）
  -> 存储多个微调版本（每个版本 14GB）

LoRA 的核心思想:
  不更新原来的 70 亿参数（冻结掉）
  在旁边加一个小型"适配器"（几百万参数）
  只更新适配器

效果:
  微调效果 ≈ 全量微调
  显存需求: 24GB → 8GB
  模型体积: 14GB → 20MB
  切换任务: 只需要换 20MB 的适配器文件

```text
### 3.2 LoRA 原理


```text
原始:
  W (70亿参数矩阵)
  y = W × x  (全量更新)

LoRA:
  W_frozen (70亿参数, 冻结不动)
  + A × B (几十万参数, 可训练)

  y = W_frozen × x + (A × B) × x

  A 的维度: d_in × r
  B 的维度: r × d_out
  r = 8（极小的中间维度）

  为什么 A×B 能模拟大矩阵变化？
  因为参数更新通常是"低秩"的（变化量可以压缩到很小的维度）

```text
### 3.3 使用 HuggingFace PEFT 实现 LoRA 微调


```python
# ── 安装 ──
# pip install transformers peft datasets accelerate bitsandbytes

import torch
from transformers import (
    AutoTokenizer, AutoModelForCausalLM,
    TrainingArguments, Trainer
)
from peft import (
    get_peft_model, LoraConfig, TaskType,
    prepare_model_for_kbit_training
)

# ═══════════════════════════════════════════
# Step 1: 加载基础模型
# ═══════════════════════════════════════════

model_name = "Qwen/Qwen2.5-1.5B-Instruct"  # 1.5B 参数, 消费级显卡能跑

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,   # 半精度 — 省一半显存
    device_map="auto",            # 自动分配 GPU/CPU
)

# ═══════════════════════════════════════════
# Step 2: 配置 LoRA
# ═══════════════════════════════════════════

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,          # 因果语言模型
    r=8,                                       # LoRA 秩（越小越省，越弱）
    lora_alpha=32,                             # 缩放系数
    lora_dropout=0.1,                          # Dropout（防过拟合）
    target_modules=["q_proj", "v_proj"],        # 只微调注意力层的 Q 和 V 矩阵
)

# 冻结原始参数，添加 LoRA 适配器
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# 输出: trainable params: 2.1M || all params: 1.5B || trainable%: 0.14
# 说明: 只更新 0.14% 的参数（210 万 / 15 亿）

# ═══════════════════════════════════════════
# Step 3: 准备训练数据
# ═══════════════════════════════════════════

# 训练数据格式: 指令 + 输入 + 输出
train_data = [
    {
        "instruction": "根据自然语言问题生成 SQL 查询",
        "input": "上周各渠道通过率是多少？",
        "output": "SELECT channel, AVG(approval_rate) FROM ads_model_monitor_daily WHERE dt >= '2026-06-30' AND dt <= '2026-07-06' GROUP BY channel;"
    },
    {
        "instruction": "根据自然语言问题生成 SQL 查询",
        "input": "近7天平均评分是多少？",
        "output": "SELECT AVG(avg_score) FROM ads_model_monitor_daily WHERE dt >= '2026-07-02';"
    },
    # ... 至少 100-500 条这样的数据
]


def format_example(example):
    """构造 Prompt 格式"""
    prompt = f"""指令: {example['instruction']}
输入: {example['input']}
输出: {example['output']}"""
    return tokenizer(prompt, truncation=True, max_length=512,
                     padding="max_length")


# ═══════════════════════════════════════════
# Step 4: 配置训练参数并训练
# ═══════════════════════════════════════════

training_args = TrainingArguments(
    output_dir="./lora_sql_output",           # 模型保存路径
    num_train_epochs=3,                       # 训练轮数
    per_device_train_batch_size=4,            # 批大小（GPU显存决定）
    gradient_accumulation_steps=4,            # 梯度累积（等效 batch=16）
    learning_rate=2e-4,                      # LoRA 学习率（比全量微调大）
    warmup_steps=100,                        # 预热步数
    logging_steps=50,                        # 日志间隔
    save_strategy="epoch",                   # 每轮保存
    fp16=True,                                # 混合精度（省显存）
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
)

# 开始训练
trainer.train()

# ═══════════════════════════════════════════
# Step 5: 保存和推理
# ═══════════════════════════════════════════

# 保存 LoRA 适配器（只有 20MB）
model.save_pretrained("./lora_sql_adapter")

# 推理测试
def generate_sql(question: str) -> str:
    prompt = f"""指令: 根据自然语言问题生成 SQL 查询
输入: {question}
输出:"""

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_new_tokens=128,
        temperature=0.0,     # SQL 不需要创意
        do_sample=False,      # 贪婪解码，确保确定性
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

print(generate_sql("昨天申请总数是多少？"))

```text

---

---

## 24. 请说说LoRA 参数选择指南

> ID: `L118`

```text
r（秩）:
  r=4  → 最快，效果最差 → 简单的格式转换
  r=8  → 推荐，效果不错 → 通用场景
  r=16 → 较慢，效果更好 → 需要学习复杂模式
  r=64 → 接近全量微调 → 数据量大（>1000 条）时用

lora_alpha（缩放）:
  建议: lora_alpha = 2 × r
  r=8 → alpha=16
  r=16 → alpha=32

target_modules（微调哪些层）:
  推荐: ["q_proj", "v_proj"]（最小的改动）
  进阶: ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
  → 模块越多，效果越好，显存需求越大

```text

---

---

## 25. 请讲讲PyTorch 微调：从原理到 LoRA中的动手练习

> ID: `L119`

```python
"""
练习 1: 用 LoRA 微调一个小模型生成 SQL

步骤:
1. 使用 Qwen2.5-0.5B（0.5B 参数，单 CPU 也能跑）
2. 准备 50 条 NL2SQL 训练数据（参考项目的表结构）
3. 配置 LoRA (r=8)
4. 训练 3 轮
5. 对比微调前后的 SQL 生成质量

练习 2: 判断你的项目需要微调还是 RAG

填写下表:
| 场景 | 用 RAG 还是微调？ | 理由 |
|------|----------------|------|
| LLM 需要知道你项目特有的概念 | | |
| LLM 需要控制输出格式（JSON/SQL） | | |
| 知识库会频繁更新 | | |
| 回答需要非常精确（不能有幻觉） | | |
"""

```text

---

---

## 26. 面试官问：常见问题你会怎么回答？

> ID: `L120`

### Q1: 微调后模型会忘记原来的能力吗？


```text
会，这叫"灾难性遗忘"。

解决方案:
1. 混合训练: 在领域数据中混入 20% 通用数据
2. LoRA: 灾难性遗忘比全量微调轻很多（原始参数没变）
3. 学习率不要太大: 2e-4 是 LoRA 的安全值

```text
### Q2: 消费级显卡（RTX 3060 12GB）能微调多大的模型？


```text
Qwen2.5-1.5B  ← ✅ 12GB 显存足够
Qwen2.5-3B    ← ✅ 需要量化 + LoRA
Qwen2.5-7B    ← ⚠️ 需要量化 + LoRA + 梯度累积
LLaMA-13B     ← ❌ 显存不够

建议从 1.5B 开始尝试，跑通流程后再上更大的模型。

```text

---

## 27. 为什么需要 LangChain（20min）

> ID: `L121`

### 1.1 没有框架时的问题


```python
# 手写代码调 LLM — 看起来很简单，直到你需要:
# 1. 多轮对话维护上下文
# 2. 调用多个函数
# 3. 错误重试
# 4. 异步调用
# 5. 日志追踪

# 手写代码开始变得混乱...
def my_agent(query):
    response = llm(query)
    if has_tool_call(response):
        result = tool(response)
        response = llm(query + result)
    # 每次都重复这个模式
    # 没有标准的结构

```text
### 1.2 LangChain 解决了什么


```text
LangChain 提供:
1. 标准化接口 — 所有 LLM（OpenAI/DeepSeek/Claude）用同一套 API
2. 链式编程 — 像搭积木一样组合功能
3. 内置工具 — 向量检索、SQL查询、网页搜索等
4. 可观测性 — LangSmith 追踪执行路径

LangChain 不是必须的，但它是目前最主流的 LLM 应用框架（JD 出现率 71%）

```text

---

---

## 28. 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangChain **核心概念**（40min）

> ID: `L122`

### 2.1 Chat Models


```python
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatDeepSeek

# 统一接口: 不管用哪个 LLM，代码结构完全一样
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
    api_key="sk-xxx",
)

# 改成 DeepSeek: 只换类名和 base_url
llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0.0,
    api_key="sk-xxx",
    base_url="https://api.deepseek.com",
)

# 调用
response = llm.invoke("什么是 night_ops_ratio_30d？")
print(response.content)

```text
### 2.2 Prompt Templates


```python
from langchain.prompts import ChatPromptTemplate

# 比普通字符串拼接好的地方:
# 1. 自动变量注入
# 2. 支持 System/User/Assistant 多角色
# 3. 可以串联

# 基础模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个 SQL 专家。根据以下表结构生成 SQL: {schema}"),
    ("human", "{question}"),
])

# 使用: 自动填充变量
messages = prompt.invoke({
    "schema": "表 ads_model_monitor_daily: channel STRING, approval_rate DOUBLE",
    "question": "上周通过率最高的渠道是什么？",
})

```text
### 2.3 Chains（链）


```python
from langchain.chains import LLMChain

# Chain = Prompt + LLM 的组合
# 这是 LangChain 最基础的原子单位

llm = ChatDeepSeek(model="deepseek-chat", temperature=0.0)

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个 SQL 专家。表结构: {schema}"),
    ("human", "问题: {question}\n生成 SQL:"),
])

sql_chain = LLMChain(
    llm=llm,
    prompt=prompt,
)

# 调用 chain
result = sql_chain.invoke({
    "schema": "ads_model_monitor_daily(channel, approval_rate, dt)",
    "question": "上周哪个渠道通过率最高？",
})
print(result["text"])  # 输出: SELECT channel, AVG(approval_rate) ...


# Sequential Chain（串行链）— 一个链的输出是下一个链的输入
from langchain.chains import SequentialChain

# Chain 1: 生成 SQL
sql_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个 SQL 专家。"),
    ("human", "问题: {question}\n生成 SQL:"),
])
chain_sql = LLMChain(llm=llm, prompt=sql_prompt, output_key="sql")

# Chain 2: 解释 SQL
explain_prompt = ChatPromptTemplate.from_messages([
    ("human", "用中文解释这段 SQL 做了什么:\n{sql}"),
])
chain_explain = LLMChain(llm=llm, prompt=explain_prompt, output_key="explanation")

# 串起来: 用户问问题 → 生成 SQL → 解释 SQL
full_chain = SequentialChain(
    chains=[chain_sql, chain_explain],
    input_variables=["question"],
    output_variables=["sql", "explanation"],
)

result = full_chain.invoke({"question": "上周通过率最高渠道？"})
print(f"SQL: {result['sql']}")
print(f"解释: {result['explanation']}")

```text
### 2.4 Tools（工具调用）


```python
from langchain.tools import tool

# @tool 装饰器: 把 Python 函数变成 LLM 可调用的工具
@tool
def query_warehouse(sql: str) -> str:
    """
    执行 SQL 查询数据仓库。参数: sql — SQL 查询语句
    """
    # 这里是简化实现
    return f"已执行: {sql}"

# 多种内置工具
from langchain_community.tools import DuckDuckGoSearchRun

# 把工具绑定到 LLM
llm_with_tools = llm.bind_tools([query_warehouse, DuckDuckGoSearchRun()])

```text
### 2.5 Agents（智能体）


```python
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate

# Agent = LLM + Tools + 循环决策
# 1. LLM 决定是否调用工具
# 2. 如果调用，执行工具，结果返回给 LLM
# 3. LLM 根据结果决定下一步（继续调用还是直接回答）

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是风控数据仓库的 AI 助手。"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),  # ← 中间步骤
])

agent = create_tool_calling_agent(
    llm=llm_with_tools,
    tools=[query_warehouse],
    prompt=prompt,
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=[query_warehouse],
    verbose=True,  # ← 打印每一步
)

# 执行
agent_executor.invoke({
    "input": "查一下 2026-07-01 各渠道通过率"
})
# 输出:
# > 调用 query_warehouse(sql="SELECT channel, approval_rate ...")
# > 结果: [('APP_IOS', 0.723), ('APP_ANDROID', 0.651)]
# > 回答: APP_IOS 渠道通过率最高，为 72.3%...

```text

---

---

## 29. 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangGraph：状态机工作流（1h）

> ID: `L123`

### 3.1 Chain vs Graph 的区别


```text
Chain (串行): A → B → C → D
  固定的、线性的执行路径
  不能分支、不能循环、不能等待

Graph (有向图):
  A → [条件] → [B → C → D]
            → [E → F] → G → ...
  可以分支（条件路由）
  可以循环（状态机）
  可以等待人工输入（异步）

```text
**LangGraph 用 StateGraph 来定义有状态的工作流。**

### 3.2 **核心概念**


```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

# ═══════════════════════════════════════════
# 概念 1: State（状态）
#   TypedDict — 定义工作流中传递的数据结构
# ═══════════════════════════════════════════

class ApprovalState(TypedDict):
    """信贷审批工作流的状态 — 在各个节点之间传递"""
    user_id: str
    score: int
    decision: str      # APPROVE / REJECT / MANUAL_REVIEW
    reason: str
    rejected: bool


# ═══════════════════════════════════════════
# 概念 2: Nodes（节点）
#   每个节点是一个函数: 输入 State → 修改 State → 输出
# ═══════════════════════════════════════════

def rule_check(state: ApprovalState) -> ApprovalState:
    """节点1: 规则引擎检查"""
    print(f"[规则引擎] 检查 {state['user_id']}")
    state["rejected"] = False
    return state

def model_score(state: ApprovalState) -> ApprovalState:
    """节点2: 模型评分"""
    state["score"] = 672
    return state


# ═══════════════════════════════════════════
# 概念 3: Edges（边）
#   条件边: 根据 State 决定下一步
#   普通边: 固定走到下一个节点
# ═══════════════════════════════════════════

def route_after_rules(state: ApprovalState) -> Literal["rejected", "scoring"]:
    """
    条件边: 规则检查后决定去哪
    - 如果命中硬拒绝 → 去 rejection 节点
    - 否则 → 去模型评分节点
    """
    if state.get("rejected"):
        return "rejected"
    return "scoring"


# ═══════════════════════════════════════════
# 构建图
# ═══════════════════════════════════════════

workflow = StateGraph(ApprovalState)

# 注册节点
workflow.add_node("check", rule_check)
workflow.add_node("scoring", model_score)
workflow.add_node("rejection", lambda s: s)

# 设置入口
workflow.set_entry_point("check")

# 设置边
workflow.add_conditional_edges(
    "check",
    route_after_rules,
    {"rejected": "rejection", "scoring": "scoring"}
)
workflow.add_edge("scoring", END)
workflow.add_edge("rejection", END)

# 编译
app = workflow.compile()

```text
### 3.3 实战：信贷审批完整工作流


```python
"""
本例实现信贷审批的完整状态机:

rule_check ──REJECT──→ rejection_letter → END
    │
    └──PASS──→ model_score ──APPROVE──→ disburse → END
                    │
                    ├──MANUAL_REVIEW──→ request_docs → 【等待用户上传】→ model_score
                    └──REJECT──→ rejection_letter → END
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal
import json


# ── 状态定义 ──
class CreditState(TypedDict):
    user_id: str
    features: dict
    rule_hits: list[str]
    score: int
    decision: str
    reason: str
    required_docs: list[str]


# ── 节点函数 ──

def rule_check(state: CreditState) -> CreditState:
    """节点1: 规则引擎检查 — 需要实现短路逻辑"""
    hits = []
    if state["features"].get("in_blacklist"):
        hits.append("BLACKLIST_HIT")
        state["decision"] = "REJECT"
        state["reason"] = "命中黑名单"
    state["rule_hits"] = hits
    print(f"  [规则] 命中: {hits}")
    return state


def model_scoring(state: CreditState) -> CreditState:
    """节点2: 模型评分"""
    # 模拟 XGBoost 推理
    prob = 0.3  # 违约概率
    score = int(600 + 50 / 0.693 * (1 - prob) / prob)  # 简化评分公式
    state["score"] = score
    print(f"  [模型] 评分: {score}")
    return state


def request_docs(state: CreditState) -> CreditState:
    """节点3 (LLM): 生成需要补充的材料清单"""
    docs = {
        "收入不稳定": "收入证明、银行流水",
        "多头借贷": "现有贷款合同明细",
        "设备异常": "人脸识别视频验证",
    }
    # 根据规则命中情况生成
    state["required_docs"] = [docs.get(state["reason"], "身份证明")]
    print(f"  [LLM] 请补充材料: {state['required_docs']}")
    return state


def rejection_letter(state: CreditState) -> CreditState:
    """节点4 (LLM): 生成拒绝通知"""
    letter = f"""尊敬的{state['user_id']}:
    很抱歉，您的贷款申请未通过。
    原因: {state['reason']}
    您有权在 15 个工作日内申请人工复核。"""
    state["reason"] = letter
    print(f"  [LLM] 已生成拒绝函")
    return state


def disburse(state: CreditState) -> CreditState:
    """节点5: 放款"""
    print(f"  [放款] 已向 {state['user_id']} 放款 ¥5,000")
    return state


# ── 路由函数 ──

def route_after_rules(state) -> Literal["REJECT", "PROCEED"]:
    if state["decision"] == "REJECT":
        return "REJECT"
    return "PROCEED"


def route_after_scoring(state) -> Literal["APPROVE", "MANUAL_REVIEW", "REJECT"]:
    score = state["score"]
    if score >= 600:
        return "APPROVE"
    elif score >= 500:
        return "MANUAL_REVIEW"
    else:
        return "REJECT"


# ── 构建图 ──

def build_credit_workflow():
    graph = StateGraph(CreditState)

    graph.add_node("rule_check", rule_check)
    graph.add_node("model_scoring", model_scoring)
    graph.add_node("request_docs", request_docs)
    graph.add_node("rejection_letter", rejection_letter)
    graph.add_node("disburse", disburse)

    # 条件边: 规则引擎 → 拒绝/继续
    graph.add_conditional_edges(
        "rule_check",
        route_after_rules,
        {
            "REJECT": "rejection_letter",
            "PROCEED": "model_scoring"
        }
    )

    # 条件边: 模型评分 → 通过/人工/拒绝
    graph.add_conditional_edges(
        "model_scoring",
        route_after_scoring,
        {
            "APPROVE": "disburse",
            "MANUAL_REVIEW": "request_docs",
            "REJECT": "rejection_letter"
        }
    )

    graph.add_edge("disburse", END)
    graph.add_edge("rejection_letter", END)
    graph.add_edge("request_docs", END)  # 等待用户上传 — 异步恢复

    graph.set_entry_point("rule_check")
    return graph.compile()


# ── 执行 ──
workflow = build_credit_workflow()

# 场景 1: 正常用户
result = workflow.invoke({
    "user_id": "user_000042",
    "features": {"in_blacklist": False, "age": 30, "income": 8000},
    "rule_hits": [],
    "score": 0,
    "decision": "",
    "reason": "",
    "required_docs": [],
})
print(f"决策: {result['decision']}")

# 场景 2: 黑名单用户
result = workflow.invoke({
    "user_id": "user_000999",
    "features": {"in_blacklist": True, "age": 30, "income": 8000},
    "rule_hits": [],
    "score": 0,
    "decision": "",
    "reason": "",
    "required_docs": [],
})
print(f"决策: {result['decision']} — 原因: {result['reason'][:30]}...")

```text

---

---

## 30. 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的LangGraph 的进阶功能

> ID: `L124`

### 4.1 条件循环（human-in-the-loop）


```python
# 当用户补充材料时，工作流需要恢复
# LangGraph 的 checkpointer 可以自动保存状态

from langgraph.checkpoint.memory import MemorySaver

# 使用持久化存储
checkpointer = MemorySaver()

workflow = build_credit_workflow()
app = workflow.compile(checkpointer=checkpointer)

# 第一次执行: 暂停在 request_docs 等待用户上传
config = {"configurable": {"thread_id": "user_000042_session"}}
result = app.invoke(input_data, config=config)

# 用户上传材料后: 恢复执行
# update_state 从上次暂停处继续
app.update_state(config, {"required_docs": []})
result = app.invoke(None, config=config)

```text
### 4.2 可视化


```python
# 生成工作流图
from IPython.display import Image, display

display(Image(workflow.get_graph().draw_mermaid_png()))
# → 直接看到审批流程图

```text

---

---

## 31. 请说说LangChain vs LangGraph 选择指南

> ID: `L125`

| 场景 | 用 LangChain | 用 LangGraph |
|------|:----------:|:----------:|
| 简单的 Prompt → LLM → 输出 | ✅ | ❌ 杀鸡用牛刀 |
| 多步链式调用（A→B→C） | ✅ | 也✅ |
| 有分支的路由（if-else 决策） | ❌ | ✅ |
| 循环直到条件满足 | ❌ | ✅ |
| 等待人工输入 | ❌ | ✅ |
| 复杂状态机 | ❌ | ✅ |


```text
一句话: 顺序执行用 Chain，条件分支用 Graph，人工干预用 Graph + Checkpointer。

```text

---

---

## 32. 请讲讲LangChain / LangGraph：LLM 应用开发框架实战中的动手练习（1h）

> ID: `L126`

```python
"""
练习 1: 用 LangChain 实现 NL2SQL Agent

要求:
1. 定义两个工具: query_warehouse(sql), get_schema(table_name)
2. Agent 先获取 Schema → 再生成 SQL → 执行 SQL → 返回结果
3. 支持"查一下 2026-07-01 各渠道通过率"这类问题

练习 2: 用 LangGraph 实现客服质检工作流

状态:
  Text → Classify → [投诉] → RouteToAgent → LLM生成摘要 → END
                    [简单问题] → AutoReply → END
                    [复杂问题] → Escalate → END
"""

```text

---

---

## 33. 面试官问：常见问题你会怎么回答？

> ID: `L127`

### Q1: LangChain 值得学吗？还是直接用 Python 调 API 更好？


```text
如果只是调 LLM API（NL2SQL、聊天）→ 直接调 API 更简单，不需要 LangChain
如果需要工具调用（Agent）→ LangChain 让代码结构更清晰
如果面试要求（JD 出现率 71%）→ 值得学

最佳实践: 学会 LanfgChain 的概念，小项目手写，大项目用框架。

```text
### Q2: LangGraph 和 FastAPI 的异步兼容吗？


```python
# LangGraph 原生支持 async
result = await app.ainvoke(input_data)

# 可以集成到 FastAPI
from fastapi import FastAPI

fastapi_app = FastAPI()
workflow = build_credit_workflow()

@fastapi_app.post("/credit/apply")
async def credit_apply(user_id: str):
    result = await workflow.ainvoke({
        "user_id": user_id,
        "features": {"in_blacklist": False},
    })
    return {"decision": result["decision"]}

```text

---
