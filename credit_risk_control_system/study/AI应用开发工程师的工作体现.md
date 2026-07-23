# AI 应用开发工程师在项目中的工作体现

> 核心问题：在一条数据的流转过程中（ODS→DWD→DWS→ADS→推理），AI 应用开发工程师做了什么？与数据工程师、后端工程师的边界在哪里？

---

## 角色分工总览

```
数据流转环节:    ODS          →    DWD         →     DWS        →     ADS        →   推理/服务

主要角色:     数据工程师        数据工程师          ★ AI工程师       ★ AI工程师       ★ AI工程师
                                                                                 + 后端工程师
             ──────────        ──────────         ──────────      ──────────      ──────────
             ·数据接入           ·数据清洗          ·特征工程        ·样本构建        ·规则+模型融合
             ·Kafka/Flink       ·脱敏规则          ·衍生特征设计    ·标签定义        ·推理流水线编排
             ·分区策略           ·质量评分          ·时间窗口选择    ·监控指标定义    ·A/B测试路由
             ·DDL定义            ·标准化映射        ·风险信号挖掘    ·评估标准制定    ·降级策略
                                                  ·缺失值策略      ·PIT校验         ·熔断规则
                                                                                  ·评分卡映射
                                                                                  ·可解释性(SHAP)
```

---

## 第1站 ODS 层 — AI 工程师几乎不参与

**承担角色**：数据工程师

| 工作内容                          | 谁做的    | 为什么                |
|--------------------------------|---------|--------------------|
| 设计 `ODSTable` 元数据模型           | 数据工程师  | 定义表名、来源系统、接入方式     |
| Kafka Connect / Flink CDC 配置  | 数据工程师  | Binlog 实时同步是基础设施   |
| 分区策略（按 `dt` 分区）               | 数据工程师  | 存储优化和查询性能          |
| 模拟数据中的脏数据注入                   | 数据工程师  | 测试数据管道的健壮性         |

**AI 工程师的唯一关切**：确保 ODS 中包含训练模型所需的**原始信息**（如行为事件中的 `event_time`、申请记录中的 `apply_amount`），
因为这些字段后续会被加工成特征。如果源系统没有采集这些数据，AI 工程师需要向数据工程师提出需求。

---

## 第2站 DWD 层 — AI 工程师间接参与

**承担角色**：数据工程师为主，AI 工程师提需求

| 工作内容                  | 谁做的    | AI 工程师的价值   |
|------------------------|---------|-------------|
| PII 脱敏（`DataMasker`）  | 数据工程师  |             |
仍然保留了地区码和出生日期信息，可以衍生"年龄"特征 |
| 数据质量评分（`dq_score`） | 数据工程师 | 要求：哪些字段缺失会影响模型？必填字段缺失扣 30 分，
可选字段扣 5 分——这个权重需要 AI 工程师根据特征重要性给出建议 |
| 产品类型标准化  | 数据工程师  | 要求：标准化的枚举值要能作为 categorical feature 输入模型              |
|-----------|---------|------------------------------------------------------|
| 异常金额修正   | 数据工程师  | 要求：负数金额应如何处理？clip(0)？填均值？填中位数？这会影响模型训练——AI 工程师决定策略   |

**关键代码体现**：

```python
# src/data/warehouse/dwd_layer.py 第116-127行
# 数据工程师写的清洗逻辑，但扣分权重需要 AI 工程师确认：
df['dq_score'] = 100
df.loc[mask, 'dq_score'] -= 30   # 必填缺失——致命，模型无法使用
df.loc[amount <= 0, 'dq_score'] -= 20  # 金额异常——严重，影响收入特征
df.loc[product == 'UNKNOWN', 'dq_score'] -= 10  # 类型未知——可用但降权
```

---

## 第3站 DWS 层 — ★ AI 工程师的核心战场

**承担角色**：AI 应用开发工程师主导，这是整个项目体现 AI 工程师价值最集中的地方。

### 3.1 特征工程 — 从"原始数据"到"模型可理解的信息"

AI 工程师拿到清洗后的 DWD 明细数据，要做最关键的转化：**把散落的业务事件聚合成模型能理解的特征向量**。

```
DWD 明细（数据工程师交付的）:
  user_000042 | page_view  | /mine    | 2026-07-01 23:45 ← 这是一行事件日志
  user_000042 | submit     | /apply   | 2026-07-01 02:30
  user_000042 | click      | /repay   | 2026-07-01 10:00
  ...

AI 工程师将其转化为特征（DWS 宽表的一行）:
  user_000042 | night_ops_ratio_30d=0.27 | apply_cnt_7d=1 | on_time_rate=0.33 | ...
```

