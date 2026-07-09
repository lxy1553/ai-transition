# AI 应用工程师 7 天复习计划
## 能力总结：面试时怎么说

### 七个能力一句话

| 能力       | 面试一句话                                   | 代码证明                                  |
|-----------|------------------------------------------|---------------------------------------|
| PIT 样本   | "我设计过严格防时间泄漏的样本生成，用 merge 而非 concat"    | `ads_layer.py`                        |
| 特征工程     | "我能从任意事件日志提取特征：时间窗口+比率衍生+缺失策略"          | `dws_layer.py`                        |
| 规则+模型融合  | "我设计过四层决策：硬规则短路→模型评分→融合→策略"             | `inference_pipeline.py`               |
| 评估+监控    | "我搭建过离线评估+在线监控+自动熔断的 MLOps 闭环"          | `evaluator.py + circuit_breaker.py`   |
| 降级容错     | "我设计过三层降级：在线→缓存→默认值，每层有触发条件"            | `inference_pipeline.py`               |
| LLM 应用   | "我用 NL2SQL 让业务查数仓，用 LangGraph 编排审批工作流"  | NL2SQL/RAG/LangGraph                  |
| 可解释性     | "我用 SHAP+reason_code 为每笔决策提供三层可追溯解释"    | `ModelWrapper.explain()`              |

### 面试官关心的五个问题

1. **能不能把业务问题抽象成 AI 方案？** → 规则+模型融合架构
2. **知不知道模型上线后会发生什么？** → 监控+熔断+降级
3. **懂不懂数据？能不能从脏数据中提炼出特征？** → DWD→DWS 特征工程
4. **会不会用 LLM？不只是调 API？** → NL2SQL + RAG + LangGraph
5. **有没有工程思维？代码能上生产？** → FastAPI + 异步 + 降级 + 熔断

### 你的独特卖点

> "我是从数据仓库转型的 AI 应用开发工程师。独特优势是**全链路打通**：从底层数据建模(ODS/DWD/DWS/ADS)到
> 上层 AI 应用(训练+推理+监控+熔断)独立完成。同时擅长 LLM 应用架构——NL2SQL 让业务自然语言查数仓，
> RAG 把项目文档变知识库，LangGraph 编排多步骤 AI 工作流。能从数据库做到 AI 服务，这是单一技术栈 AI 工程师不具备的广度。"


> 基于信贷风控项目 `credit_risk_control_system/`，每天 4-6 小时。每天包含：项目代码阅读 + 代码复现 + 跨业务转化。

---

## Day 1：PIT 样本构建 + 数据→训练样本的转化

**目标**：理解时间泄漏的本质，能手写 PIT 正确的样本构建代码。

### 上午：阅读项目代码（2.5h）

| 阅读文件 | 重点内容 | 时间 |
|----------|---------|------|
| `src/data/warehouse/ads_layer.py` | `build_training_samples()` — merge vs concat 的选择 | 30min |
| `src/data/mock_data_generator.py` | 看 label 是怎么生成的（随机概率分配） | 20min |
| `scripts/generate_data_pipeline.py` 第 120-130 行 | 标签生成逻辑：label_df = ... np.random.choice([0,1]) | 20min |
| `src/models/trainer.py` 的 `train_xgboost()` | 看训练时如何使用 X_train/y_train | 30min |
| 回顾 `study/跨业务通用的AI应用开发能力.md` 能力 1 | PIT 样本构建的理论 + 三种拼接方式的对比 | 30min |
| 在 `data/warehouse/ads/dt=2026-07-01/` 打开 training_samples.parquet | 用 `pd.read_parquet()` 查看实际样本结构 | 20min |

### 下午：代码复现（2.5h）

**练习 1**（1h）：手写 PIT 样本构建的三个版本并对比

