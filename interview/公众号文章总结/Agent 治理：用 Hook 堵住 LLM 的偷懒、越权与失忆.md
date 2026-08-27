# Agent 治理：用 Hook 堵住 LLM 的偷懒、越权与失忆

> 核心观点：Prompt 是软约束，不是安全边界。能用确定性兜底的，别交给模型。框架 Hook 层是 Agent 治理的最后一道物理防线。


## 一、问题的根因：三类"Prompt 管不住"的行为

### 从两个真实案例说起

| 案例 | 问题 | 后果 |
|------|------|------|
| 案例一 | Agent 改写 1200 行长 SQL 时"偷懒"，中间跳过一大段写了省略号 | 残缺脚本上线，下游几十张表数据算错 |
| 案例二 | Agent 还在"方案设计"阶段就径直调了发布工具 | 未确认的表结构被推上生产 |

**根因不是模型能力不够，而是三种系统性问题：**

| 问题类型 | 表现 | 根因 |
|----------|------|------|
| **偷懒** | 处理长脚本时截断、占位略写、跳步骤、token 耗尽 | 长文本物理上超出 token 预算 |
| **越权** | 发布/回刷/冻结等危险操作不打招呼直接执行 | 模型无法区分"查询"和"发布"的可逆性差异 |
| **失忆** | 改完表不查下游风险、产出了图不告诉用户 | 模型追求最短路径，不会主动给自己加检查步骤 |

> **"在 prompt 里多写几句 ⚠️ 禁止"根本管不住。** 唯一的解法是在 Agent 框架层，让偷懒和越权的路径代码级强制走不通，让失忆的已知盲区确定性补齐。


## 二、解决方案框架：Hook 链 + 三层护栏

### 2.1 Hook 机制：在关键切面挂载护栏逻辑

Agent 框架在运行的每个关键节点（模型调用前/后、工具调用前/后）暴露出**切面（Hook/Callback）**。把拦截逻辑挂载到这些切面上，到点框架自动回调。

**本文用到的核心切面：**

| 切面 | 触发时机 | 本文用途 |
|------|----------|----------|
| **Before Tool** | 工具真正执行前，可改入参/直接拦截 | 长脚本回写前加载全文、危险操作确认（HITL） |
| **After Tool** | 工具执行后、结果回给 LLM 前，可改返回值 | 长脚本拉取后把内容替换成引用句柄 |
| **Before/After Model** | 每次请求 LLM 前/后 | 响应用户取消等 |
| **Before/After Agent** | 单个 Agent 运行前/后 | 对话持久化等 |

**设计原则：基础设施和推理逻辑解耦**——Hook 切面上的逻辑独立运作，模型的 ReAct 循环不用感知。新增/删除一个 Hook，主流程一行代码都不用改。

### 2.2 三层护栏全景

| 护栏层 | 解决的问题 | 核心机制 |
|--------|-----------|----------|
| **长文本完整性护栏** | 偷懒（截断、略写、残缺） | 读写两侧 offload + 引用句柄 + 强制小步改 |
| **危险操作确认 HITL** | 越权（未确认发布、回刷） | BeforeTool 守卫 + 富交互确认框 |
| **上下文联动闭环** | 失忆（该查的不查） | Hook 采集 → state → Attachment 注入 |


## 三、护栏一：长文本完整性护栏（治"偷懒"）

### 3.1 长 SQL 在哪里被截断、略写

| 阶段 | 偷懒形式 | 后果 |
|------|----------|------|
| **拉取**（US → LLM） | 流式 token 自截断、view 后复印重写、占位略写 | 文件截断成残缺 SQL |
| **写回**（LLM → US） | scriptContent 入参自截断 | 提交残缺脚本，US 平台无校验 |

> **一句话定位**：长产物的偷懒是结构性问题。解法是——把 LLM 必须接触的长内容降到最少、每次接触的窗口压到最小、所有写入路径都做成"小步增量改 + 强制校验"。

### 3.2 根治方案：读写两侧 Offload + 引用句柄