**AI 工程师在这里做的工作**：

| 特征                     | AI 工程师的决策                            | 为什么这是 AI 工作而非数据工程                                           |
|-------------------------|---------------------------------------|-------------------------------------------------------------|
| `night_ops_ratio_30d`  | 从 `event_time` 提取小时维度，统计夜间(22-05)占比  | **业务洞察→特征转化**：正常用户白天操作，欺诈团伙常在夜间批量操作。这个洞察来自对欺诈行为的理解，不是工程问题   |
| `apply_cnt_7d`         | 7 天滑动窗口计数                            | **时序窗口选择**：7 天 vs 14 天 vs 30 天？需要 A/B 实验验证哪个窗口预测力最强         |
| `on_time_rate`         | 衍生公式 `1 - 逾期次数/总还款次数`                | **风险量化**：将还款行为转化为一个 [0,1] 的数，新用户默认为 1.0——"无罪推定"是业务决策        |
| `fillna(0)`            | 缺失特征填充策略                             | **模型输入规约**：选 0 而不是均值/中位数，因为"无行为记录"本身就是信号（新用户/沉默用户）          |

**代码位置**：`src/data/warehouse/dws_layer.py` 第 135-199 行

```python
# 这段代码表面是聚合逻辑，实质是 AI 工程师的特征设计：

# ★ night_ops_ratio_30d — 风控强特征
night_hours = group_30d['event_time'].dt.hour.isin([22, 23, 0, 1, 2, 3, 4, 5])
night_ops_ratio = night_hours.mean()

# 为什么选 22:00-05:00？这是基于对借贷欺诈行为模式的分析：
# 欺诈团伙倾向于深夜操作以躲避风控审核。
# 如果选 20:00-06:00 就太宽(包含正常夜生活)，选 00:00-04:00 就太窄。
# 这个时间窗口是 AI 工程师通过数据分析定的。
```

### 3.2 特征筛选 — WOE/IV 方法

**代码位置**：`src/models/woe_iv.py`

```python
# AI 工程师实现的 WOE/IV 计算：
# WOE_i = ln(Distribution_Good_i / Distribution_Bad_i)
# IV    = Σ (Distr_Good_i - Distr_Bad_i) × WOE_i

# IV 解读标准（AI 工程师根据行业经验确定）:
# < 0.02  : 无预测能力 → 剔除（不是数据工程师决定的）
# 0.02-0.10: 弱预测能力
# 0.10-0.30: 中等预测能力
# > 0.50  : 可疑（可能过拟合或时间泄漏）
```

**为什么这是 AI 工作**：IV 阈值选 0.02 还是 0.05，直接影响模型特征数量。阈值太低会引入噪声特征，太高会丢失有用信息。这是建模经验，不是工程判断。

### 3.3 评分卡映射

**代码位置**：`src/models/scorecard.py`

```python
# AI 工程师设计的评分卡参数：
mapper = ScorecardMapper(
    base_score=600,   # 基准分——为什么是 600 而不是 500？
    base_odds=20,     # 基准 odds（好坏比）——为什么是 20:1？
    pdo=50,           # 翻倍分数——翻倍 odds 需要的分数差
    min_score=300,    # 最低分
    max_score=900,    # 最高分
)

# 评分公式：score = 600 + (50/ln2) × ln(odds)
# 这些参数不是随意设的——需要根据实际业务的通过率和坏账率目标来调整
```

---

## 第4站 ADS 层 — ★ AI 工程师的第二个核心战场

### 4.1 训练样本构建 — PIT 正确性

**代码位置**：`src/data/warehouse/ads_layer.py` 第 41-81 行

```python
def build_training_samples(self, dws_wide_table, label_df, performance_window_days=30):
    """
    这是 PIT Join 的最后一站:
    - DWS 宽表的特征快照时间是 dt (如 07-01)
    - label 是该用户在 dt + 30天后的逾期标签
    - 拼接时严格保证: dt_特征 < dt_标签  ← AI 工程师决定的
    """
```

**为什么 PIT 正确性是 AI 工程师的责任**：时间泄漏是最隐蔽的建模错误。如果用 08-01 的还款记录去预测 07-01 的逾期，模型 AUC 可能高达 0.95，但上线后完全失效。数据工程师不了解这个陷阱，后端工程师更不会关心——这是 AI 工程师独有的领域知识。

### 4.2 模型评估标准

**代码位置**：`src/models/evaluator.py`

