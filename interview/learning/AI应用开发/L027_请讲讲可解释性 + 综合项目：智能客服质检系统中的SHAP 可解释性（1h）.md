---
id: L027
source: learning
category: AI应用开发
title: 请讲讲可解释性 + 综合项目：智能客服质检系统中的SHAP 可解释性（1h）
generated: 2026-07-23T15:41:19.861614
---

# 请讲讲可解释性 + 综合项目：智能客服质检系统中的SHAP 可解释性（1h）

> 来源: 学习复习计划 | 分类: AI应用开发

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