**核心理念：LLM 永远不直接接触脚本全文。**

长内容全文留在沙箱，LLM 上下文里只有一句引用句柄。US 平台 ↔ 沙箱 ↔ LLM 三方各管一段，LLM 只用 `str_replace` 小步改写。

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  US 平台    │ ←→ │   沙箱文件   │ ←→ │    LLM      │
│  (源头/终点) │    │  (中转站)   │    │ (只读句柄)  │
└─────────────┘    └─────────────┘    └─────────────┘
```

**拉取侧（AfterTool Hook - Offload）：**

Hook 拦截到含 `scriptContent` 的响应后，将全文写入沙箱只读快照，响应中替换为引用句柄：

```
<offloaded to /sandbox/order_detail.remote.etl (read-only snapshot, length=37814 chars).
 To start editing, run copy_file(...) first, then str_replace.>
```

**治理前后对比：**

| 治理前 | 治理后 |
|--------|--------|
| 约 3.8 万字符长 SQL 原样进上下文 | 上下文里只剩一句引用句柄 |
| 复印重写到一半 token 耗尽 | 长 SQL 全文留在沙箱只读快照 |
| 输出含占位略写 `-- 其他字段...` | 只走 `str_replace` 小步改 |

**写回侧（BeforeTool Hook - Onload）：**

工具同时声明两个参数——`scriptContent`（内容）和 `scriptFilePath`（路径）。框架 Onload Hook 从沙箱读全文覆盖 `scriptContent`，并在转发前剥离 `scriptFilePath`。下游无感知，协议不用改。

### 3.3 效果数据

| 维度 | 治理前 | 治理后 |
|------|--------|--------|
| 修改任务工具调用输出 token | 每轮重传整段 SQL | **直降约 90%** |
| SQL 复印自截断 | "view→重写"路径下概率近 100% | **物理消除** |
| 写侧失败 | 提交残缺脚本 | **阻断工具调用** |

### 3.4 行业对比

| 工程 | 读侧 | 写侧 | 自动化程度 |
|------|------|------|-----------|
| **ADK** | ✅ save/load API | ❌ 需工具内手动调用 | 非 Hook 层自动拦截 |
| **LangGraph DeepAgents** | ✅ 内置 Large Tool Result Offloading | ❌ 只做读侧 | ✅ 中间件层透明 |
| **Anthropic Claude Code** | ❌ Read 默认 2000 行 | ✅ Edit 强制 str_replace | ❌ 内容全留上下文 |

**核心结论**：ADK 和 LangGraph 都有读侧 offload，但都没有写侧 onload。DECO 的数仓场景有"写长 SQL"的保存工具，必须两端对称 offload，并额外加固：只读快照/工作副本分离、scriptFilePath 框架协议、失败语义非对称（读侧降级、写侧阻断）。


## 四、护栏二：危险操作确认 HITL（治"越权"）

### 4.1 核心原则

> **Prompt 是软约束，不是安全边界。** 任何"做了就回不去"的操作（发布、回刷、冻结/解冻、终止），都必须有一道**代码级强制确认**：没拿到用户明确授权，工具就是不能执行。

**HITL 本质**：一个特殊的 BeforeTool Hook——工具真正执行前，判断"是不是危险操作、用户授权了没"，没授权就阻断。

### 4.2 配置驱动的危险工具守卫

危险工具清单是配置出来的，每个配一个授权标记和确认对话框：

```yaml
deco:
  dangerous-tools:
    - name: packCommit
      required-state: confirm_pack
      hint: "需要用户先选择发布方式"
      confirmation:
        title: "请确认发布方式"
        options:
          - {id: direct, label: "直接发布（免审批）", value: direct}
          - {id: approval, label: "提交审批", value: approval, hasInput: true}
          - {id: draft, label: "保存草稿", value: draft}
