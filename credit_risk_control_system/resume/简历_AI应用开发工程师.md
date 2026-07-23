# 个人简历 — AI 应用开发工程师

## 📌 基本信息

| 项目 | 内容 |
|------|------|
| **求职意向** | **AI 应用开发工程师**（NL2SQL / RAG / Agent 方向） |
| **工作年限** | 5-8 年（含数据仓库经验） |
| **技术栈** | Python · LangChain · LangGraph · RAG · NL2SQL · XGBoost · 向量数据库 · LLM API |
| **核心优势** | 从底层数据到上层 AI 全链路打通，数仓背景为 NL2SQL/RAG 提供独特壁垒 |
| **邮箱** | your-email@example.com |
| **电话** | 1XX-XXXX-XXXX |
| **GitHub** | github.com/yourname |

---

## 🎯 个人优势

数仓出身，专注 AI 应用开发。
全链路能力——能从数据接入（Kafka/Flink）到特征工程到模型训练到 LLM 应用全部独立完成。
相比纯算法背景的 AI 工程师：我更懂数据结构、数据血缘、实时计算——NL2SQL 中 Schema Context 的构建能力、RAG 中知识库的结构化能力，正是数仓工程师的天然壁垒。
相比纯工程背景的开发者：我具备模型训练、特征工程、评估体系(AUC/KS/PSI)的完整 AI 工程化经验。

---

## 🏢 项目经验

### 核心项目：金融信贷风控 AI 应用系统（数仓+AI 全栈）

**项目概述**：独立设计并实现了一套完整的生产级金融信贷风控系统，
**核心亮点在于数据仓库和 AI 应用的深度结合**
——数据仓库的 ODS/DWD/DWS/ADS 四层架构直接服务于 AI 模型的特征工程和训练样本构建，
SchemaRegistry 元数据体系直接作为 NL2SQL 和 RAG 的知识库上下文。
同一套数据底座，既支撑传统 ML 模型（XGBoost 评分），也支撑 LLM 应用（NL2SQL 智能问数、RAG 知识库问答）。

**项目规模**：代码量 **27,334 行**（Python + SQL + YAML + 文档），包含 10 张表结构、17 维特征向量、50+ 篇知识库文档。

**技术栈**：Python · LangChain · LangGraph · RAG · NL2SQL · XGBoost · FastAPI · ChromaDB · Flink · Hive/Spark · ClickHouse · Kafka

---

### 📐 一、体系架构：数据流即 AI 特征流

```
                    ┌────────────────────────────────────────────────────┐
                    │         LLM 应用层（NL2SQL + RAG + LangGraph）       │
                    │    NL2SQL: "上周通过率？"→ SQL → "APP_IOS 72%"      │
                    │    RAG:    "什么是night_ops?"→ 检索Schema→ 回答     │
                    │    Agent:  信贷审批：规则→模型→人工在环              │
                    └───────────────────────┬────────────────────────────┘
                                            │ 消费 DDL/COMMENT/Schema
                                            │ 消费 DWS 宽表特征
                    ┌───────────────────────▼────────────────────────────┐
                    │    传统 ML 层（XGBoost 特征工程 + 推理引擎）          │
                    │    DWS 宽表 = 17维特征向量 → WOE/IV筛选 → 训练      │
                    │    规则+模型融合推理 = 四层决策架构                   │
                    └───────────────────────┬────────────────────────────┘
                                            │ 消费 DWS 宽表和 ADS 样本
                    ┌───────────────────────▼────────────────────────────┐
                    │    数据仓库层（ODS/DWD/DWS/ADS + SchemaRegistry）    │
                    │    ODS: 原始数据 → DWD: 清洗脱敏 → DWS:17维宽表     │
                    │    ADS: 训练样本 + 监控日报 + 资产报表                │
                    │    SchemaRegistry: COMMENT=NL2SQL上下文, DDL=RAG知识 │
                    └────────────────────────────────────────────────────┘
```

---

### 🧩 二、功能模块详解

#### 功能 1：NL2SQL 智能问数系统（数仓+LLM 的核心结合点）

**解决的问题**：业务分析师想查数据但不会写 SQL，数据工程师被频繁查询请求打断工作。

**实现方案**：

```python
# 把数据仓库的表结构（DDL + COMMENT）作为 LLM 的 System Prompt
# 核心代码：nl2sql/sql_generator.py
class NL2SQLGenerator:
    def query(self, question: str) -> dict:
        # Step 1: 从 SchemaRegistry 加载表结构 + COMMENT → 构造 LLM Prompt
        schema = self.registry.list_tables()
        # COMMENT "近30天深夜操作占比。>60%→高度可疑" → LLM 理解这个列的语义

        # Step 2: 调用 DeepSeek API 生成 SQL（temperature=0.0 确保确定性）
        sql = self._generate_sql(question, schema)

        # Step 3: 安全校验（三道防线）
        assert not any(kw in sql for kw in ['DROP','DELETE'])  # 防注入
        assert 'dt' in sql.lower()  # 必须分区过滤，防全表扫描
        assert sql.strip().upper().startswith('SELECT')  # 只读查询

        # Step 4: 执行 SQL → 返回结果
        return self._execute(sql)
```

