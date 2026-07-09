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
def validate_sql(sql: str) -> tuple[bool, str]:
    """
    安全校验 — 永远不信任 LLM 的输出。

    三道检查:
    1. 禁止 DROP/DELETE/INSERT/UPDATE/ALTER/CREATE
    2. 必须包含 dt 或 WHERE dt（分区过滤）
    3. 必须以 SELECT 开头

    测试:
    >>> validate_sql("SELECT * FROM t WHERE dt='2026-07-01'")
    (True, 'OK')
    >>> validate_sql("DROP TABLE t")
    (False, '禁止关键字: DROP')
    >>> validate_sql("SELECT * FROM t")
    (False, '必须包含分区过滤 dt')
    """
    pass

# 写 5 个测试用例，覆盖正常和异常场景
```

### 练习 2：设计 RAG 的切片策略（30min）

```
你有以下文档需要索引为 RAG 知识库:
  - config/schemas/ods_tables.yaml (3张表的定义)
  - config/schemas/dws_wide_table.yaml (17个特征的定义)
  - config/rules/credit_policy.yaml (10条规则)
  - study/模拟数据的完整项目流转过程.md (长文档)

问题:
1. 每个文件应该用什么切片策略？
2. YAML 按什么切？MD 按什么切？
3. 切完后每个 chunk 应该带什么 metadata？
```

### 练习 3：画出审批工作流的状态图（20min）

用 ASCII 或 Mermaid 画出信贷审批的 LangGraph 状态图，标注：
- 每个节点的名称和职责
- 条件路由的判定条件
- LLM 节点 vs 普通函数节点的区别

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
