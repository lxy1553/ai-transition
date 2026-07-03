# Day 57 - 数据质量 + 错误治理报告

**生成时间：** 2026-06-11T16:38:33.528956+08:00

---

## 一、质量检查汇总

| 指标 | 值 |
|------|-----|
| 整体质量状态 | **quality_blocked** |
| 路由决策 | **blocked_answer** |
| 阻断规则数 | 2 |
| 警告规则数 | 8 |
| 正常规则数 | 0 |
| Agent 可信度 | 0.30 |
| 决策原因 | 存在 2 条阻断级质量问题：DQ-006, DQ-009 |

**阻断规则：** DQ-006, DQ-009

**警告规则：** DQ-001, DQ-002, DQ-003, DQ-004, DQ-005, DQ-007, DQ-008, DQ-010

---

## 二、质量规则检查明细

| 规则 ID | 规则名称 | 分类 | 风险等级 | 仓库类型 | 质量状态 |
|---------|----------|------|----------|----------|----------|
| DQ-001 | 审批结果字段空值检查 | 空值 | high | offline | 🟡 quality_warning |
| DQ-002 | 申请事件重复落库检查 | 重复 | high | realtime | 🟡 quality_warning |
| DQ-003 | 事件乱序检查（结果先于明细） | 乱序 | medium | realtime | 🟡 quality_warning |
| DQ-004 | 离线分区延迟检查 | 延迟 | high | offline | 🟡 quality_warning |
| DQ-005 | 补偿任务完成状态检查 | 补偿 | high | offline | 🟡 quality_warning |
| DQ-006 | 幂等写入失败检查 | 幂等 | high | both | 🔴 quality_blocked |
| DQ-007 | 离线/实时状态字段不一致检查 | 状态不一致 | high | both | 🟡 quality_warning |
| DQ-008 | 实时窗口晚到数据检查 | 晚到数据 | medium | realtime | 🟡 quality_warning |
| DQ-009 | 空分区检查 | 空分区 | critical | offline | 🔴 quality_blocked |
| DQ-010 | 窗口数据倾斜检查 | 数据倾斜 | medium | realtime | 🟡 quality_warning |

---

## 三、错误分类与修复建议

### 需阻断（quality_blocked）

- **DQ-006 幂等写入失败检查**（幂等）
  - 风险等级：high
  - 触发条件：模拟触发：同一 event_id/流水号 在目标表中出现多行，且关键字段不一致，说明去重逻辑未生效...
  - 处理动作：阻断回答：离线日报和实时快照差异不可忽略时，不给出确定结论，明确说明数据不一致并给出排查项

- **DQ-009 空分区检查**（空分区）
  - 风险等级：critical
  - 触发条件：模拟触发：查询指定分区的行数为 0，而前一天同分区的行数正常（>0）...
  - 处理动作：阻断回答：明确告知分区为空，不给任何指标值，说明原因、影响范围和排查建议


### 需降级（quality_warning）

- **DQ-001 审批结果字段空值检查**（空值）
  - 风险等级：high
  - 触发条件：模拟触发：核心业务字段（approval_result、risk_level、loan_amount）NULL 比例超过 5%...
  - 处理动作：降级回答：在回答中标注空值比例，说明指标可能偏低/偏高，并给出数据完整性修复建议

- **DQ-002 申请事件重复落库检查**（重复）
  - 风险等级：high
  - 触发条件：模拟触发：同一 apply_id + event_type 在同一窗口内出现超过 1 次，去重后差异大于 3%...
  - 处理动作：降级回答：同时给出原始值和去重值，说明重复可能原因（幂等失败、重放），标注差异幅度

- **DQ-003 事件乱序检查（结果先于明细）**（乱序）
  - 风险等级：medium
  - 触发条件：模拟触发：event_result 时间戳早于 event_detail 时间戳，或同一 apply_id 的 event 顺序颠...
  - 处理动作：降级回答：说明事件顺序存在乱序，给出窗口内已确认的事件数，建议拉大窗口重查

- **DQ-004 离线分区延迟检查**（延迟）
  - 风险等级：high
  - 触发条件：模拟触发：当天期望分区（如 dt={today}）的 ETL 任务未完成，或分区行数相比前一天同分区偏差超过 30%...
  - 处理动作：降级回答：如果分区未产出则明确说明并给出最新可用分区数据；如果行数偏差则标注并给出修正参考

- **DQ-005 补偿任务完成状态检查**（补偿）
  - 风险等级：high
  - 触发条件：模拟触发：存在针对查询分区的未完成补偿任务（回补/修正），或补偿任务状态为 running/failed...
  - 处理动作：降级回答：标注当前分区存在未完成补偿任务，给出当前快照值和预计补偿后范围

