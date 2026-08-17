# Vanna 学习 14：信贷业务 Hook 示例代码

> 基于你的信贷风控背景，给出 4 个钩子点的真实业务 hook 例子。
> 这些是"照 LifecycleHook 接口自己写"的正确示范——Vanna 不内置，要你实现。
> 每个 hook 对应：信贷场景 + 代码 + 为什么。

---

## Hook 总览（信贷场景）

| 钩子点 | 信贷业务规则 | 拦截/改写 |
|--------|-------------|----------|
| before_message | 敏感信息过滤 + 配额 | 拦截 |
| before_tool | 动态权限 + 大额审批 | 拦截 |
| after_tool | 手机号/身份证脱敏 | 改写 |
| after_message | 审计留痕 | 记录 |

---

## ① before_message：敏感信息过滤 + 用户配额

### 信贷场景
- 用户不能问"别人的征信"（隐私）
- 免费用户每天限 5 次查询

```python
class CreditPrivacyFilterHook(LifecycleHook):
    """业务规则：不能查询他人征信/隐私信息"""

    # 敏感主体（防用户问别人的数据）
    SENSITIVE_TERMS = ["征信报告", "身份证", "手机号", "住址"]

    async def before_message(self, user, message):
        # 检查是否涉他人隐私（"张三的征信"）
        for term in self.SENSITIVE_TERMS:
            if term in message:
                raise AgentError(f"无权查询涉及 {term} 的信息，仅限本人数据")
        # 不涉及敏感词 → 放行
        return None


class CreditQuotaHook(LifecycleHook):
    """业务规则：免费用户每天 5 次，VIP 不限"""

    def __init__(self):
        self._usage = {}          # {user_id: 今日次数}
        self._vip_users = set()   # VIP 用户免配额

    async def before_message(self, user, message):
        if user.id in self._vip_users:
            return None   # VIP 放行

        count = self._usage.get(user.id, 0)
        if count >= 5:
            raise AgentError("免费用户今日配额已用完，请升级 VIP 或明天再试")
        self._usage[user.id] = count + 1
        return None
```

**为什么**：隐私过滤是金融合规底线；配额是成本控制（免费用户不烧 token）。

---

## ② before_tool：动态权限 + 大额审批

### 信贷场景
- 超 100 万授信的查询要人工审批
- 某些敏感工具只有 risk 组能用（动态判断，不只静态 group）

```python
class LargeLoanApprovalHook(LifecycleHook):
    """业务规则：大额授信查询需人工审批"""

    async def before_tool(self, tool, context):
        # 只检查 run_sql 工具
        if tool.name != "run_sql":
            return

        # 从工具参数里提取 SQL（context.metadata 由上层传入）
        sql = context.metadata.get("sql", "")
        if "credit_limit > 1000000" in sql or "amount > 1000000" in sql:
            raise AgentError("大额授信查询需人工审批，请提交审批单")
        # 未超限额 → 放行


class RiskOnlyToolHook(LifecycleHook):
    """业务规则：设备指纹工具只有 risk 组能用（动态判断）"""

    async def before_tool(self, tool, context):
        if tool.name == "query_device_fingerprint":
            if "risk" not in context.user.group_memberships:
                raise AgentError("设备指纹查询仅限风控组使用")
        # 其他工具放行
```

**为什么**：大额审批防风险敞口；动态权限比静态 group 更细（结合业务上下文）。

---

## ③ after_tool：手机号/身份证脱敏

### 信贷场景
- 查询结果里的手机号、身份证必须打码后才能展示给用户

```python
class MaskPiiHook(LifecycleHook):
    """业务规则：返回结果中的 PII 必须脱敏"""

    async def after_tool(self, result):
        if not result.success:
            return result   # 失败不改

        text = str(result.result_for_llm)

        # 手机号：13812345678 → 138****5678
        text = re.sub(r'\b1[3-9]\d{9}\b', lambda m: m.group(0)[:3] + "****" + m.group(0)[-4:], text)

        # 身份证：110101199003071234 → 110101********1234
        text = re.sub(r'\b\d{6}(19|20)\d{2}(0[1-9]|1[0-2])\d{6}\b',
                      lambda m: m.group(0)[:6] + "********" + m.group(0)[-4:], text)

        # 返回改写后的结果（回喂 LLM 的就是脱敏版）
        result.result_for_llm = text
        return result   # ★ 关键：返回改写后的 result
```

