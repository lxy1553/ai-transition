---
id: L111
source: learning
category: LLM与AI工程
title: 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的输出
generated: 2026-07-23T15:41:19.874110
---

# 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的输出

> 来源: 学习复习计划 | 分类: LLM与AI工程

只输出 SQL 代码，不要任何解释。"""

```

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

```

---