```python
import pandas as pd
import numpy as np

# 模拟数据：10 个用户在 T 时刻的特征，T+30 天的标签
features = pd.DataFrame({
    'user_id': [f'u{i}' for i in range(10)],
    'feature_a': np.random.randn(10),
    'feature_time': ['2026-07-01'] * 10,
})
labels = pd.DataFrame({
    'user_id': [f'u{i}' for i in range(10)],
    'label': np.random.choice([0, 1], 10),
    'label_time': ['2026-08-01'] * 10,
})

# 版本 A: 错误 — concat（时间泄漏）
samples_A = pd.concat([features, labels], axis=1)
print("版本A (concat):", samples_A.columns.tolist())
# 问题：你怎么确认没有时间泄漏？

# 版本 B: 错误 — 按行号 merge 但不检查时间
# ...

# 版本 C: 正确 — merge on user_id + 显式时间校验
# ...

# 写一段分析：版本 A 在什么情况下"看起来没问题"但实际有问题？
```

**练习 2**（1h）：为电商推荐写 PIT 样本构建

```python
# 电商推荐场景：预测"曝光后 7 天内用户是否会购买"
def build_电商推荐_训练样本(
    user_features,    # 曝光时刻的特征
    click_labels,     # T+7 的购买标签
):
    """
    要求：
    1. 时间约束：feature_time < label_time
    2. 关联键：user_id + item_id（比信贷多一个维度）
    3. 处理一个用户对多个商品曝光的情况
    """
    pass
```

**练习 3**（30min）：时间泄漏检测器

```python
# 写一个函数，检测训练样本中是否存在时间泄漏
def detect_time_leakage(samples: pd.DataFrame,
                        feature_time_col: str,
                        label_time_col: str) -> list[str]:
    """
    返回存在时间泄漏的样本行索引列表。
    泄漏 = feature_time >= label_time
    """
    pass
```

### 晚上：跨业务思考（1h）

- 自动驾驶的"碰撞预测"模型：特征时间是什么？标签时间是什么？时间泄漏会怎样？
- 内容推荐的"点击预测"：如果用"点击后"的用户画像去预测"是否点击"会有什么后果？

### 产出物
- [ ] 三个版本的 PIT 样本构建代码 + 分析文档
- [ ] 电商推荐 PIT 样本构建代码
- [ ] `detect_time_leakage()` 函数

---

## Day 2：特征工程 — 从事件流到特征向量

**目标**：掌握三种特征构造模式（时间窗口 COUNT WHERE、比率衍生、缺失值策略），能对任意业务事件日志提取特征。

### 上午：阅读项目代码（2.5h）

| 阅读文件 | 重点内容 | 时间 |
|----------|---------|------|
| `src/data/warehouse/dws_layer.py` 的 `_build_behavior_features()` | ★ 核心：三种模式的代码实现 | 1h |
| `config/schemas/dws_wide_table.yaml` 的 category_behavior 部分 | 6 个行为特征的 aggregation 公式 | 30min |
| `src/data/warehouse/dws_layer.py` 的 `_build_profile_features()` | 聚合函数选择（为什么 income 取 max） | 20min |
| `src/data/warehouse/dws_layer.py` 的 `_build_repayment_features()` | on_time_rate 的衍生公式 + 新用户默认 1.0 | 20min |
| 回顾 `study/跨业务通用的AI应用开发能力.md` 能力 2 | 三种模式的理论 + 三个"为什么"的注释分析 | 20min |

### 下午：代码复现（2.5h）

**练习 1**（1.5h）：为电商行为日志提取特征

```python
# 原始数据: 用户电商行为日志
events = pd.DataFrame({
    'user_id': ['u1', 'u1', 'u1', 'u1', 'u2', 'u2', ...],
    'event_type': ['view_item', 'add_cart', 'purchase', 'search', ...],
    'category': ['电子', '电子', '电子', '服装', ...],
    'event_time': ['2026-07-01 09:30', ...],  # datetime
    'price': [2999, 2999, 2999, 199, ...],
})

def build_ecommerce_behavior_features(events, ref_date):
    """
    要求设计至少 8 个特征，包含：
    - 模式1: COUNT WHERE（view_cnt_7d, cart_cnt_7d, purchase_cnt_7d）
    - 模式2: 比率衍生（cart_conversion=加购/浏览, purchase_conversion=购买/加购）
    - 模式3: 多样性（category_diversity, avg_session_pages）
    - 缺失值: 新用户无行为 → fillna(?)
    """
    pass
```

