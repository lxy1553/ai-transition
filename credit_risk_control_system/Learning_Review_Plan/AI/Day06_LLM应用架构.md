 # Day 06：LLM 应用架构 — NL2SQL + RAG + LangGraph

> 目标：理解 LLM 不是"调个 API"，而是"设计架构"。掌握 NL2SQL 四步骤、RAG 切片策略、LangGraph 状态机。

---

## 一、NL2SQL：让业务人员用自然语言查数仓（1.5h）

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

## 二、RAG：让 LLM 基于项目文档回答（1h）

### 2.1 RAG 的知识库 = 你的项目文档

```
问题: "night_ops_ratio_30d 超过多少算异常？"

RAG 检索:
  → config/schemas/dws_wide_table.yaml: "★ 深夜操作占比(22-05时)。>60%→高度可疑"
  → config/rules/credit_policy.yaml: "night_ops_ratio_30d > 0.6 → MANUAL_REVIEW"
  → 01_system_architecture.md: "风控强特征，欺诈团伙常在夜间批量操作"

LLM 综合:
  "night_ops_ratio_30d 超过 60% 触发人工审核(RC_BH001)。
   正常范围 < 30%。> 60% 是高度可疑信号，因为欺诈团伙常在夜间操作。"
```

### 2.2 切片策略（比向量模型更重要）

```
错误做法: 每 500 字切一刀
  文档: "特征分为三类: 申请画像、行为衍生、还款表现。申请画像包括..."
  一刀切在 "申请画像包括" 后面 → 丢失了具体特征列表

正确做法: 按语义边界切
  YAML: 每个顶级 key 一个 chunk（一个表定义 = 一个片段）
  SQL:  每个 CREATE TABLE 一个 chunk（一张表的完整 DDL）
  MD:   每个 ## 标题一个 chunk（一个章节一个片段）

为什么？检索时返回的是"完整片段"，不是"半句话"
```

---

## 三、LangGraph：多步骤 AI 工作流（40min）

### 3.1 信贷审批的状态机

```
rule_check ──REJECT──→ rejection_letter(LLM) ──→ END
    │
    └──PASS──→ model_score ──APPROVE──→ disburse ──→ END
                    │
                    ├──REJECT──→ rejection_letter(LLM)
                    └──MANUAL_REVIEW──→ request_docs(LLM) ──→ END
                                            ↑
                                    用户上传材料后恢复
```

### 3.2 为什么用 LangGraph 而不是手写 if-else

```
手写 if-else 的问题:
  改流程 = 改代码 = 改 if-else 分支 = 容易出错
  异步操作(等用户上传材料) → 状态需要自己持久化
  流程可视化 → 要另外画图

LangGraph:
  加一个节点 = graph.add_node("new_step", new_step_fn)
  异步状态 = checkpointer 自动处理
  可视化 = graph.get_graph().draw_mermaid_png()
```

---

## 四、动手练习（1.5h）

### 练习 1：实现 NL2SQL 的 validate_sql()（30min）

```python
# ★ 参考答案
FORBIDDEN_KW = ['DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE',
                'ALTER', 'CREATE', 'GRANT', 'REVOKE']

def validate_sql(sql: str) -> tuple[bool, str]:
    sql_up = sql.upper().strip()

    # 校验1: 禁止危险关键字
    for kw in FORBIDDEN_KW:
        if kw in sql_up:
            return False, f"禁止关键字: {kw}"

    # 校验2: 必须是 SELECT
    if not sql_up.startswith('SELECT'):
        return False, "只允许 SELECT"

    # 校验3: 必须有分区过滤（dt）
    if 'DT' not in sql_up:
        return False, "必须包含 dt 分区过滤（防全表扫描）"

    return True, "OK"


# 5 个测试用例
tests = [
    ("SELECT * FROM t WHERE dt='2026-07-01'", True, "正常查询"),
    ("DROP TABLE t", False, "危险关键字"),
    ("SELECT * FROM t", False, "无 dt 分区"),
    ("  select channel, avg(rate) from t where dt > '2026-07-01'", True, "小写SELECT"),
    ("DELETE FROM t WHERE dt='2026-07-01'", False, "DELETE 应拦截"),
]
for sql, expected, desc in tests:
    ok, msg = validate_sql(sql)
    assert ok == expected, f"[{desc}] {sql} → {msg}"
print("✅ 所有测试用例通过")
```