**实现成果**：
| 能力 | 实现方式 |
|------|---------|
| 表结构感知 | 从 SchemaRegistry 动态加载，表变更后 Prompt 自动更新 |
| 语义理解 | COMMENT 注释直接作为 LLM 的列含义说明 |
| 安全防护 | 三道校验 + 禁止危险关键字 + 强制分区过滤 |
| 查询示例 | "上周各渠道通过率？" → `SELECT channel, AVG(approval_rate) FROM ads_model_monitor_daily WHERE dt >= '2026-06-30' AND dt <= '2026-07-06' GROUP BY channel` |

---

#### 功能 2：RAG 知识库问答系统（项目文档即知识库）

**解决的问题**：风控运营人员需要快速查询规则定义、特征含义、模型参数，但文档散落在各处。

**实现方案**：

```python
# 核心代码：rag/retrieval_qa.py
class WarehouseRAG:
    def build_index(self):
        # 知识库来源 = 项目文档（不是外部文档！）
        # YAML: config/schemas/*.yaml         → 按顶级 key 切片
        # SQL:  config/ddl/*.sql              → 按 CREATE TABLE 切片
        # MD:   study/*.md                    → 按 ## 标题切片
        for each_file in project_docs:
            chunks = chunk_by_semantic_boundary(each_file)  # 语义边界切片
            self.vector_store.add(chunks)

    def answer(self, question: str) -> str:
        contexts = self.vector_store.search(question, k=3)  # 检索 Top-3
        # "night_ops_ratio_30d 超过多少算异常？"
        # → 检索到: ws_wide_table.yaml: "★ 深夜操作占比。>60%→高度可疑"
        # → 检索到: credit_policy.yaml: "night_ops_ratio_30d > 0.6 → MANUAL_REVIEW"
        return llm(f"根据以下文档回答:\n{contexts}\n\n问题: {question}")
```

**实现成果**：
| 维度 | 具体成果 |
|------|---------|
| 知识库规模 | 50+ 篇结构化文档（Schema DDL 规则 架构） |
| 切片策略 | YAML 按 key / SQL 按 CREATE / MD 按 ## ——不是固定长度切 |
| 检索准确率 | 语义相似度 Top-3 检索 + 余弦距离排序 |
| 回答示例 | "night_ops_ratio_30d 超过 60% 触发人工审核(RC_BH001)。正常范围 < 30%。" |

---

#### 功能 3：LangGraph 信贷审批工作流（多步骤 AI 编排）

**解决的问题**：信贷审批不是单次模型调用，而是需要多步骤状态流转的复杂业务流程，包含人工介入环节。

**实现方案**：

```python
# 核心代码：decision_engine/inference_pipeline.py + LangGraph 状态机
workflow = StateGraph(ApprovalState)

# 节点定义（LLM节点 + 普通节点统一编排）
workflow.add_node("rule_check", rule_check)               # 普通节点：规则引擎
workflow.add_node("model_scoring", model_scoring)          # 普通节点：XGBoost
workflow.add_node("request_docs", request_docs)            # LLM节点：生成补充材料单
workflow.add_node("rejection_letter", rejection_letter)    # LLM节点：生成拒绝函

# 条件路由
workflow.add_conditional_edges("rule_check", route_by_rules,
    {"REJECT": "rejection_letter", "PASS": "model_scoring"})
workflow.add_conditional_edges("model_scoring", route_by_score,
    {"APPROVE": "disburse", "MANUAL_REVIEW": "request_docs", "REJECT": "rejection_letter"})
```

**实现成果**：
| 维度 | 具体成果 |
|------|---------|
| 状态机 | CLOSED→OPEN→HALF_OPEN→CLOSED 四状态，支持人工介入 |
| LLM 节点 | request_docs（生成补材料清单）、rejection_letter（生成合规拒绝函） |
| 条件路由 | 按规则结果/模型评分动态决定下一步，而非固定流程 |
| 可观测性 | LangGraph checkpointer 自动持久化状态，中断后可恢复 |

---

#### 功能 4：XGBoost 评分模型 + 四层融合推理引擎（传统 ML）

**解决的问题**：纯 LLM 无法处理结构化信贷数据的精准评分，需要用 XGBoost 做核心风控模型，并与规则引擎融合决策。

**实现方案**：