**练习 2**（1h）：分析特征的预测力

```python
# 用 WOE/IV 方法（项目中的 src/models/woe_iv.py）计算特征 IV 值
from src.models.woe_iv import WOECalculator

# 1. 生成模拟数据（1000 个用户，有 label 和特征）
# 2. 运行 WOE 计算
# 3. 按 IV 从高到低排序
# 4. 分析：哪个特征 IV 最高？为什么？（写一段分析）
# 5. 如果所有特征 IV 都 < 0.02，说明什么？怎么办？
```

### 晚上：跨业务思考（1h）

- 游戏行业：如何从"登录/充值/副本/社交"事件中提取付费意愿特征？
- 打车行业：如何从"下单/接单/取消/评价"事件中提取司机质量特征？

### 产出物
- [ ] `build_ecommerce_behavior_features()` 完整代码
- [ ] WOE/IV 特征分析报告
- [ ] 游戏/打车行业的特征设计方案（文字描述）

---

## Day 3：规则 + 模型融合决策架构

**目标**：掌握四层决策架构的设计原理，能手写融合逻辑。

### 上午：阅读项目代码（2.5h）

| 阅读文件 | 重点内容 | 时间 |
|----------|---------|------|
| `src/decision_engine/inference_pipeline.py` | ★ 全文精读 `execute()` 方法 6 个 Phase | 1h |
| `src/decision_engine/rule_engine.py` | `RuleEngine.evaluate()` + `SafeExpressionEvaluator` AST 安全求值 | 40min |
| `config/rules/credit_policy.yaml` | 三层规则：hard_reject → risk_assessment → credit_limit | 30min |
| `src/models/scorecard.py` | `prob_to_score()` 评分卡公式：score = 600 + factor × ln(odds) | 20min |

### 下午：代码复现（2.5h）

**练习 1**（1h）：手写决策融合的四个版本并对比

```python
# 场景：一个模型给出违约概率 0.3（评分 620），规则引擎触发了"多头借贷警告"

# 版本 A: 纯模型 — 只看模型评分，忽略规则
# 决策: APPROVE (因为 620 >= 600)
# 问题: 规则信号被忽略 → 放了该被 Review 的申请

# 版本 B: 纯规则 — 只看规则结果，忽略模型
# 决策: MANUAL_REVIEW (因为触发了规则)
# 问题: 模型信息浪费 → 600+ 评分本质是安全的

# 版本 C: 规则优先 + 模型兜底（项目采用的方案）
# 决策: MANUAL_REVIEW (规则强制 Review)
# 但如果规则没触发 → 模型做主决策

# 版本 D: 加权融合 — 规则分数 + 模型分数 → 总分
# 决策: 取决于权重设计

# 要求：写出四个版本的代码，并分析各自的优劣
```

**练习 2**（1h）：为内容审核设计分层决策

```python
async def moderate_content(text: str, user: dict) -> dict:
    """
    四层架构：
    Layer 1: 硬规则 — 敏感词字典 → 直接拦截
    Layer 2: 模型 — BERT 违规分类 → 输出概率 [0,1]
    Layer 3: 融合 — 规则覆盖 + 模型兜底 + 用户历史
    Layer 4: 策略 — 拦截 / 限流 / 标记 / 放行

    要求：
    1. 定义至少 3 条硬规则
    2. 设定融合阈值（为什么选这个阈值？）
    3. 新用户 vs 老用户用不同的阈值吗？
    """
    pass
```

**练习 3**（30min）：分析评分卡参数对决策的影响

```python
# src/models/scorecard.py
# base_score=600, base_odds=20, pdo=50

# 问题 1: 如果把 base_score 从 600 改为 550，对 APPROVE/MANUAL_REVIEW/REJECT 的分布有什么影响？
# 问题 2: pdo=50 的含义是"当 odds 翻倍时，分数增加 50"。
#         如果把 pdo 改为 20，评分对概率变化是更敏感还是更迟钝？
# 问题 3: 如何根据实际业务的通过率目标来反推这些参数？
```