- **DQ-007 离线/实时状态字段不一致检查**（状态不一致）
  - 风险等级：high
  - 触发条件：模拟触发：同一 apply_id 在离线表和实时表中的状态字段（如 loan_status、risk_flag）不一致...
  - 处理动作：降级回答：同时给出离线状态和实时状态，说明差异原因（时效差异、补偿差异），给出建议参考哪个来源

- **DQ-008 实时窗口晚到数据检查**（晚到数据）
  - 风险等级：medium
  - 触发条件：模拟触发：事件实际发生时间与写入时间之差超过窗口允许的延迟阈值（如 5 分钟），且该事件影响窗口聚合结果...
  - 处理动作：降级回答：标注窗口内可能未包含的晚到数据量，说明当前窗口指标可能偏保守

- **DQ-010 窗口数据倾斜检查**（数据倾斜）
  - 风险等级：medium
  - 触发条件：模拟触发：单个窗口内某个 channel / product_type 的事件量占比超过历史均值的 3 倍标准差...
  - 处理动作：降级回答：标注倾斜维度，拆开正常维度和异常维度分别说明，避免聚合值被单维度异常主导

---

## 四、Bad Case 回归验证

| Bad Case | 关联规则 | 关联 Day 56 场景 | 预期状态 | 实际状态 | 回归结果 |
|----------|----------|-----------------|----------|----------|----------|
| BC-001 空分区：日报指标查询 | DQ-009 | 空分区查询 | quality_blocked | quality_blocked | ✅ |
| BC-002 重复事件：实时申请量虚高导致假告警 | DQ-002 | 告警误报 | quality_warning | quality_warning | ✅ |
| BC-003 分区延迟：日报指标偏低 | DQ-004 | 实时延迟 | quality_warning | quality_warning | ✅ |
| BC-004 补偿未完成：逾期率口径差异 | DQ-005 | 口径冲突 | quality_warning | quality_warning | ✅ |
| BC-005 空值：风控拒绝率失真 | DQ-001 | 有界解释 | quality_warning | quality_warning | ✅ |
| BC-006 幂等失败：实时与离线日报不一致 | DQ-006 | 口径冲突 | quality_blocked | quality_blocked | ✅ |
| BC-007 乱序事件：窗口指标异常 | DQ-003 | 实时延迟 | quality_warning | quality_warning | ✅ |
| BC-008 晚到数据：告警延迟 | DQ-008 | 实时延迟 | quality_warning | quality_warning | ✅ |
| BC-009 状态不一致：离线/实时风控标记冲突 | DQ-007 | 有界解释 | quality_warning | quality_warning | ✅ |
| BC-010 数据倾斜：单渠道异常拉高整体指标 | DQ-010 | 告警误报 | quality_warning | quality_warning | ✅ |

**回归汇总：** 10/10 通过

---

## 五、审计字段设计（Day 58 准备）

### Request 字段

| 字段名 | 说明 |
|--------|------|
| `request_id` | str — 请求唯一标识，用于全链路追踪 |
| `trace_id` | str — 分布式追踪 ID，串联 Agent → 工具 → 数据源 |
| `timestamp` | str (ISO 8601) — 请求时间 |
| `user_question` | str — 用户原始问题 |
| `agent_intent` | str — Agent 识别的意图类型 |

### Quality Check 字段

| 字段名 | 说明 |
|--------|------|
| `quality_status` | enum: quality_ok | quality_warning | quality_blocked |
| `triggered_rules` | list[str] — 触发的质量规则 ID 列表 |
| `quality_detail` | dict — 每条触发规则的详细检查结果 |
| `data_freshness` | str — 数据新鲜度描述（如 'dt=2026-06-10, ETL completed'） |
| `completeness_score` | float 0.0-1.0 — 数据完整度评分 |
| `duplication_rate` | float — 重复率（如有） |

### Decision 字段

| 字段名 | 说明 |
|--------|------|
| `action` | enum: normal_answer | degraded_answer | blocked_answer |
| `confidence` | float 0.0-1.0 — Agent 回答可信度 |
| `degradation_reason` | str — 降级原因（quality_warning 时必填） |
| `block_reason` | str — 阻断原因（quality_blocked 时必填） |
| `suggestions` | list[str] — 给用户的排查建议 |

### Regression 字段

| 字段名 | 说明 |
|--------|------|
| `bad_case_id` | str — 关联的 bad case ID |
| `regression_check_passed` | bool — 本次回答是否通过该 bad case 断言 |
| `linked_day56_scenario` | str — 关联的 Day 56 评测场景 |

---

## 六、后续步骤

- **day58**：将 quality_status、triggered_rules、confidence 等字段写入审计存储，支持 request_id + trace_id 回放
- **day59**：在统一仓库 Agent 入口中集成质量检查节点，根据 quality_status 路由到正常/降级/阻断分支
- **day60**：在演示中展示：正常回答 → 降级说明 → 阻断排查 三种质量状态下的 Agent 行为差异