```python
# AI 工程师定义的上线标准：
MIN_KS = 0.25           # KS 统计量 —— 区分好坏样本的能力
MIN_AUC = 0.65          # AUC —— 排序能力
MAX_PSI = 0.25          # PSI —— 特征/分数分布稳定性
MAX_OVERFIT_GAP = 0.05  # 过拟合差距 —— train AUC - test AUC

# 为什么 KS ≥ 0.25？这不是拍脑袋：
# KS < 0.2   → 几乎没有区分力，模型无用
# KS 0.2-0.3 → 勉强可用，适合次级客群
# KS 0.3-0.5 → 良好，大部分信贷模型在这个范围
# KS > 0.5   → 优秀，但需检查是否过拟合
```

### 4.3 监控指标定义

**代码位置**：`src/data/warehouse/ads_layer.py` 第 83-130 行

```python
monitor = pd.DataFrame([{
    'approval_rate': ...,       # 通过率——由 AI 工程师监控，偏离基线说明模型退化
    'avg_score': ...,           # 平均分——下降说明客群质量恶化
    'score_std': ...,           # 标准差——变化说明分布偏移
    'avg_latency_ms': ...,      # 延迟——超过 300ms 触发告警
}])

# AI 工程师设定的告警规则:
# approval_rate > 0.90 → 风控形同虚设，可能已被欺诈攻破
# approval_rate < 0.30 → 过于严格，影响业务量
# manual_review_rate > 0.20 → 模型区分力不足，大量转人工
```

---

## 第5站 推理服务 — ★ AI 工程师的第三个核心战场

### 5.1 规则 + 模型融合决策

**代码位置**：`src/decision_engine/inference_pipeline.py` 第 164-261 行

```
推理流水线的 6 个 Phase:
  Phase 1: 并行获取特征 (asyncio.gather, 50ms超时)
  Phase 2: 规则引擎硬拒绝 → 命中直接返回 REJECT，不跑模型  ← AI工程师决定短路逻辑
  Phase 3: XGBoost 推理 + SHAP 解释
  Phase 4: 额度策略计算
  Phase 5: 决策判定（规则结果 + 模型评分融合）
  Phase 6: 异步写决策日志
```

**融合逻辑是 AI 工程师设计的**：

```python
# src/decision_engine/inference_pipeline.py 第 233-246 行

# 硬拒绝 → 不跑模型，直接返回（节省算力+绝对安全）
if reject_rules:
    return REJECT

# 模型推理
default_prob = model.predict_proba(feature_vector)
score = prob_to_score(default_prob)

# 融合判定:
if score >= 500:           decision = "APPROVE"
elif score >= 450:         decision = "MANUAL_REVIEW"
else:                      decision = "REJECT"

# 但规则引擎的人工审核标记可以覆盖模型决策:
if manual_review_rules:    decision = "MANUAL_REVIEW"
```

**为什么 500 分是分界线**：这需要分析评分分布与坏账率的关系，确定"通过/人工/拒绝"三段的最优切分点。这完全是 AI 工程师的数据分析工作。

### 5.2 A/B 测试路由

**代码位置**：`src/decision_engine/ab_router.py`

AI 工程师设计流量分配策略：新模型上線时只切 5% 流量，观察一周后逐步放量到 50%、100%。

### 5.3 降级策略

**代码位置**：`src/decision_engine/degradation.py`

AI 工程师定义：特征服务超时 50ms → 用缓存 → 缓存也没有 → 用默认值。默认值的选择（如 `night_ops_ratio_30d` 默认为 0.2 还是 0.5）影响风控效果。

### 5.4 模型熔断

**代码位置**：`src/monitoring/circuit_breaker.py`

```python
breaker = ModelCircuitBreaker(
    delinquency_spike_threshold=0.30,  # 逾期率突增 30% → 熔断
    # CLOSED → OPEN → HALF_OPEN → CLOSED 状态机
)
```

AI 工程师决定：逾期率突增 30% 时自动切换到备用模型或纯规则模式。这个阈值需要分析历史逾期率的波动范围来确定。

### 5.5 SHAP 可解释性

**代码位置**：`src/models/shap_explainer.py`

金融监管要求每笔拒绝决策都能解释原因。AI 工程师用 SHAP 值量化每个特征对决策的贡献——"您的贷款被拒绝，主要原因是近期多头借贷次数过多(shap=+0.15)和历史逾期记录(shap=+0.12)"。

---

## 总结：AI 工程师 vs 其他角色

