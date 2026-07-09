# Day 07：可解释性 + 综合项目：智能客服质检系统

> 目标：理解 SHAP 可解释性原理 + 综合运用 7 天所学设计完整 AI 应用。

---

## 一、SHAP 可解释性（1h）

### 1.1 为什么需要 SHAP？

```
用户问: "为什么拒绝我的贷款？"

不好的回答: "模型评分低于阈值"  ← 等于没说
好的回答: "主要原因——历史逾期2次(影响最大)，近7天申请3次(次要)，深夜操作占比40%(偏高等)"
           ← SHAP 值告诉你的
```

### 1.2 项目中的 SHAP 实现

打开 `src/models/trainer.py` 的 `ModelWrapper.explain()`：

```python
class ModelWrapper:
    def explain(self, feature_vector, top_n=10) -> dict:
        """
        返回每个特征对"这个用户"的 SHAP 贡献值。

        和 feature_importance 的区别:
        - feature_importance: 全局性——"哪个特征整体最重要"
        - SHAP:              局部性——"对这个用户，哪个特征贡献最大"

        SHAP 值含义:
        +0.15 → 推高违约概率 0.15 → 这个特征增加了风险
        -0.10 → 拉低违约概率 0.10 → 这个特征降低了风险
        """
        shap_vals = self._shap.shap_values(dmatrix)[0]
        return dict(sorted(
            zip(self.feature_names, shap_vals),
            key=lambda x: abs(x[1]), reverse=True  # 按贡献绝对值排序
        )[:top_n])
```

### 1.3 RuleResult 的 reason_code 体系

```python
# 规则引擎的输出——确定性原因
RuleResult(
    rule_id="MULTI_HEAD_SPIKE",
    decision=Decision.MANUAL_REVIEW,
    reason_code="RC_MH001",         # ← 唯一编码
    reason_desc="近7天多头借贷次数>=5"  # ← 人类可读
)

# SHAP——概率性贡献
{"overdue_cnt_hist": +0.15, "night_ops_ratio": +0.08}

# 给用户看 reason_desc（"多头借贷次数过多"）
# 给分析师看 SHAP（"overdue_cnt_hist 贡献 +0.15"）
# 两者互补，不是替代
```

---

## 二、综合项目：智能客服质检系统（3h）

### 2.1 业务理解

```
业务: 智能客服质检系统

需求: 自动评估客服对话质量，减少人工抽检工作量

数据源:
  - 对话记录(文本): "用户: 我的订单怎么还没到？ 客服: 我帮您查一下..."
  - 客服信息: 工龄、技能组、历史质检分数
  - 用户评价: 1-5 星、评价标签（态度好/解决问题/态度差）
  - 订单信息: 订单状态、物流状态、金额

质检维度:
  - 态度: 是否礼貌、是否主动道歉
  - 准确性: 回答是否正确、是否遗漏关键信息
  - 效率: 对话轮次、解决时长
  - 合规: 是否说了违禁词（如承诺赔偿金额）
```

### 2.2 任务清单

**任务 1: 特征设计（30min）**

设计至少 10 个特征，分为三类：

```python
# 对话文本特征（NLP 提取）:
f1_conversation_turns: int       # 对话轮次 → 越高越差?
f2_avg_reply_time_sec: float     # 平均回复间隔
f3_customer_anger_score: float   # 用户情绪愤怒程度 (NLP)
f4_has_apology: bool             # 客服是否道歉
f5_keyword_compliance_hits: int  # 违禁词命中次数

# 客服画像特征:
f6_tenure_days: int             # 工龄
f7_historical_quality_score: float # 历史质检均分

# 上下文特征:
f8_order_complexity: str         # 订单状态(退款/换货/查询 → 难度不同)
f9_conversation_time_hour: int   # 对话时间（深夜→客服可能疲劳）
f10_user_vip_level: int          # 用户等级（VIP → 更难处理）
```

**任务 2: PIT 样本构建（20min)**

```python
# 质检的"时间泄漏"风险:
# 特征: 对话结束时的所有信息（包括用户评价！）
# 标签: 质检是否合格
# 如果特征里包含了用户评价 → 模型学会了"差评=不合格"→ 毫无意义

# 正确做法: 特征只用对话结束时的客观信息（不含用户评价）
# 标签用后续的专家抽检结果
```

**任务 3: 规则+模型融合（30min）**