**为什么**：列级脱敏——工具查出了完整 PII，这里打码后才回喂给 LLM / 展示给用户。这是"权限五层 ② 列级脱敏"的实现点。

---

## ④ after_message：审计留痕

### 信贷场景
- 每次查询必须留痕：谁、何时、查了什么、结果

```python
class CreditAuditHook(LifecycleHook):
    """业务规则：每次查询写审计日志（合规要求）"""

    async def after_message(self, result):
        audit_record = {
            "user_id": result.user_id,
            "username": result.username,
            "query": result.query,              # 用户问什么
            "sql": result.sql,                   # 生成了什么 SQL
            "result_summary": result.summary,    # 结果摘要（脱敏后）
            "timestamp": datetime.now().isoformat(),
            "latency_ms": result.latency_ms,
        }
        # 写入审计表（合规：所有查询可追溯）
        await audit_db.insert(audit_record)
        # 只记录，不干预
```

**为什么**：金融合规要求"每次数据访问可追溯"——对应权限五层 ⑤ 审计。

---

## 完整装配（怎么挂到 Agent）

```python
agent = Agent(
    llm_service=llm,
    tool_registry=tool_registry,
    lifecycle_hooks=[
        CreditQuotaHook(),          # 配额（先查配额）
        CreditPrivacyFilterHook(),  # 隐私过滤（再过滤）
        LargeLoanApprovalHook(),    # 大额审批（工具前）
        RiskOnlyToolHook(),         # 敏感工具权限
        MaskPiiHook(),              # 结果脱敏（工具后）
        CreditAuditHook(),          # 审计（最后）
    ],
)
```

**执行顺序**（按列表顺序）：
```
用户消息 → [配额 → 隐私过滤] → LLM → [大额审批 → 敏感工具] → 工具执行 → [脱敏] → 回答 → [审计]
```

---

## 信贷场景完整流程（一个例子）

用户"张三"（免费用户）问："查一下李四的征信"

```
① before_message 配额：张三今天第 3 次，通过
② before_message 隐私：含"征信"→ ❌ raise AgentError("无权查询涉及 征信 的信息")
→ 整条消息中断，不进 LLM，不烧 token
```

用户"张三"问："查我自己的授信额度，credit_limit > 1000000 的"

```
① 配额 ✅ ② 隐私 ✅
③ before_tool 大额审批：SQL 含 "credit_limit > 1000000" → ❌ raise AgentError("需人工审批")
→ 工具不执行
```

用户"风控组李四"问："查设备指纹 device_001"

```
① 配额 ✅ ② 隐私 ✅
③ before_tool 敏感工具：李四在 risk 组 → ✅ 放行
④ 工具执行 → 查出指纹
⑤ after_tool 脱敏：无 PII → 不改
⑥ LLM 回答 → ⑦ after_message 审计记录
```

---

## 对照 ai_assistant（怎么落地）

你的 ai_assistant 现在：
- 权限 `permission.check` 硬编码在 pipeline → 移到 before_tool hook
- 审计 `audit.log` 硬编码 → 移到 after_message hook
- 无脱敏 → 加 MaskPiiHook
- 无配额 → 加 CreditQuotaHook

**改造顺序**：
1. 先加 after_message（审计）——最小改动，直接可用
2. 加 before_tool（权限）——把 permission.check 移进去
3. 加 after_tool（脱敏）——复用你的脱敏逻辑
4. 加 before_message（配额/过滤）——最后加，需要配额表

---

## 一句话总结

> 信贷业务 hook = 用 4 个钩子点，把金融规则（隐私/配额/审批/脱敏/审计）插进 Agent。Vanna 不内置，但接口支持——这些例子是"照接口的正确写法"，直接可落地到你的项目。