```
                        数据工程师          AI应用开发工程师        后端工程师
                        ─────────          ────────────────        ─────────
ODS 层                   ★ 主导              提需求(需要哪些字段)      —
DWD 层                   ★ 主导              提需求(脱敏+质量策略)     —
DWS 层 (特征工程)         提供聚合框架          ★ 主导(特征设计+筛选)   —
ADS 层 (训练样本)         提供数据基础设施       ★ 主导(PIT+标签+监控)   —
ADS 层 (监控报表)         提供报表平台           ★ 主导(指标定义+阈值)   提供 Grafana
模型训练 (trainer)        —                    ★ 主导(XGBoost+评估)   —
推理流水线编排            —                    ★ 主导(规则+模型融合)   提供 FastAPI 框架
A/B 路由                 —                    ★ 主导                实现路由逻辑
降级+熔断                —                    ★ 主导(策略+阈值)      实现降级代码
评分卡映射               —                    ★ 主导(P→Score)       —
SHAP 可解释性            —                    ★ 主导                集成到 API 响应
API 网关                 —                    定义接口契约            ★ 主导(实现+部署)
特征服务 (Feast)         搭建存储(Redis)        ★ 主导(特征定义+在线查询) 调用服务
```

### AI 工程师在项目中创建的 10 个核心文件

| 文件                                           | AI 工程师的工作                          |
|-----------------------------------------------|------------------------------------|
| `src/models/woe_iv.py`                       | WOE/IV 特征筛选算法实现，IV 阈值标准            |
| `src/models/trainer.py`                      | XGBoost 训练流程，超参默认值，样本不平衡处理         |
| `src/models/evaluator.py`                    | KS/AUC/Gini/PSI/Lift 评估指标，上线标准阈值   |
| `src/models/scorecard.py`                    | 违约概率→评分的映射公式，基准分/PDO 参数            |
| `src/models/shap_explainer.py`               | SHAP 特征贡献计算，可解释性输出                 |
| `src/decision_engine/inference_pipeline.py`  | 6 阶段推理编排，规则+模型融合逻辑，评分阈值            |
| `src/decision_engine/ab_router.py`           | A/B 测试流量分配策略                       |
| `src/decision_engine/degradation.py`         | 降级默认值设计                            |
| `src/monitoring/psi_monitor.py`              | PSI 漂移检测，告警阈值                      |
| `src/monitoring/circuit_breaker.py`          | 熔断规则，逾期率阈值，状态机设计                   |
| `config/rules/credit_policy.yaml`            | 规则条件、决策逻辑、额度策略——业务理解转规则            |
| `config/features/feature_defs.yaml`          | 特征定义——选择哪些特征进入模型                   |

### 一句话概括

**数据仓库工程师铺铁轨，AI 应用开发工程师造列车并决定怎么开，后端工程师建车站。**
- 数据仓库工程师：数据从哪来、怎么建模、怎么清洗、怎么存储、怎么保证质量——**数据资产的构建者**
- AI 工程师：数据怎么变成特征、怎么训练模型、怎么融合规则做决策、怎么监控退化——**从数据到决策的转化**
- 后端工程师：API 怎么设计、怎么部署、怎么扩容——**服务的基础设施**

---

## 补充一：数据仓库工程师的工作体现

> 你的定位是"数据仓库工程师转型 AI 应用开发工程师"。数据仓库的功底不是要抛弃的东西——恰恰相反，DWS 宽表设计和特征工程是数据仓库和 AI 的**交汇点**，是你最大的优势。

### 数据仓库工程师在项目中的完整工作

```
数据流转:    ODS            →    DWD           →     DWS          →     ADS          →   推理
            ───                ───                  ───                ───
数仓工作:   ★ 主导              ★ 主导               ★ 主导(架构)        ★ 主导(数据产品)
            ·分层架构设计        ·清洗规则设计         ·宽表模型设计        ·数据产品设计
            ·数据源接入策略      ·数据质量体系         ·聚合粒度定义        ·指标口径统一
            ·分区策略           ·标准化字典           ·维度建模            ·报表输出
            ·表结构DDL          ·脱敏合规             ·缓慢变化维处理      ·血缘管理
            ·元数据管理         ·异常处理策略         ·Join策略           ·Schema Registry
```

### 逐层展开

#### ODS 层 — 数据仓库工程师的 4 项核心决策

| 决策           | 在这个项目中的体现                                   | 行业通用方法                                            |
|---------------|----------------------------------------------|---------------------------------------------------|
| **分层架构**     | `ODS → DWD → DWS → ADS` 四层分层                | 阿里/美团数仓分层标准：ODS(操作层)→DWD(明细层)→DWS(汇总层)→ADS(应用层)   |
| **表结构 DDL**  | `config/ddl/01_ods_tables.sql` — 16 列的完整定义  | CREATE TABLE 语句、COMMENT 注释、TBLPROPERTIES 元信息      |
| **分区策略**     | 按 `dt` (日期) 分区，`PARTITIONED BY (dt)`        | Hive/Iceberg 分区裁剪，避免全表扫描                          |
| **元数据管理**    | `ODSTable` dataclass + `ODS_TABLES` 注册表     | 生产环境对应 Hive Metastore / AWS Glue Catalog          |