```

实际配置了多个危险工具，每个对应不同的授权标记：`confirm_pack`（发布提交）、`confirm_deploy`（触发发布）、`confirm_upsert_datasource`（数据源变更）、`confirm_transfer_task_upsert`（同步任务变更）。同一套 Guard 机制统一管控。

**守门流程：**

```
Agent 调工具 → beforeTool 拦截 → 查危险清单 → 是否已授权？
                                                   ↓
                                              未授权 → 弹确认框 → 用户确认 → state 写入 → 放行
                                              已授权 → 直接放行
```

无论 Agent 是自作主张还是被诱导，只要没有人工确认这一步，`packCommit`/`deployCommit` 在框架层就物理走不通。

### 4.3 行业 HITL 全景

| 框架 | 开箱程度 | 交互模式 | 配置驱动 | 暂停/恢复 |
|------|----------|----------|----------|-----------|
| **ADK ToolConfirmation** | ✅ 布尔确认一行配置 | yes/no | ❌ 写工具代码 | ✅ 原生 |
| **LangGraph HITL** | ✅ interruptOn 配置 | approve/edit/reject | ✅ 映射 | ✅ + checkpoint |
| **Claude Code** | ✅ shell 脚本 | deny/allow/ask | ✅ settings.json | N/A |
| **DECO** | ❌ 需自研 | 多选项+输入控件+变更预览 | ✅ yaml | 自研 |

**自研必要性**：DECO 的场景要求更多——发布前展示变更清单、确认框带参数（选发布方式、填审批人）、危险清单配置驱动、和 SSE 流式协议一体。这四条，ADK 原生和 LangGraph 的 HITL 都不直接覆盖。


## 五、护栏三：上下文联动闭环（治"失忆"）

### 5.1 第三类问题：LLM 的"不作为健忘"

改了 DDL 字段重命名 → 不主动分析下游影响；
Python 产出图表 → 不主动告诉用户图在哪；
表结构变更 → 不主动回查刷新元数据。

**这不是模型能力不够，而是"主动探测 = 额外一次 tool call = 多耗 token"。** 模型天然追求以最少 token 完成任务，不会主动给自己加检查步骤。

### 5.2 范式：Hook 采集 → state → Attachment 注入

核心是把「副作用采集」和「上下文注入」解耦成两段：

```
工具调用 → afterTool Hook 采集事实 → 写 state → 下一轮 Attachment 注入 prompt
```

**优势：**

- **采集是确定性的**：工具调用一定触发 Hook，不靠 LLM"记得去查"
- **注入是时机正确的**：只在下一轮 prompt 注入，不污染当前轮、不增加当前轮 token

| 方案 | 可靠性 | Token 开销 | LLM 偷懒风险 |
|------|--------|-----------|--------------|
| prompt 写"改表后记得分析风险" | ❌ 软约束 | 无额外 | 高——LLM 可能跳过 |
| 单独发一轮"请分析风险" | 🟡 依赖调度 | 额外一轮 | 中——LLM 可能敷衍 |
| **Hook→state→Attachment** | ✅ 确定触发 | 无额外 | 零——不依赖 LLM 自觉 |

### 5.3 案例：RiskAnalysisHook —— 改表后自动注入风险分析

**场景**：Agent 调 `upsertTable` 改了一张表的字段结构。LLM 把"改表"当一次成功的工具调用完成了，不会想到还要接着查改动影响了谁。

**做法**：afterTool Hook 判定"带 tableId 的 upsertTable = 改表"→ 查下游依赖 → 结果写 state → 下一轮 Attachment 注入 prompt。

**LLM 下一轮回复中自然输出：**

```
⚠️ 风险提示：刚刚修改了 dws_order_detail 表的字段，检测到下游影响：
- dws_channel_report (HIGH) — 依赖字段 order_amount
- ads_daily_summary (MEDIUM) — 依赖字段 order_status
建议检查这两张表的 ETL 是否需要同步调整。
```

### 5.4 案例：PythonImageHook —— 自动发现并呈现生成产物

**场景**：Python 脚本产出了一张图表，但 LLM 不知道脚本产出了什么新文件，自然不会主动告诉用户。

**做法**：beforeTool 加文件快照 → afterTool 对比 → 检测新产出图片 → 生成预签名 URL → 写 state → 下一轮以结构化 JSON 注入 → 前端据此渲染内联图片。

用户无需点按钮、不必翻沙箱目录，图直接出现在对话流里。


## 六、Hook 全景：十余个横切逻辑

同一套 Hook 链上，DECO 实际挂了十余个 Hook：

| 分类 | Hook | 挂载点 | 职责 |
|------|------|--------|------|
| **长文本护栏** | TaskScriptOffload/Onload | after/beforeTool | ETL 脚本读写 offload |
| | TableColumnsOffload/Onload | after/beforeTool | 宽表 columns offload |
| | DdlBodyOffload | afterTool | DDL 正文落盘 |
| **危险操作护栏** | DangerousToolGuard | beforeTool | 危险工具拦截+HITL |
| **工具返回处理** | LineageResponseOffload | afterTool | 血缘响应 offload |
| | ToolResponseTruncator | afterTool | 超大返回智能裁剪 |
| | ToolResponseFormatter | afterTool | 工具返回结构化格式化 |
| **可观测&持久化** | ToolCallLogHook | before/afterTool | 记录入参/出参/耗时 |
| | LoggingHook | 多点 | Agent 链路日志 |
| | ConversationPersistenceHook | beforeAgent/afterTool | 对话落库 |
| **前端实时刷新** | SqlExecuteHook | beforeTool | SQL 执行前推文件事件 |
| | CopyFileHook | afterTool | 文件变更推事件 |
| | ReleaseItemCollectorHook | afterTool | 发布条目收集 |
| **Hook→Attachment** | RiskAnalysisHook | afterTool | 改表风险分析 |
| | PythonImageHook | before/afterTool | 检测新产出图片 |


## 七、核心要点速记

### 三层护栏对比

| 护栏 | 解决的问题 | 核心机制 | 关键 Hook 切面 |
|------|-----------|----------|---------------|
| **长文本完整性护栏** | 偷懒（截断、略写、残缺） | Offload + 引用句柄 + 强制小步改 | AfterTool / BeforeTool |
| **危险操作确认 HITL** | 越权（未确认发布、回刷） | BeforeTool 守卫 + 确认框 | BeforeTool |
| **上下文联动闭环** | 失忆（该查的不查） | Hook 采集 → state → Attachment | AfterTool |

### 三个设计原则

1. **Prompt 定意图，Skill 定规矩，框架 Hook 定边界**——能用确定性兜底的，别交给模型
2. **基础设施和推理逻辑解耦**——Hook 切面上的逻辑独立运作，模型的 ReAct 循环不用感知
3. **失败语义非对称**——读侧降级（不阻断）、写侧阻断（杜绝生产事故）

### 一句话总结

> **Prompt 是软约束，不是安全边界。偷懒、越权、失忆这三类问题，在 prompt 里写再多"禁止"也管不住。唯一的解法是在框架 Hook 层做确定性兜底——让偷懒和越权的路径代码级强制走不通，让失忆的已知盲区确定性补齐。**

### 面试回答框架

> Agent 治理的核心问题是三类"prompt 管不住"的行为：长文本偷懒、危险操作越权、上下文失忆。
>
> 解法是在框架 Hook 切面上挂载三层护栏：
> - **长文本护栏**：读写两侧 offload + 引用句柄，让 LLM 永远不直接接触全文，只做小步增量改
> - **HITL 门禁**：BeforeTool 守卫 + 配置驱动的危险工具清单 + 富交互确认框，没拿到用户授权就物理走不通
> - **上下文联动闭环**：Hook 采集事实 → 写 state → 下一轮 Attachment 注入，把"需要 LLM 主动查"降维为"框架自动 push"
>
> 核心原则是：**Prompt 定意图，Skill 定规矩，框架 Hook 定边界——能用确定性兜底的，别交给模型。**