### 晚上：跨业务思考（1h）

- 医疗分诊系统：Layer 1 硬规则应该包含什么？（生命体征异常？过敏史？）
- 自动驾驶决策：规则和模型的分界线在哪里？什么情况下应该"宁可保守"？

### 产出物
- [ ] 四个版本的决策融合代码 + 对比分析表
- [ ] `moderate_content()` 完整代码
- [ ] 评分卡参数影响分析

---

## Day 4：模型评估 + 线上监控 + 自动熔断

**目标**：掌握 MLOps 闭环：离线评估→在线监控→熔断→重训。

### 上午：阅读项目代码（2.5h）

| 阅读文件 | 重点内容 | 时间 |
|----------|---------|------|
| `src/models/evaluator.py` | `evaluate()` + `_calculate_ks()` + `_calculate_psi()` | 1h |
| `src/monitoring/psi_monitor.py` | PSI 漂移检测：build_baseline + run_daily_check | 40min |
| `src/monitoring/circuit_breaker.py` | 状态机：CLOSED→OPEN→HALF_OPEN→CLOSED | 30min |
| `scripts/run_monitoring.py` | 运行 PSI 和熔断器演示，观察输出 | 20min |

### 下午：代码复现（2.5h）

**练习 1**（1h）：手写 KS 和 PSI 计算（不调库）

```python
import numpy as np

def calculate_ks(y_true, y_pred):
    """
    从零实现 KS 计算。
    KS = max(|好样本累积比例 - 坏样本累积比例|)

    为什么不用 sklearn.metrics？
    → 面试时可能让你手写
    → 理解累积分布的每一步
    """
    # 1. 按预测概率降序排列
    # 2. 分别累积好坏样本比例
    # 3. 取最大差值
    pass

def calculate_psi(expected, actual, bins=10):
    """
    从零实现 PSI。
    PSI = Σ (actual_i - expected_i) × ln(actual_i / expected_i)

    为什么分箱用 expected(训练集)的百分位？
    → 保持分箱边界固定：用训练集边界评估测试集
    """
    # 1. 计算训练集的百分位分箱边界
    # 2. 统计每个箱的占比
    # 3. 计算 PSI
    pass

# 测试：完美分离 vs 随机预测的 KS 值
y_true = np.array([0]*100 + [1]*100)
y_perfect = np.array([0.1]*100 + [0.9]*100)  # 完美分离 → KS ≈ 1.0
y_random = np.random.random(200)               # 随机 → KS ≈ 0.0
print(f"完美 KS: {calculate_ks(y_true, y_perfect):.4f}")
print(f"随机 KS: {calculate_ks(y_true, y_random):.4f}")
```

**练习 2**（1h）：设计推荐系统的监控+熔断

```python
class RecommendationMonitor:
    """
    推荐模型监控器。

    设计三个核心指标 + 告警规则:
    1. CTR 降幅 > 20% → 回退到基线模型
    2. 转化率降幅 > 15% → 触发重训
    3. 推荐覆盖率 < 50% → 告警（可能模型坍塌，只推爆款）
    """
    def __init__(self, baseline_ctr, baseline_conversion):
        self.baseline_ctr = baseline_ctr
        self.baseline_conversion = baseline_conversion

    def check(self, current_ctr, current_conversion, coverage):
        # TODO: 实现监控逻辑

    def rollback(self):
        """回退到上一版本的模型"""
        # TODO: 实现回退逻辑
        pass
```

**练习 3**（30min）：分析项目的评估报告

运行 `python3 scripts/train_model.py --from-warehouse`，分析输出的评估报告：
- 为什么 AUC(train)=0.99, AUC(test)=0.47？
- Overfit Gap=0.52 > 0.05 → 说明什么问题？
- 如何改进？

### 晚上：跨业务思考（1h）

- 语音识别模型的 WER 从 5% 上升到 8%，应该触发什么动作？
- 自动驾驶感知模型在"雨天场景"的准确率骤降 → 应该熔断吗？熔断后用什么兜底？