```sql
-- config/ddl/01_ods_tables.sql
-- 数据仓库工程师写的 DDL，定义了表存在的"骨架"：
CREATE TABLE IF NOT EXISTS ods.ods_application (
    user_id           STRING    COMMENT '用户唯一标识',
    apply_amount      DOUBLE    COMMENT '申请金额(元)。含脏数据: 负数/0/NULL',
    user_name         STRING    COMMENT '★ 用户真实姓名(明文PII)',
    ...
)
PARTITIONED BY (dt)
STORED AS parquet
TBLPROPERTIES (
    'source_system' = 'mysql_credit_core',
    'pii_columns' = 'user_name,id_card,phone,ip_address',
    'retention_days' = '90'   -- ← 数据生命周期管理
);
```

#### DWD 层 — 数据仓库工程师的 5 项核心决策

| 决策          | 代码位置                                  | 说明                                                          |
|--------------|----------------------------------------|-------------------------------------------------------------|
| **数据质量体系**  | `dwd_layer.py` 扣分制 `dq_score`         | 不是简单的"通过/不通过"，而是 0-100 的可量化评分                               |
| **清洗规则设计**  | `clean_application()` 6 步清洗           | 必填检查→金额修正→标准化→脱敏→收入修正→隔离                                    |
| **脱敏合规**    | `DataMasker` 类                        | 姓名→`黄*`，身份证→`934184********8691`，满足 GDPR/个人信息保护法            |
| **标准化字典**   | `valid_products` / `channel_map` 映射表  | `cash_loan→CASH_LOAN`，统一全仓枚举值，消除多源异构                        |
| **质量报告产出**  | `DQReport` dataclass                  | `total_rows / passed_rows / quarantined_rows / null_rate`   |

#### DWS 层 — 数据仓库 × AI 的交汇点 ★

**这是你转型最大的优势所在。**

DWS 宽表是数据仓库工程师设计的（维度建模、聚合粒度、Join 策略），但宽表里存的是 AI 工程师需要的特征向量。**同一个人同时懂建模和特征工程，就能设计出"既好查又好训"的宽表。**

| 数仓决策                            | AI 影响                                                      | 你同时具备的能力                  |
|----------------------------------|-------------------------------------------------------------|---------------------------|
| **粒度**: 用户×日期                   | 决定了训练样本的最小单元                                               | 数仓的粒度思维 + AI 的 PIT 思维     |
| **left join**: 保证新用户不丢          | 决定了 `fillna(0)` 对新用户"无罪推定"                                 | 数仓的 Join 策略 + AI 的缺失值处理   |
| **时间窗口**: 7天/30天滑动              | 决定了特征的时效性                                                  | 数仓的窗口函数 + AI 的特征新鲜度分析     |
| **聚合方式**: AVG/MAX/SUM/DISTINCT  | 决定了特征的信息密度                                                 | 数仓的聚合函数 + AI 的 IV 值分析     |
| **建表 DDL**                      | `config/ddl/03_dws_wide_table.sql` — COMMENT 里写了每个特征的风险方向  | 数仓的 DDL 规范 + AI 的元信息标注    |

```sql
-- 这个 DDL 同时体现了数据仓库和 AI 的思维：
CREATE TABLE IF NOT EXISTS dws.user_risk_feature_wide (
    -- 数据仓库视角: 分区键、主键、粒度定义
    -- AI 视角: 17维特征向量，risk_direction 标注在 COMMENT 中
    night_ops_ratio_30d  DOUBLE    COMMENT '★ 近30天深夜操作占比(22-05时)。风控强特征。>60%→高度可疑',
    on_time_rate         DOUBLE    COMMENT '★ 按时还款率=1-逾期次/总次。新用户=1.0。3笔2逾期→0.33→高风险',
    ...
)
PARTITIONED BY (dt)
TBLPROPERTIES (
    'feature_count' = '17',
    'feature_categories' = 'profile(6) + behavior(6) + repayment(5)',
    'pit_principle' = '所有时间窗口以dt为基准向后推算 — 不使用未来信息'
);
```

#### ADS 层 — 数据仓库工程师的数据产品思维