### 练习 2：设计 RAG 的切片策略（30min）

```
★ 参考答案:

| 文件 | 切片策略 | chunk 数 | metadata |
|------|---------|:--------:|---------|
| ods_tables.yaml | 按顶级 key 切（ods_application/ods_user_behavior/ods_repayment 各一段） | 3 | source, table_name |
| dws_wide_table.yaml | 按 category 切（profile/behavior/repayment 三大类，每类一个 chunk） | 3 | source, category |
| credit_policy.yaml | 按 rule group 切（hard_reject/risk_assessment/credit_limit 各一段） | 3 | source, group_name |
| 流转过程.md | 按 ## 标题切（每站一个 chunk） | 5 | source, chapter |

YAML 按顶级 key 切的原因:
  → 每个 key 是一段自包含的定义（一张表、一条规则）
  → key 本身是 chunk 的"标题"，LLM 能理解这段在说什么

MD 按 ## 标题切的原因:
  → 文档作者的标题层级 = 自然语义边界
  → 按 # 切太粗（全文），按 ### 切太碎（可能不完整）
  → ## 是"章节"级别，刚好自包含

chunk metadata 必须包含 source 的原因:
  → LLM 引用时可以说"根据 ods_tables.yaml 中的描述..."
  → 来源可追溯 = 可信度可验证
```

### 练习 3：画出审批工作流的状态图（20min）

```
★ 参考答案（ASCII 状态图）:

               ┌─────────────────────────┐
               │    rule_check (普通)      │
               │    规则引擎检查           │
               └────────┬───────────────┘
                        │
               ┌────────┴────────┐
               │ 条件: 是否硬拒绝? │
               └────────┬────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    REJECT            PASS             (通往下一节点)
        │               │
        ▼               ▼
┌─────────────────┐  ┌─────────────────────────┐
│ rejection_letter│  │    model_score (普通)    │
│ (LLM 节点)       │  │    XGBoost 模型推理      │
│ 生成拒绝函       │  └────────┬────────────────┘
└────────┬────────┘           │
         │            ┌────────┴────────┐
         │            │ 条件: 评分判定?  │
         │            └────────┬────────┘
         │                     │
         │        ┌────────────┼────────────┐
         │        │            │            │
         │    APPROVE      MANUAL      REJECT
         │        │         REVIEW         │
         │        ▼            │            │
         │  ┌──────────┐       │            │
         │  │ disburse  │       │            │
         │  │ (普通)    │       ▼            │
         │  │ 放款     │  ┌──────────────┐  │
         │  └──────────┘  │ request_docs  │  │
         │                │ (LLM 节点)     │──┤
         │                │ 生成补充材料清单│  │
         │                └──────────────┘  │
         └──────────────────────────────────┘
                              │
                              ▼
                           ┌──────┐
                           │ END  │
                           └──────┘

LLM 节点 vs 普通函数节点的区别:
  LLM 节点: 需要调用大模型（如生成拒绝函、生成材料清单）
    特点: 有延迟、不稳定（可能输出不符合格式）
    应对: temperature=0 保证确定性、失败后重试

  普通节点: 纯计算/规则（如规则引擎、模型推理）
    特点: 低延迟、确定性的
    优势: 没有 LLM 的"幻觉"风险和延迟问题
```

---

## 五、今天要点

```
NL2SQL: Schema Context 的质量 > LLM 的能力
  → 你写的 COMMENT 就是 LLM 理解业务的唯一途径

RAG: 切片策略 > 向量模型
  → 按语义边界切 > 按固定长度切

LangGraph: 状态机 + 条件路由
  → 解决"多步骤 AI 工作流"的结构化问题
```

---

## 六、检查清单

- [ ] 能说出 NL2SQL 的四步骤
- [ ] 实现了 validate_sql() 并写了测试用例
- [ ] 能解释"为什么 COMMENT 是 NL2SQL 的命脉"
- [ ] 能解释 YAML 和 MD 的切片策略差异
- [ ] 画出了审批工作流的状态图