### 产出物
- [ ] 手写 `calculate_ks()` 和 `calculate_psi()` 代码
- [ ] `RecommendationMonitor` 完整代码
- [ ] 项目评估报告分析（200 字）

---

## Day 5：生产级降级 + 容错设计

**目标**：掌握多层降级路径的设计，理解"每一层为什么这么设计"。

### 上午：阅读项目代码（2h）

| 阅读文件 | 重点内容 | 时间 |
|----------|---------|------|
| `src/decision_engine/inference_pipeline.py` 的 `_fetch_features_with_fallback()` | 三层降级：在线→缓存→默认值 | 40min |
| `src/decision_engine/degradation.py` | `DegradationPolicy.DEFAULTS` 每个默认值的选择逻辑 | 30min |
| `src/decision_engine/inference_pipeline.py` 的 `_gather_features()` | `asyncio.gather` + `return_exceptions=True` 并行超时 | 30min |
| `src/services/api_gateway.py` 的 `credit_apply()` | 看 HTTP 层如何把异常转为 503 | 20min |

### 下午：代码复现（2.5h）

**练习 1**（1h）：手写降级路径的完整实现

```python
import asyncio

class FeatureService:
    """模拟的特征服务 — 有时快有时慢有时挂"""

    async def get_online_features(self, user_id: str):
        """路径1: 在线 — 可能超时"""
        await asyncio.sleep(random.choice([0.01, 0.02, 0.06, 0.2]))
        return {"feature_a": 1.0, "feature_b": 2.0}

    def get_cached_features(self, user_id: str):
        """路径2: 缓存 — 可能命中/可能过期"""
        if random.random() > 0.3:
            return {"feature_a": 0.9, "feature_b": 1.8}  # 缓存命中
        return None  # 缓存过期

class DegradationPolicy:
    """路径3: 默认值 — 总是可用"""
    DEFAULTS = {"feature_a": 0.5, "feature_b": 0.5}

# 要求：实现与项目中完全相同的三层降级逻辑
# 关键: 用 async/await + try/except TimeoutError
# 每层降级要记录到日志（degraded_features 标记）
```

**练习 2**（1h）：设计搜索系统的降级路径

```
搜索系统的四层降级:
路径1: 语义搜索（BERT + 排序模型）→ 80ms 超时
路径2: 关键词匹配（Elasticsearch）→ 50ms 超时
路径3: 热门结果缓存 → 不超时，直接返回
路径4: 空结果 + "请优化搜索词"提示 → 永远可用

要求:
1. 写出每层的超时时间及其理由
2. 路径1 挂了 → 路径2 返回的结果质量下降了，用户体验差多少？
3. 如何评估"降级后的用户满意度"是否可接受？
```

**练习 3**（30min）：降级实验

修改 `DegradationPolicy.DEFAULTS` 中的值，跑一次推理，观察决策变化：
- `night_ops_ratio_30d` 从 0.5 改为 0.1 → 决策从 REVIEW 变成 APPROVE 了吗？
- `on_time_rate` 从 0.5 改为 0.8 → 评分变化了多少分？

### 晚上：跨业务思考（1h）

- 语音助手的降级：云端大模型 → 本地小模型 → 预设回复 → "请稍后再试"。每层的延迟差多少？
- 自动驾驶的降级底线在哪里？什么情况绝对不能降级？

### 产出物
- [ ] 三层降级代码（含日志标记）
- [ ] 搜索系统降级路径设计
- [ ] 降级实验报告（default 值变化 → 决策变化）

---

## Day 6：LLM 应用架构 — NL2SQL + RAG + LangGraph

**目标**：掌握 LLM 应用的架构设计，能独立实现 NL2SQL 和 RAG 系统。

### 上午：阅读与理解（2h）