| 数据产品                       | 数仓工作                            | 行业对应                            |
|-----------------------------|----------------------------------|---------------------------------|
| `ads_training_samples`     | 设计训练样本的输出格式，保证可复现               | 机器学习平台的 Feature Store 输出        |
| `ads_model_monitor_daily`  | 设计监控指标的口径：通过率怎么算？用哪个分母？         | 数据产品指标定义                        |
| `ads_portfolio_analysis`   | 分数段分布的分桶逻辑：A+/A/B+/B/C/D 的切分规则  | BI 报表维度设计                       |
| `SchemaRegistry`           | 元数据管理：表结构随数据一起存储，可被外部工具消费       | Hive Metastore / Data Catalog   |

---

## 补充二：RAG / NL2SQL / LangChain 在项目中的体现

> 你学习的 RAG、NL2SQL、LangChain/LangGraph 不是孤立的技术，而是可以**直接嵌入到这个信用风控系统中**，让系统从"被动执行规则"升级为"主动理解和交互"。

### 1. NL2SQL — 让业务人员用自然语言查询数据仓库

**在这个项目中的直接应用场景**：

```
业务分析师（不会写 SQL）:  "上周各个渠道的通过率是多少？"

NL2SQL 引擎:
  1. 从 Schema Registry 读取表结构: ads_model_monitor_daily 有 approval_rate, dt
  2. 生成 SQL:
     SELECT channel, AVG(approval_rate) as avg_approval_rate
     FROM ads.ads_model_monitor_daily
     WHERE dt >= '2026-06-30' AND dt <= '2026-07-06'
     GROUP BY channel;
  3. 执行并返回结果: "APP_ANDROID 65%, APP_IOS 72%, H5 58%"
```

**为什么你作为数据仓库工程师做 NL2SQL 有天然优势**：

| 你的数仓积累               | NL2SQL 中的作用                                                      |
|-----------------------|------------------------------------------------------------------|
| 表结构 DDL / Schema 定义  | 作为 LLM 的 context，告诉它有哪些表、哪些列、什么含义                                |
| COMMENT 注释           | COMMENT `'近30天深夜操作占比(22-05时)'` 直接帮助 LLM 理解列的语义                   |
| 数据血缘                 | 当用户问"逾期率"，系统知道要去 `ads_model_monitor_daily` 还是去 `dwd_repayment`   |
| 指标口径                 | 你定义过"通过率 = APPROVE/总数"，LLM 才能写出正确的聚合 SQL                         |

**在这个项目中的落地位置**：

```
credit_risk_control_system/
├── src/
│   ├── nl2sql/                          ← 新增模块
│   │   ├── schema_context.py            ← 从 SchemaRegistry 加载表结构，构造 LLM prompt
│   │   ├── sql_generator.py             ← LLM 生成 SQL（调用 DeepSeek/Claude API）
│   │   ├── sql_validator.py             ← SQL 安全校验（禁止 DROP/DELETE，只允许 SELECT）
│   │   └── query_executor.py            ← 执行 SQL → 返回结果
│   └── services/
│       └── nl_query_api.py              ← FastAPI 端点: POST /api/v1/query
│                                          {"question": "上周通过率最高的渠道是哪个?"}
```

**伪代码示例**：

```python
# src/nl2sql/schema_context.py
# 从数据仓库的 Schema 定义构造 LLM 的上下文

class NL2SQLContext:
    def __init__(self, registry: SchemaRegistry):
        self.registry = registry

    def build_prompt(self, user_question: str) -> str:
        """构造 NL2SQL 的 System Prompt"""
        tables = self.registry.list_tables()

        schema_desc = []
        for t in tables:
            cols_desc = "\n".join(
                f"    {c.name} {c.type} -- {c.description}"
                for c in t.columns
            )
            schema_desc.append(f"表 {t.layer}.{t.table_name}:\n{cols_desc}")

        return f"""你是一个 SQL 专家。根据以下数据仓库表结构，将用户的自然语言问题转为 SQL。

可用的表：
{chr(10).join(schema_desc)}

查询规则：
- 只生成 SELECT 语句
- 日期过滤使用 dt 列，格式 YYYY-MM-DD
- 涉及"通过率"的查询使用 approval_rate 列

用户问题: {user_question}
请生成 SQL:"""
```

### 2. RAG — 基于数据仓库知识库的智能问答

**在这个项目中的直接应用场景**：

RAG 不是单独存在的——它需要一个**知识库**。而这个项目的 Schema 文档、DDL、规则配置、模型文档，天然构成了知识库。

