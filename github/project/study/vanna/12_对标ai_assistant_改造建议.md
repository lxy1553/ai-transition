# Vanna 学习 12：对标 ai_assistant —— 改造建议（活文档）

> 这是**持续更新**的对标文档。每学完 Vanna 一个部分，就把"区别 → 对照 → 改造建议"追加到这里。
> 目标：把 Vanna 学到的东西，逐步落地到 `credit_risk_control_system/src/ai_assistant/`。
>
> 学习 → 对照 → 改造 → 验证 → 再学习（循环推进）

---

# 一、总览：Vanna vs ai_assistant 现状

## ai_assistant 当前状态（已核实，2026-08）

```
src/ai_assistant/
├── llm_client.py          # LLM 抽象 + MockLLM（有接口雏形）
├── schema_catalog.py      # 指标/表结构目录
├── intent_classifier.py   # ① 意图识别（固定步骤）
├── query_rewriter.py      # ② Query改写
├── retriever.py           # ③ RAG检索（多路+RRF+权限）
├── sql_generator.py       # ④ NL2SQL
├── sql_validator.py       # ⑤ SQL校验
├── query_executor.py      # ⑥ 执行
├── result_explainer.py    # ⑦ 结果解释
├── audit_logger.py        # ⑧ 审计（硬编码调用）
└── pipeline.py            # 固定 8 步 if-else 编排
```

**核心差距**：`pipeline.py` 是 **8 步固定 if-else**（`_handle_indicator_query`），不是 while 循环 + LLM 决定。权限/审计硬编码在 pipeline 里。

## 一句话对比

| | Vanna | ai_assistant |
|---|---|---|
| 流程 | while 循环 + LLM 决定 | 8 步固定 if-else |
| 工具 | ToolRegistry 多工具 | 写死 1 个查数 |
| 权限 | 分层（工具级+transform_args+RLS）| permission.check 判一次 |
| 扩展点 | hook/middleware/workflow | 无 |
| 记忆 | AgentMemory 训练式RAG | 静态 RAG |

---

# 二、已学内容 → 对照 → 改造建议（持续追加）

## 2026-08-14：主干① Agent 循环

### 学到什么
Agent 循环 = `while` + `is_tool_call()` + 结果回喂 + `finish_reason` 控制继续/退出。这是"脚本→Agent"的分水岭。

### 区别
- Vanna：LLM 在循环里**自主决定**要不要调工具、调哪个
- ai_assistant：`_handle_indicator_query` 固定顺序（意图→改写→检索→SQL→校验→执行→解释→审计）

### 改造建议（优先级：★★★ 最高）
把你的 8 步 if-else 改成 while 循环，让"是否查数"由 LLM 决定：

```python
# 改造方向：while 循环 + LLM 决定下一步
while iterations < max_iterations:
    response = llm.send_request(request)           # 问 LLM（带工具schema）
    if response.is_tool_call():                     # LLM 说"要查数"
        for tc in response.tool_calls:
            result = registry.execute(tc)          # 执行工具
            request.add_tool_result(result)        # 结果回喂
    else:
        answer = response.content                  # LLM 直接回答
        break
```

**具体步骤**：
1. `sql_generator`/`executor`/`explainer` 包成 Tool
2. 引入 ToolRegistry，注册这些工具
3. pipeline 改成 while 循环 + is_tool_call 判断
4. 结果回喂（role="tool" 消息）

---

## 2026-08-14：循环外三个扩展点（hook/middleware/workflow）

### 学到什么
Vanna 把灵活性放在循环外：WorkflowHandler（命令拦截）/ LifecycleHook（4 钩子点）/ LlmMiddleware（LLM 调用外层）。

### 区别
- Vanna：配额/日志/权限/脱敏通过 hook 外置，核心干净
- ai_assistant：权限判断（`permission.check`）和审计（`_log`）**硬编码在 pipeline**

### 改造建议（优先级：★★★）
把约束层从 pipeline 抽到 hook：

```python
# 现状（硬编码在 pipeline）
if not self.permission.check(indicator_name, user_role):
    return "无权限..."            # 权限写死在 _handle_indicator_query
self._log(...)                     # 审计写死在 ask

# 改造：4 个 hook 外置约束层
# before_message → 配额/敏感词过滤（可拦截）
# before_tool → 权限（可拦截）
# after_tool → 结果脱敏（可改写）
# after_message → 审计（记录）
```