```python
# 核心代码：models/trainer.py + decision_engine/inference_pipeline.py

# 训练层面：DWS 宽表 → 特征向量 → XGBoost
# DWS 宽表的 17 维特征就是模型的 17 个输入特征
# WOE/IV 从 20 维中筛选出 13 维有效特征
features = dws_wide_table[selected_features]  # DWS 宽表 = 特征向量
model = xgb.XGBClassifier(
    scale_pos_weight=9,    # 样本不平衡：好坏比 1:9
    max_depth=5,           # 防过拟合
    eval_metric='auc',
    early_stopping_rounds=50
)

# 推理层面：四层融合决策
async def execute(request):
    # Layer 1: 硬规则（短路）
    rules = rule_engine.evaluate(context)
    if any(r.decision == 'REJECT' for r in rules):
        return REJECT  # 不跑模型，安全省算力

    # Layer 2: XGBoost 评分
    prob = model.predict_proba(feature_vector)  # 违约概率 [0,1]
    score = 600 + 72.1 * np.log((1-prob)/prob)  # 评分卡映射 [300,900]

    # Layer 3: 融合判定（规则 > 模型）
    decision = "APPROVE" if score >= 600 else "MANUAL_REVIEW"
    if any(r.decision == 'MANUAL_REVIEW' for r in rules):
        decision = "MANUAL_REVIEW"  # 规则覆盖模型

    return Decision(decision, score, reason_codes, shap_values)
```

**实现成果**：
| 维度 | 具体成果 |
|------|---------|
| 特征体系 | 从 3 张 DWD 明细表聚合为 17 维用户风险特征宽表 |
| 特征筛选 | WOE/IV 方法从 20 维筛选到 13 维有效特征 |
| 模型评估 | AUC / KS / PSI / Lift 四维指标体系，设定上线标准 |
| 推理架构 | 四层融合（硬规则→模型→融合→策略），P99 < 300ms |
| 降级容错 | 在线特征(50ms超时)→缓存→默认值，三层降级路径 |
| 可解释性 | SHAP 值 + reason_code 双轨可追溯 |

---

#### 功能 5：MLOps 监控与自动熔断

**解决的问题**：模型上线后数据分布会变化、模型效果会退化，需要自动化监控和熔断机制。

**实现方案**：

| 组件 | 实现方式 | 触发阈值 |
|------|---------|---------|
| **PSI 漂移监控** | 每日计算线上 vs 训练的特征分布 PSI | PSI > 0.25 → CRITICAL 告警 |
| **模型熔断器** | CLOSED→OPEN→HALF_OPEN→CLOSED 状态机 | 逾期率突增 > 30% / PSI 超标 > 3 个 / 错误率 > 10% |
| **降级路径** | 在线特征(50ms)→缓存→默认值(保守) | 异步超时自动降级 |
| **熔断恢复** | 冷却 1 小时后用 5% 流量试探恢复 | HALF_OPEN 状态指标正常则恢复 |

---

### 📊 三、实现成果汇总

| 维度 | 成果 | 衡量方式 |
|------|------|---------|
| **项目规模** | 27,334 行代码 | git 统计 |
| **数据仓库** | 10 张表（ODS 3 + DWD 3 + DWS 1 + ADS 3） | 表结构定义 |
| **特征向量** | 17 维宽表特征（画像6 + 行为6 + 还款5） | DWS 宽表列数 |
| **知识库** | 50+ 篇结构化文档 | 向量数据库 chunks |
| **模型评估** | AUC/KS/PSI/Lift 四维指标 + 上线标准 | evaluator.py |
| **推理延迟** | P99 < 300ms（含特征获取+规则+模型+序列化） | FastAPI + asyncio |
| **代码文档** | 14 篇/14,078 行技术文档 | Learning_Review_Plan |

---

### 🔗 四、数据仓库如何支撑 AI 应用（融合点总结）

| 数仓能力 | AI 应用中的角色 | 不可替代性 |
|---------|---------------|:---------:|
| **ODS/DWD/DWS/ADS 分层** | 特征工程的天然分层——DWS 宽表 = 特征向量，ADS 样本 = 训练数据 | ⭐⭐⭐⭐⭐ |
| **DDL + COMMENT 规范** | NL2SQL 的 Schema Context——LLM 通过 COMMENT 理解列含义 | ⭐⭐⭐⭐⭐ |
| **SchemaRegistry** | NL2SQL 的 Prompt 动态来源 + RAG 知识库的数据源 | ⭐⭐⭐⭐ |
| **数据血缘** | 模型可解释性追溯——特征从哪个源表来，经过了什么转换 | ⭐⭐⭐⭐ |
| **数据质量体系** | 模型监控思维的底层——dq_score 和 PSI 本质上都在衡量"分布变化" | ⭐⭐⭐⭐ |
| **分区策略** | PIT 样本构建——防时间泄漏的物理保证 | ⭐⭐⭐⭐⭐ |