```
风控运营人员:  "night_ops_ratio_30d 这个特征是什么含义？超过多少算异常？"

RAG 系统:
  1. 检索相关文档:
     - config/schemas/dws_wide_table.yaml → "深夜操作占比，>60%→高度可疑"
     - config/rules/credit_policy.yaml → "night_ops_ratio_30d > 0.6 → MANUAL_REVIEW"
     - 01_system_architecture.md → "风控强特征，从用户行为日志的时间维度提取"

  2. LLM 综合回答:
     "night_ops_ratio_30d 是近30天深夜(22:00-05:00)操作占比。
     正常范围 < 30%，超过 60% 会触发人工审核(RC_BH001规则)。
     这是反欺诈的核心特征，因为欺诈团伙常夜间批量操作。"
```

**RAG 的知识库来源**（你项目中已有的文档）：

| 知识类型        | 源文件                                  | RAG 能回答的问题                          |
|--------------|---------------------------------------|-------------------------------------|
| 表结构 Schema  | `config/schemas/*.yaml`              | "ods_application 有哪些列？"             |
| DDL 定义      | `config/ddl/*.sql`                   | "dws_wide_table 的主键是什么？"            |
| 数据血缘        | `config/schemas/data_lineage.yaml`   | "night_ops_ratio_30d 是从哪个源列算出来的？"   |
| 规则配置        | `config/rules/credit_policy.yaml`    | "什么情况下会被拒绝？"                        |
| 架构文档        | `01_system_architecture.md`          | "整个推理流程是怎样的？"                       |
| 特征定义        | `config/features/feature_defs.yaml`  | "有哪些行为衍生特征？"                        |

**在这个项目中的落地位置**：

```
credit_risk_control_system/
├── src/
│   ├── rag/                             ← 新增模块
│   │   ├── document_loader.py           ← 加载 YAML/Markdown/SQL 文档
│   │   ├── vector_store.py              ← ChromaDB / FAISS 向量化存储
│   │   ├── retriever.py                 ← 检索相关文档片段
│   │   └── qa_chain.py                  ← LangChain RetrievalQA 链
│   └── services/
│       └── knowledge_api.py             ← FastAPI 端点: POST /api/v1/knowledge/ask
│                                          {"question": "什么是night_ops_ratio_30d?"}
```

### 3. LangChain / LangGraph — AI 工作流编排

**在这个项目中的直接应用场景**：

#### 3a. LangChain — 替代手写的推理流水线

当前 `InferencePipeline` 是手写的 Python 编排。用 LangChain 可以实现**可配置的决策链**：

```python
# LangChain 版推理流水线（替代手写的 InferencePipeline.execute()）

from langchain.chains import SequentialChain, LLMChain
from langchain.prompts import PromptTemplate

# Chain 1: 特征解释链
feature_explain_chain = LLMChain(
    llm=llm,
    prompt=PromptTemplate(
        template="""
        用户特征: {features}
        请用自然语言总结该用户的风险点。重点关注：
        - 深夜操作比例是否异常
        - 历史逾期情况
        - 多头借贷情况
        """,
        input_variables=["features"]
    ),
    output_key="risk_summary"
)

# Chain 2: 决策解释链
decision_explain_chain = LLMChain(
    llm=llm,
    prompt=PromptTemplate(
        template="""
        模型评分: {score}
        规则结果: {rule_results}
        风险总结: {risk_summary}

        请生成一段用户友好的拒绝/通过理由。
        如果是拒绝，需要引用具体原因（如"多头借贷次数过多"）。
        """,
        input_variables=["score", "rule_results", "risk_summary"]
    ),
    output_key="explanation"
)

# 总链
credit_decision_chain = SequentialChain(
    chains=[feature_explain_chain, decision_explain_chain],
    input_variables=["features", "score", "rule_results"],
    output_variables=["risk_summary", "explanation"],
)
```

#### 3b. LangGraph — 多步骤审批工作流

信贷审批不是一次模型调用就结束的。复杂场景需要**状态机**：

```
用户提交申请 → 规则检查 → [通过] → 模型评分 → 额度计算 → 放款
                         ↓
                      [命中人工审核规则]
                         ↓
                   人工审核 → [补充材料] → 用户上传 → 重新评估
                            → [拒绝] → 生成拒绝函（LLM生成）
                            → [通过] → 额度打折 → 放款
```

