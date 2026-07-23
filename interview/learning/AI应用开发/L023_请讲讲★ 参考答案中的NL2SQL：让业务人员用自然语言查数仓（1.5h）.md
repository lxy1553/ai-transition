---
id: L023
source: learning
category: AI应用开发
title: 请讲讲★ 参考答案中的NL2SQL：让业务人员用自然语言查数仓（1.5h）
generated: 2026-07-23T15:41:19.860989
---

# 请讲讲★ 参考答案中的NL2SQL：让业务人员用自然语言查数仓（1.5h）

> 来源: 学习复习计划 | 分类: AI应用开发

### 1.1 四步骤架构


```
用户: "上周各渠道通过率是多少？"
  │
  ▼
Step 1: Schema Context 注入
  把表结构（表名、列名、COMMENT）作为 System Prompt
  → "表 ads_model_monitor_daily, 列 channel STRING -- 渠道,
     approval_rate DOUBLE -- 通过率, dt STRING -- 日期"

  │
  ▼
Step 2: LLM 生成 SQL (temperature=0.0)
  SELECT channel, AVG(approval_rate) as rate
  FROM ads.ads_model_monitor_daily
  WHERE dt >= '2026-06-30' AND dt <= '2026-07-06'
  GROUP BY channel ORDER BY rate DESC;

  │
  ▼
Step 3: 安全校验（永远不信任 LLM 的输出）
  ✓ 无 DROP/DELETE/INSERT/UPDATE
  ✓ 有 dt 分区过滤（防全表扫描）
  ✓ 是 SELECT 语句

  │
  ▼
Step 4: 执行 → 返回
  APP_IOS: 72%, APP_ANDROID: 65%, H5: 58%

```

### 1.2 为什么数仓工程师天然适合做 NL2SQL

**NL2SQL 的瓶颈不是 LLM 生成 SQL 的能力，而是 Schema Context 的质量。**


```
LLM 能生成:
  SELECT AVG(approval_rate) FROM ads_model_monitor_daily WHERE ...

但它不知道:
  - approval_rate 是"通过率" ← 你的 COMMENT 告诉它的
  - "上周"需要翻译为 dt >= '2026-06-30' AND dt <= '2026-07-06'
  - "渠道"是 channel 列
  - 不能不带 dt 过滤（会全表扫描 10 亿行）

没有好的 COMMENT → LLM 猜错列 → SQL 返回错误结果

```

**COMMENT 是 NL2SQL 的命脉**。你之前在 DDL 里写的每一行 COMMENT，现在都变成了 LLM 的上下文。

### 1.3 核心代码模式


```python
class NL2SQLGenerator:
    def __init__(self, schema_registry):
        self.registry = schema_registry

    def _build_system_prompt(self):
        """从 SchemaRegistry 动态构造 Prompt — COMMENT 在这里发挥作用"""
        tables = self.registry.list_tables()
        parts = []
        for t in tables:
            cols = [f"  {c.name} {c.type} -- {c.description}" for c in t.columns]
            parts.append(f"表 {t.layer}.{t.table_name}:\n" + "\n".join(cols))
        return f"可用表:\n{chr(10).join(parts)}\n只生成SELECT。用dt过滤。"

    def validate_sql(self, sql):
        """三道安全校验 — 永远不信任 LLM"""
        sql_up = sql.upper()
        # 1. 禁危险关键字
        for kw in ['DROP','DELETE','INSERT','UPDATE']:
            if kw in sql_up: return False, f"禁止: {kw}"
        # 2. 必须有分区过滤
        if 'DT' not in sql_up:
            return False, "必须包含 dt 分区过滤"
        # 3. 必须是 SELECT
        if not sql_up.startswith('SELECT'):
            return False, "只允许 SELECT"
        return True, "OK"

```

---