```
Layer 1 — 合规红线:
  说了违禁词 → 直接不合格（不需要跑模型）
  举例: "我保证赔偿"（客服不能承诺赔偿金额）

Layer 2 — NLP 模型评分:
  BERT Fine-tune 对对话文本打分 [0, 1]

Layer 3 — 融合:
  新客服(工龄<30天) + 模型分 0.4-0.6 → 人工复核(新人保护)
  老客服 + 模型分 0.4 → 不合格(对老人不宽容)

Layer 4 — 策略:
  不合格 → 通知主管 + 扣绩效 + 培训提醒
  人工复核 → 进入质检员队列
```

**任务 4: 监控+熔断（15min）**

```
质检模型监控指标:
  - 不合格率日环比 > 50% → 告警（可能是模型偏差或客服整体质量崩溃）
  - 人工复核率 > 30% → 模型区分力不足
  - 平均评分日环比 > 0.2 → 分布漂移

熔断: 不合格率突增 80% → 暂停自动质检，全部转人工
```

**任务 5: LLM 应用设计（30min）**

```
NL2SQL: 运营主管问"本周哪个客服的投诉率最高？"
  → 查询 ads_customer_service_daily 表

RAG: 客服问"用户说货没到，我应该怎么处理？"
  → 知识库: 客服FAQ + 退换货政策 + 物流异常SOP
  → 检索最相关的处理流程
  → 生成建议话术

LangGraph: 申诉工作流
  客服被扣绩效 → 提交申诉 → 主管审核 → AI 辅助判责(LLM分析对话记录)
  → 判定: 维持/撤销
```

**任务 6: 可解释性（15min）**

```
客服: "为什么我的对话被判不合格？"

系统输出:
  评分: 0.32/1.0 → 不合格

  SHAP 主要贡献:
  1. keyword_compliance_hits=3 → +0.18（说了 3 个违规词: "保证""绝对""最"）
  2. customer_anger_score=0.78 → +0.12（用户情绪非常愤怒）
  3. conversation_turns=25 → +0.08（对话轮次过长）
  4. has_apology=False → +0.05（没有道歉）
  5. historical_quality_score=0.85 → -0.06（历史表现良好，拉低了不合格概率）
```

---

## 三、自评表（30min）

| 能力 | Day 1 自评 | Day 7 自评 | 提升 | 面试怎么说 |
|------|----------|----------|------|-----------|
| PIT 样本构建 | /5 | /5 | | "设计过严格防时间泄漏的样本生成" |
| 特征工程 | /5 | /5 | | "能对任意事件日志提取预测特征" |
| 规则+模型融合 | /5 | /5 | | "设计过四层决策架构" |
| 评估+监控+熔断 | /5 | /5 | | "搭建过完整 MLOps 闭环" |
| 降级容错 | /5 | /5 | | "设计过多层降级路径，永不停服" |
| LLM 应用 | /5 | /5 | | "NL2SQL+RAG+LangGraph 全链路" |
| 可解释性+合规 | /5 | /5 | | "SHAP+reason_code 双轨追溯" |

---

## 四、产出物

- [ ] 客服质检系统的完整设计方案（文档）
- [ ] 10 个特征的定义和来源
- [ ] 四层决策架构图
- [ ] LLM 应用方案（NL2SQL + RAG + LangGraph）
- [ ] SHAP 可解释性示例输出
- [ ] 自评表

---

## 五、一周回顾

两个 7 天计划到此结束。回顾一下你完成的所有产出物：

```
数仓工程师 7 天产出:
  Day 1: 电商 ODS 定义 + DDL
  Day 2: 电商清洗函数 + 扣分权重设计
  Day 3: 电商消费画像宽表 + 聚合函数选择
  Day 4: SchemaRegistry.validate_dataframe() + 血缘图
  Day 5: 电商脱敏策略 + 生产级 DDL
  Day 6: 分区策略 + 广告投放数据产品
  Day 7: ★ 在线教育平台完整数仓

AI 应用工程师 7 天产出:
  Day 1: PIT 样本构建 + 时间泄漏检测器
  Day 2: 电商行为特征工程 + ratio vs sum 分析
  Day 3: 四个版本的决策融合 + 内容审核分层
  Day 4: 手写 KS/PSI + 推荐系统监控
  Day 5: 三层降级代码 + 搜索系统降级
  Day 6: validate_sql() + RAG 切片策略 + LangGraph 状态图
  Day 7: ★ 智能客服质检系统完整 AI 应用
```

这些产出物就是你面试时可以说的"项目经验"——不只是"我做过信贷风控"，而是"我能把信贷风控中的方法论应用到任何业务"。