| 阅读文件 | 重点内容 | 时间 |
|----------|---------|------|
| 回顾 `study/跨业务通用的AI应用开发能力.md` 能力 6 | NL2SQL 四步骤 + RAG 切片策略 + LangGraph 状态机 | 1h |
| `src/data/schema_registry.py` | SchemaRegistry 作为 NL2SQL 的 Schema Context 来源 | 20min |
| `config/rules/credit_policy.yaml` | 规则配置如何作为 RAG 的知识库 | 20min |
| `config/schemas/data_lineage.yaml` | 数据血缘如何帮助 LLM 理解表关系 | 20min |

### 下午：代码实现（3h）

**练习 1**（1.5h）：实现一个最小可行的 NL2SQL 引擎

```python
class MiniNL2SQL:
    """
    最小可行 NL2SQL 引擎。

    不使用 LangChain，只用 LLM API + 手写 Prompt。
    目的是理解"NL2SQL 到底做了什么"，而不是调库。
    """

    def __init__(self, tables_schema: dict):
        """
        tables_schema = {
            "ads_model_monitor": {
                "columns": ["channel", "approval_rate", "dt"],
                "descriptions": {
                    "channel": "渠道",
                    "approval_rate": "通过率 0-1",
                    "dt": "日期 YYYY-MM-DD",
                }
            }
        }
        """
        self.schema = tables_schema

    def _build_prompt(self, question: str) -> str:
        """构造 System Prompt: 注入 schema + 约束规则"""
        pass

    def generate_sql(self, question: str) -> str:
        """调用 LLM 生成 SQL"""
        pass

    def validate_sql(self, sql: str) -> tuple[bool, str]:
        """三道校验: 禁危险关键字 + 必须有分区过滤 + 必须是 SELECT"""
        pass

    def query(self, question: str) -> dict:
        """完整流程: 生成 → 校验 → 执行"""
        pass

# 测试:
engine = MiniNL2SQL(tables_schema)
result = engine.query("上周哪个渠道通过率最高？")
# → {"success": True, "sql": "SELECT channel, AVG(approval_rate)...",
#    "data": [{"channel": "APP_IOS", "avg_rate": 0.72}]}
```

**练习 2**（1h）：实现一个最小可行的 RAG 系统

```python
class MiniRAG:
    """
    最小可行 RAG 系统。

    知识库: 项目的 config/schemas/*.yaml（表结构定义）
    回答: "ods_application 有哪些列？""night_ops_ratio 是什么意思？"
    """

    def __init__(self, docs_dir: str):
        # 1. 加载所有 YAML/MD 文档
        # 2. 切片（按 ## 标题 / 按顶级 YAML key）
        # 3. 向量化（可以用 sklearn TfidfVectorizer 代替 Embedding API）
        # 4. 存入内存（不用 ChromaDB，简化实现）
        pass

    def search(self, question: str, k=3) -> list[str]:
        """检索最相关的 k 个文档片段"""
        pass

    def answer(self, question: str) -> str:
        """检索 + 构造 Prompt + LLM 回答"""
        prompt = f"根据以下文档:\n{self.search(question)}\n\n问题: {question}"
        # return llm.chat(prompt)
        pass
```

**练习 3**（30min）：画出信贷审批的 LangGraph 状态图

```
用 ASCII 或 Mermaid 画出审批工作流的状态转换图:
rule_check → [PASS] → model_score → [APPROVE] → disburse
           → [REJECT] → rejection_letter
                        → [MANUAL_REVIEW] → request_docs → [用户上传] → model_score

要求: 标注每个节点的输入/输出状态字段
```

### 晚上：跨业务思考（1h）

- NL2SQL 在客服系统中的应用：客服主管问"本周投诉最多的原因是什么？"
- RAG 在医疗中的应用：医生问"糖尿病患者的二甲双胍初始剂量是多少？" → 知识库是诊疗指南和药品说明书

### 产出物
- [ ] `MiniNL2SQL` 完整代码
- [ ] `MiniRAG` 完整代码
- [ ] 审批工作流 LangGraph 状态图

---

## Day 7：可解释性 + 综合项目

**目标**：SHAP 可解释性原理 + 综合运用 7 天所学设计一个完整的 AI 应用系统。

### 上午：可解释性（2h）