**具体步骤**：
1. 定义 `LifecycleHook` 接口（仿 Vanna）
2. 把 `permission.check` 移到 before_tool hook
3. 把 `audit.log` 移到 after_message hook
4. 加一个 after_tool 脱敏 hook（手机号打码）

---

## 2026-08-15：权限五层防御模型

### 学到什么
权限是分层防御：①认证 ②授权（功能/数据/指标）③脱敏 ④数据库RLS ⑤审计。transform_args 是表级/行级权限的实现点。

### 区别
| 层 | Vanna | ai_assistant |
|----|-------|-------------|
| ① 认证 | UserResolver | user_role 参数 |
| ② 功能 | user_groups & tool_groups | 无 |
| ② 数据 | transform_args 注入过滤 | 无（查任意表）|
| ② 指标 | 指标平台 | required_role（已有雏形 ✅）|
| ③ 脱敏 | sanitize_tool_parameters | 无 |
| ④ 数据库 | PostgreSQL RLS | 无（SQLite）|
| ⑤ 审计 | audit 框架 | audit_logger（雏形 ✅）|

### 改造建议（优先级：★★）
**先做指标权限 → 已达标**：你的 `indicators.yaml` 有 `required_role`，这是"指标权限层"，比 Vanna 默认还完整。✅

**补数据权限（表级）**：给 executor 加表级校验：
```python
# 现状：query_executor 执行任意 SQL
def execute(self, sql):
    cursor.execute(sql)   # 没有表权限校验

# 改造：执行前校验 SQL 引用的表
def execute(self, sql, user_allowed_tables):
    for t in extract_tables(sql):
        if t not in user_allowed_tables:
            raise PermissionError(f"无权限访问表 {t}")
```

**补脱敏**：audit_logger 已做 user_id 脱敏，加手机号/身份证：
```python
def _mask_user(user_id):
    return user_id[:3] + "***"    # 已有
# 加：结果脱敏（手机号 13812345678 → 138****5678）
```

---

## 2026-08-16：工具三层来源 + 工具清单

### 学到什么
工具分三层：内置（import 即用）、集成（连库）、自定义（业务自写）。一个工具 = name + description + args + execute。

### 区别
- Vanna：12 个内置工具 + ToolRegistry 动态选
- ai_assistant：1 个"查数"能力写死在 pipeline

### 改造建议（优先级：★★）
把 ai_assistant 拆成多个 Tool：
```python
QueryIndicatorTool     # 查指标（复用 sql_generator + executor）
ExplainDefinitionTool  # 解释口径（复用 retriever）
TraceLineageTool       # 血缘追溯（复用 catalog.get_lineage）
VisualizeTool          # 画图（新增）
SaveUsageTool / SearchUsageTool  # 记忆（新增）
```

---

## 2026-08-16：业务规则分四层

### 学到什么
业务规则分四层：①能力（Tool）②数据（DB）③约束（hook）④配置（AgentConfig）。hook 只负责约束层。

### 对照 ai_assistant
```python
# ① 能力：sql_generator + executor（查数）→ 能力层 ✅
# ② 数据：indicators.yaml 的 required_role → 数据层 ✅
# ③ 约束：permission.check（写死在 pipeline）→ 约束层，该进 hook ⬜
# ④ 配置：settings.yaml → 配置层 ✅
```

### 改造建议
**核心认知**：你的 pipeline 问题不是"业务写死在主干"，而是"**约束层（权限判断）和主干混在一起**"。改造 = 约束层抽到 hook，能力/数据/配置保持现状。

---

## 2026-08-17：主干③ Registry 分派

### 学到什么
Registry 是工具中枢：注册、查找、执行（带完整安全关卡）。execute 六步 = 找工具→权限→参数校验→transform_args→审计→执行。任何失败返回 ToolResult(success=False)，不抛异常。

### 区别
- Vanna：所有工具经 Registry.execute，权限/校验/审计内置
- ai_assistant：`permission.check` 硬编码在 `_handle_indicator_query`，无统一工具入口

### 改造建议（优先级：★★★）
```python
# 现在（pipeline 硬编码权限）
if not self.permission.check(indicator_name, user_role):
    return "无权限"

# 改造：权限移到 Registry（register_local_tool + transform_args）
registry = CreditToolRegistry()
registry.register_local_tool(QueryIndicatorTool(...), access_groups=["analyst"])
result = await registry.execute(tool_call, context)   # 内部自动权限/校验/审计
```