---

## 🛠️ 核心技能

### AI / LLM 技能（核心）

| 技能 | 熟练度 | 应用场景 |
|------|:----:|---------|
| **Python** | ★★★★★ | AI 应用开发、数据处理、API 服务 |
| **LangChain / LangGraph** | ★★★★ | 多步骤工作流编排、Function Calling |
| **RAG 全链路** | ★★★★ | 文档切片 → 向量化 → 检索 → 重排序 → 生成 |
| **NL2SQL / Text2SQL** | ★★★★ | Schema Context 注入 + SQL 安全校验 + 执行 |
| **LLM API (DeepSeek/GPT/Claude)** | ★★★★ | Function Calling、Streaming、Prompt 工程 |
| **向量数据库 (Chroma/Milvus)** | ★★★ | 索引构建、相似度搜索、HNSW 算法 |
| **XGBoost 训练 + 评估** | ★★★★ | AUC/KS/PSI/Lift、Scale Pos Weight |
| **PyTorch 微调 (LoRA)** | ★★★ | PEFT 框架、小模型(1.5B)微调 |
| **FastAPI / 推理服务** | ★★★★ | 异步接口、降级策略、熔断机制 |
| **SHAP 可解释性** | ★★★ | 特征贡献分析、决策追溯 |

### 数据仓库 / 工程（辅助支撑）

| 技能 | 熟练度 | 对 AI 的价值 |
|------|:----:|-------------|
| **SQL** | ★★★★★ | NL2SQL 的核心基础 |
| **数据建模 / 分层架构** | ★★★★★ | 特征工程 + Schema Context |
| **Hive / Spark** | ★★★★★ | 大规模数据处理 |
| **Flink 实时计算** | ★★★★ | 实时特征管道 |
| **数据治理 / 血缘** | ★★★★ | RAG 知识库结构化基础 |
| **ETL / 调度** | ★★★★ | 数据管道编排 |
| **Kafka** | ★★★ | 流式数据接入 |

---

## 📊 项目数据

| 指标 | 数据 |
|------|:----:|
| 项目总代码量 | **27,334 行**（Python + SQL + YAML + 文档） |
| 表结构数 | **10 张表**（ODS 3 + DWD 3 + DWS 1 + ADS 3） |
| 特征向量维度 | **17 维**（画像 6 + 行为 6 + 还款 5） |
| 知识库文档数 | **50+ 篇**（Schema + DDL + 规则 + 架构文档） |
| 技术文档总量 | **14,078 行**（14 篇每日学习手册，含 6 篇补充专题） |

---

## 💡 面试话术

> **Q: 你有数据仓库背景，为什么转 AI 应用开发？**
> "数据仓库和 AI 应用之间有一片空白地带——数据怎么组织成特征？表结构怎么成为 LLM 的上下文？数据血缘怎么变成可解释性的追溯链？我转型不是放弃数仓，而是把数仓的底层能力延伸到 AI 层。最典型的例子是 NL2SQL——它的瓶颈不是 LLM 生成 SQL 的能力，而是 Schema Context 的质量，而这正是数仓工程师最擅长的事。"

> **Q: 你的 RAG 项目有什么特别之处？**
> "我的 RAG 知识库来源和一般的不同——不是外部文档，而是项目的表结构定义、DDL、规则配置。这意味着检索返回的不是泛泛的常识，而是'night_ops_ratio_30d > 60% 触发 RC_BH001 规则'这种精确的生产信息。而且切片策略是按语义边界（YAML 按 key / SQL 按 CREATE / MD 按 ##）而不是固定长度——后者会把一个完整的特征定义切成两半。"

> **Q: 传统 ML（XGBoost）和 LLM 应用你都会，更倾向哪个？**
> "两者不冲突。在企业落地中，需要根据场景选型——结构化数据用 XGBoost（信贷评分），非结构化数据用 LLM（知识库问答、NL2SQL）。我的优势是两种都能做，而且能把它们结合——比如用 XGBoost 做风控评分，用 NL2SQL 让业务人员查评分结果，用 RAG 解释评分规则。"

> **Q: 你觉得做 AI 应用开发，你的核心壁垒是什么？**
> "**NL2SQL + RAG**。现在市场上会说'我会 LangChain'的人很多，但能把 Schema 设计、COMMENT 注释规范、数据血缘这三个数仓基本功和 LLM 应用结合起来的人很少。NL2SQL 最缺的不是会写 Prompt 的人，而是懂 Schema 和数仓的人——这就是我的核心壁垒。"

---

## 📝 附加说明

> - **教育背景**：本科，计算机相关专业（待补充）
> - **证书**：待补充
> - **到岗时间**：待补充