| 阅读文件 | 重点内容 | 时间 |
|----------|---------|------|
| `src/models/trainer.py` 的 `ModelWrapper.explain()` | SHAP TreeExplainer 的使用 | 30min |
| `src/models/shap_explainer.py` | SHAP 值的计算和 Top-N 排序 | 30min |
| `src/decision_engine/rule_engine.py` 的 `RuleResult` | reason_code 体系：RC_BL001 = 命中黑名单 | 20min |
| `src/decision_engine/inference_pipeline.py` 的 `_build_result()` | 观察 DecisionResult 如何组装 SHAP + reason_codes | 20min |

**练习 1**（20min）：手写 SHAP 值解读

```python
# 给定一个用户被拒的 SHAP 值，写一段用户友好的解释
shap_values = {
    "overdue_cnt_hist": +0.15,     # 历史逾期 → 推高违约概率
    "on_time_rate": -0.12,         # 按时还款 → 拉低违约概率
    "apply_cnt_7d": +0.08,
    "monthly_income": -0.05,
}

# TODO: 生成用户友好的解释文字（150 字以内）
# 要求: 不透露具体模型参数，但让用户明白主要原因
# 参考信贷行业的监管要求（个人信息保护法）
```

### 下午：综合项目（3h）

**任务**：为"智能客服质检系统"设计完整的 AI 应用方案

```
业务背景：
- 客服对话记录（文本），需要评估客服质量
- 质检维度: 态度、准确性、效率、合规
- 数据源: 对话日志(文本) + 客服信息(工龄、技能组) + 用户评价(1-5星)
```

**要求完成**：

1. **特征设计**（30min）：从客服对话日志中提取至少 8 个特征
2. **PIT 样本构建**（20min）：如何避免时间泄漏？
3. **规则+模型融合**（30min）：设计四层决策架构
   - Layer 1: 合规红线（说了违禁词 → 直接不合格）
   - Layer 2: NLP 模型评分
   - Layer 3: 融合判定
   - Layer 4: 策略（警告/培训/扣绩效）
4. **监控+熔断**（20min）：设计质检模型的监控指标
5. **降级**（20min）：NLP 模型超时 → 切纯规则模式
6. **LLM 应用**（30min）：
   - NL2SQL: "上周哪个客服的投诉率最高？"
   - RAG: 客服 QA 知识库
   - LangGraph: 申诉工作流（被扣绩效 → 提交申诉 → 主管审核 → AI辅助判责）
7. **可解释性**（20min）：为什么这个对话被判为不合格？

### 晚上：回顾总结（1h）

完成一周自评表：

| 能力 | Day 1 | Day 7 | 提升 | 面试话术 |
|------|-------|-------|------|---------|
| PIT 样本构建 | /5 | /5 | | |
| 特征工程 | /5 | /5 | | |
| 规则+模型融合 | /5 | /5 | | |
| 评估+监控+熔断 | /5 | /5 | | |
| 降级容错 | /5 | /5 | | |
| LLM 应用(NL2SQL/RAG/LangGraph) | /5 | /5 | | |
| 可解释性+合规 | /5 | /5 | | |

### 产出物
- [ ] SHAP 解读文字（150 字）
- [ ] 智能客服质检系统完整设计方案（文档）
- [ ] 核心代码框架
- [ ] 自评表

---

## 学习资源索引

| 资源 | 路径 |
|------|------|
| 项目推理代码 | `credit_risk_control_system/src/decision_engine/` |
| 项目模型代码 | `credit_risk_control_system/src/models/` |
| 项目监控代码 | `credit_risk_control_system/src/monitoring/` |
| 项目服务代码 | `credit_risk_control_system/src/services/` |
| 项目数据代码 | `credit_risk_control_system/src/data/` |
| Schema/DDL | `credit_risk_control_system/config/` |
| AI 能力文档 | `study/跨业务通用的AI应用开发能力.md` |
| 数仓能力文档 | `study/跨业务通用数据仓库开发能力.md` |
| 流转追踪文档 | `study/模拟数据的完整项目流转过程.md` |
| 角色分析文档 | `study/AI应用开发工程师的工作体现.md` |