---

## 2026-08-17：system_prompt 构建

### 学到什么
构建流程：get_schemas(user) 过滤有权工具 → build_system_prompt 拼角色+日期+工具+指令 → _build_llm_request 打包。get_schemas 决定"LLM 能做什么"，build_system_prompt 决定"怎么做事"。

### 区别
- Vanna：有明确 SystemPromptBuilder（core/system_prompt/default.py）
- ai_assistant：pipeline 无单独构建器，直接进查询逻辑

### 改造建议（优先级：★★）
```python
# 加 build_system_prompt(user, tools) 方法
def build_system_prompt(self, user, tools):
    return (
        f"你是信贷数据分析助手，今天日期 {today}。"
        f"你能用这些工具：{', '.join(tool_names)}"
        "行为准则：先查 Schema 再生成 SQL，无权指标不查询"
    )
# 用户无权指标 → get_schemas 过滤 → 不进 prompt → LLM 不知道
```

---

## 2026-08-17：Tool 抽象详细（两类工具）

### 学到什么
工具分"执行型"（RunSqlTool 查数）和"记忆型"（SaveQuestionToolArgsTool 存模式）。记忆型通过 context.agent_memory 读写记忆——训练式 RAG 基础。

### 区别
- Vanna：执行型 + 记忆型工具都有，ToolRegistry 动态选
- ai_assistant：只有查数能力，无记忆工具

### 改造建议（优先级：★★）
拆成多个 Tool：QueryIndicatorTool（查数）+ ExplainDefinitionTool（解释）+ TraceLineageTool（血缘）+ SaveUsageTool（记忆）。

---

## 2026-08-17：信贷业务 Hook 示例（14 文件）

### 学到什么
信贷场景 4 钩子点：before_message（隐私/配额）、before_tool（大额审批/敏感工具）、after_tool（PII 脱敏）、after_message（审计）。

### 区别
- ai_assistant：权限/审计硬编码，无 hook
- Vanna：hook 插槽真实，业务规则要自写

### 改造建议（优先级：★★）
```python
lifecycle_hooks=[
    CreditQuotaHook(),          # 配额
    CreditPrivacyFilterHook(),  # 隐私
    LargeLoanApprovalHook(),    # 大额审批
    MaskPiiHook(),              # 脱敏
    CreditAuditHook(),          # 审计
]
```

---

# 三、改造优先级总表（按价值排序）

| 优先级 | 改造项 | 学到自 | 工作量 | 影响 |
|--------|--------|--------|--------|------|
| ★★★ | pipeline → while 循环 | 主干① | 中 | 从脚本→Agent 的质变 |
| ★★★ | 权限/审计抽到 hook | 扩展点 | 中 | 约束层外置，核心干净 |
| ★★ | 加表级权限校验 | 权限五层 | 小 | 数据安全 |
| ★★ | 拆多个 Tool | 工具清单 | 中 | LLM 能精确调用 |
| ★ | 加结果脱敏 | 权限五层 | 小 | 隐私保护 |
| ★ | 加记忆（训练式RAG）| 主干⑦（未学）| 大 | 效果提升 |

> 标注"未学"的：等学到主干⑦（记忆）再补。

---

# 四、验证方式（改完怎么确认）

每个改造做完，跑一遍验证：
```bash
cd credit_risk_control_system
python3 scripts/eval_qa.py   # 评测：意图/指标/行为准确率
python3 scripts/demo_qa.py   # 演示：看链路能不能跑通
```

**改造后评测指标对比**：
| 指标 | 改造前 | 改造后 |
|------|--------|--------|
| 意图识别准确率 | 98% | （改造后测）|
| 指标解析准确率 | 100% | |
| 行为判定准确率 | 100% | |

---

# 五、更新日志

| 日期 | 追加内容 |
|------|---------|
| 2026-08-14 | 主干①循环 + 扩展点 对照改造 |
| 2026-08-15 | 权限五层 对照改造 |
| 2026-08-16 | 工具三层 + 业务规则四层 |
| 2026-08-17 | 主干③ Registry + system_prompt + Tool 详细 + 信贷 Hook |

> 持续更新：每学完 Vanna 一部分，回来追加"区别 → 对照 → 改造建议 → 验证"。