```python
# LangGraph 版审批工作流

from langgraph.graph import StateGraph, END

class ApprovalState(TypedDict):
    user_id: str
    features: dict
    rule_results: list
    score: float
    decision: str          # APPROVE / REJECT / MANUAL_REVIEW / PENDING_DOCS
    explanation: str       # LLM 生成的解释
    required_docs: list    # 需要补充的材料清单

def rule_check(state: ApprovalState) -> ApprovalState:
    """节点1: 规则引擎检查"""
    ...

def model_score(state: ApprovalState) -> ApprovalState:
    """节点2: 模型打分"""
    ...

def manual_review(state: ApprovalState) -> ApprovalState:
    """节点3: 人工审核 — LLM 辅助分析"""
    # LLM 总结风险点，辅助审核员决策
    llm = ChatOpenAI(model="gpt-4")
    summary = llm.invoke(f"该用户的风险特征: {state['features']}, 请总结关键风险点")
    state['explanation'] = summary
    return state

def generate_rejection_letter(state: ApprovalState) -> ApprovalState:
    """节点4: LLM 生成拒绝函"""
    ...

def routing_function(state: ApprovalState) -> str:
    """路由: 根据状态决定下一步"""
    if state['decision'] == 'REJECT':
        return 'generate_rejection_letter'
    elif state['decision'] == 'MANUAL_REVIEW':
        return 'manual_review'
    else:
        return END

graph = StateGraph(ApprovalState)
graph.add_node("rule_check", rule_check)
graph.add_node("model_score", model_score)
graph.add_node("manual_review", manual_review)
graph.add_node("generate_rejection_letter", generate_rejection_letter)

graph.add_conditional_edges("model_score", routing_function)
graph.set_entry_point("rule_check")
app = graph.compile()
```

### 4. 三者在这个项目中的关系图

```
                         ┌─────────────────────────────┐
                         │   LangGraph 工作流编排        │
                         │   多步骤审批、状态机           │
                         │   (替代手写 InferencePipeline) │
                         └─────────────┬───────────────┘
                                       │ 调用
                  ┌────────────────────┼────────────────────┐
                  │                    │                    │
        ┌─────────▼─────────┐  ┌──────▼──────┐  ┌─────────▼─────────┐
        │   NL2SQL 模块      │  │  RAG 模块    │  │  XGBoost 模型      │
        │   "上周通过率?"     │  │  "什么是      │  │  传统 ML 评分       │
        │   → SQL → 数仓查询 │  │   night_ops?" │  │  (已有)             │
        └─────────┬─────────┘  └──────┬──────┘  └───────────────────┘
                  │                    │
        ┌─────────▼────────────────────▼─────────┐
        │         数据仓库 (ODS/DWD/DWS/ADS)       │
        │         + Schema Registry               │
        │         + 表结构 DDL                     │
        │         + 数据血缘                       │
        │         + 规则配置                        │
        │         ↑ 这些都是 RAG 的知识源            │
        │         ↑ 这些都是 NL2SQL 的 schema context│
        └─────────────────────────────────────────┘
```

### 5. 转型路径总结：数仓工程师 → AI 应用开发工程师

```
你已具备的核心能力（数据仓库）         需要叠加的 AI 能力
─────────────────────────────      ─────────────────────
ODS/DWD/DWS/ADS 分层设计          →  理解训练/推理需要什么样的数据
DWS 宽表建模（维度+聚合）          →  ★ 这是你最大的优势！宽表 = 特征向量
表结构 DDL + COMMENT 规范          →  NL2SQL 的 Schema Context
数据质量体系（dq_score 扣分制）      →  模型监控（PSI/KS/AUC 同样需要监控思维）
数据血缘管理                       →  RAG 的知识图谱检索
分区策略 / 生命周期管理              →  PIT 时间窗口的正确性保证
元数据管理（Schema Registry）       →  Feature Store（Feast）的特征注册
指标口径统一                       →  模型评估指标（AUC/KS/PSI）的定义
字典标准化 / 数据清洗               →  特征预处理 pipeline

需要全新学习的能力                  →  在这个项目中的对应
─────────────────────────────      ─────────────────────
XGBoost 训练 + 超参调优             →  src/models/trainer.py
WOE/IV 特征筛选                    →  src/models/woe_iv.py
SHAP 可解释性                      →  src/models/shap_explainer.py
评分卡映射（P→Score）               →  src/models/scorecard.py
规则+模型融合决策                   →  src/decision_engine/inference_pipeline.py
A/B 实验设计                       →  src/decision_engine/ab_router.py
NL2SQL（LangChain + LLM）          →  src/nl2sql/ (新增)
RAG 知识库问答（ChromaDB + LLM）    →  src/rag/ (新增)
LangGraph 工作流编排               →  替代手写 inference pipeline
```

**关键洞察**：你不是从零开始学 AI。你已经有数据仓库的扎实功底——DWS 宽表设计就是特征工程，数据质量监控就是模型监控的思维基础，Schema Registry 就是 Feature Store 的原型。RAG 和 NL2SQL 是你让"数据仓库"变"智能"的桥梁——数据仓库工程师最懂数据在哪、长什么样，这正是 NL2SQL 和 RAG 最需要的能力。
