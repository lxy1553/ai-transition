# 主干 ③：Registry 分派

> **状态**：✅ 已学完
> **代码位置**：`src/vanna/core/registry.py`（278 行，完整读过）
> **这是 Agent 循环里"执行工具"的中枢**——所有工具调用都经过它。

---

## 三问

- **Q1 解决什么问题**：管理所有工具——注册、按名字查找、统一执行（带权限/校验/审计）
- **Q2 数据流哪一环**：Agent 循环里"执行工具"那一步：`get_tool(name)` → `execute(tool_call)`
- **Q3 删掉会怎样**：工具散落各处，LLM 的 tool_call.name 找不到执行者 → 循环断裂

---

## 一、Registry 的全貌（它管理什么）

```python
class ToolRegistry:
    # ── 存储 ──
    _tools: Dict[str, Tool]    # 工具名 → 工具对象

    # ── 管理方法 ──
    register_local_tool(tool, access_groups)   # 注册工具（可带权限）
    get_tool(name)                              # 按名字找工具
    list_tools()                                # 列出所有工具名

    # ── 权限/转换 ──
    get_schemas(user)              # 返回用户有权用的工具 schema（供 system_prompt）
    _validate_tool_permissions(tool, user)   # 用户能否用这个工具
    transform_args(tool, args, user, context) # 改写参数（行级安全/脱敏）★

    # ── 核心：执行 ──
    async execute(tool_call, context)   # 执行工具调用（完整安全关卡）
```

**核心认知**：Registry 是"工具的中枢"——注册、查找、执行都在这里，且执行时带完整的安全关卡（权限→校验→转换→执行→审计）。

---

## 二、注册：register_local_tool（registry.py:63）

```python
def register_local_tool(self, tool, access_groups):
    """注册工具（可带权限组）"""
    # ① 防重复注册
    if tool.name in self._tools:
        raise ValueError(f"Tool '{tool.name}' already registered")

    # ② 有权限组 → 用 _LocalToolWrapper 包一层（加权限）
    if access_groups:
        wrapped_tool = _LocalToolWrapper(tool, access_groups)
        self._tools[tool.name] = wrapped_tool
    else:
        # 无权限组 → 直接存原工具（所有人可用）
        self._tools[tool.name] = tool
```

### _LocalToolWrapper（权限包装器，registry.py:20）

```python
class _LocalToolWrapper(Tool[T]):
    """给工具包一层权限——不改变工具本身，只加 access_groups"""
    def __init__(self, wrapped_tool, access_groups):
        self._wrapped_tool = wrapped_tool     # 原始工具
        self._access_groups = access_groups   # 新权限组

    # 所有属性转发给原始工具，只有 access_groups 被覆盖
    @property
    def name(self): return self._wrapped_tool.name
    @property
    def description(self): return self._wrapped_tool.description
    @property
    def access_groups(self): return self._access_groups   # ★ 覆盖权限
    def get_args_schema(self): return self._wrapped_tool.get_args_schema()
    async def execute(self, context, args): return await self._wrapped_tool.execute(context, args)
```

**关键洞察**：这是**装饰器模式**——不改原工具，只给它"套一层权限"。注册时传 `access_groups=["risk"]`，工具就能被权限控制。

**用法**：
```python
registry = ToolRegistry()
registry.register_local_tool(
    RunSqlTool(sql_runner=sqlite_runner),
    access_groups=["risk"],     # ★ 只有 risk 组能用
)
```

---

## 三、权限校验：_validate_tool_permissions（registry.py:98）

```python
async def _validate_tool_permissions(self, tool, user) -> bool:
    """用户能否用这个工具（工具级权限）"""
    tool_access_groups = tool.access_groups
    if not tool_access_groups:
        return True   # 工具没声明组 = 所有人可用

    user_groups = set(user.group_memberships)   # 用户的组集合
    tool_groups = set(tool_access_groups)       # 工具需要的组集合
    return bool(user_groups & tool_groups)      # ★ 交集非空 = 有权限
```

**这就是"用户组 ∩ 工具组"的实现**——你在权限专题学过。

---

## 四、get_schemas：决定"LLM 能看到什么工具"（registry.py:90）

### 它在哪被调用（agent.py:571）

```python
# agent.py:571 —— 构建 system_prompt 前，先拿用户有权用的工具
tool_schemas = await self.tool_registry.get_schemas(user)
#   ↓
system_prompt = await self.system_prompt_builder.build_system_prompt(user, tool_schemas)
#   ↓
# system_prompt 里包含"你能用这些工具：run_sql, explain_definition..."
# LLM 看到这个，才知道自己能调什么
```

**一句话**：get_schemas 决定"LLM 被告知能做什么"，它决定了 Agent 的能力边界。

### 逐行拆解

```python
async def get_schemas(self, user=None) -> List[ToolSchema]:
    """返回用户有权用的工具 schema（供 system_prompt 构建）"""
    schemas = []                                    # ① 结果列表
    for tool in self._tools.values():               # ② 遍历所有已注册工具
        if user is None or await self._validate_tool_permissions(tool, user):
            schemas.append(tool.get_schema())       # ③ 有权限 → 加进结果
    return schemas                                  # ④ 返回过滤后的 schema 列表
```

- **① `schemas = []`**：空列表，收集"用户有权用的工具 schema"
- **② 遍历所有工具**：不管用户是谁，先看全部
- **③ 条件判断**：`user is None`（无用户=全放行）**或** `_validate_tool_permissions`（用户组∩工具组非空）→ 放行
- **④ 返回**：只返回有权用的工具 schema

### 跟着数据走一遍（权限如何过滤）

假设注册 3 个工具：
```python
registry.register_local_tool(RunSqlTool, access_groups=["analyst"])
registry.register_local_tool(QueryPiiTool, access_groups=["risk"])    # 敏感
registry.register_local_tool(VisualizeTool, access_groups=[])         # 所有人
```

**用户 A（analyst 组）**：
```
RunSqlTool:  analyst ∩ [analyst] = 有 → 加入 ✅
QueryPiiTool: analyst ∩ [risk] = 无 → 跳过 ❌
VisualizeTool: 没声明组 = 所有人 → 加入 ✅
返回: [RunSqlTool, VisualizeTool]
```

**用户 B（risk 组）**：
```
RunSqlTool:  risk ∩ [analyst] = 无 → 跳过 ❌
QueryPiiTool: risk ∩ [risk] = 有 → 加入 ✅
VisualizeTool: 所有人 → 加入 ✅
返回: [QueryPiiTool, VisualizeTool]
```

**关键效果**：用户 A 的 system_prompt 没有 QueryPiiTool → LLM **不知道有敏感工具**，自然不会调。这就是"指标权限"的实现——没权限的工具，LLM 连"存在"都不知道。

### 为什么这样设计（vs 让 LLM 自觉判断）

| | get_schemas 过滤（Vanna）| 让 LLM 自己判断 |
|---|---|---|
| 时机 | 构建 prompt 前（静态）| LLM 运行时（动态）|
| 原理 | 没权限 → 工具不进 prompt | LLM 看到但"自觉"不用 |
| 可靠性 | 100%（物理隔离）| 不可靠（可能越权）|
| 成本 | 无 | LLM 每次判断 |

**核心**：在 prompt 层过滤，比"让 LLM 自觉不用"可靠得多——和 transform_args（数据层兜底）一样，是"分层防御"思想。

---

## 五、transform_args：改写参数（registry.py:113）★ 行级安全

```python
async def transform_args(self, tool, args, user, context):
    """根据用户上下文改写/校验参数"""
    # 官方注释：三个用途
    # - 行级安全（RLS）到 SQL 查询
    # - 按权限过滤可用选项
    # - 脱敏敏感字段
    return args   # 默认不改（NoOp）——子类覆盖实现
```

**这是表级/行级权限的钩子**（你学过）：子类覆盖它，检查 SQL 引用的表、注入 WHERE。

---

## 六、核心：execute 完整流水线（registry.py:144）★ 最重要的方法

```python
async def execute(self, tool_call, context) -> ToolResult:
    """执行工具调用，带完整安全关卡"""

    # ── 步骤 1：找工具 ──
    tool = await self.get_tool(tool_call.name)
    if not tool:
        msg = f"Tool '{tool_call.name}' not found"
        return ToolResult(success=False, result_for_llm=msg, error=msg)
        # ★ 工具不存在 → 返回错误（让 LLM 知道换个工具）

    # ── 步骤 2：工具级权限校验 ──
    if not await self._validate_tool_permissions(tool, context.user):
        msg = f"Insufficient group access for tool '{tool_call.name}'"
        # 审计：记录权限拒绝
        if self.audit_logger and self.audit_config.log_tool_access_checks:
            await self.audit_logger.log_tool_access_check(
                user=context.user, tool_name=tool_call.name,
                access_granted=False, required_groups=tool.access_groups, reason=msg)
        return ToolResult(success=False, result_for_llm=msg, error=msg)
        # ★ 无权限 → 拒绝 + 审计

    # ── 步骤 3：参数校验（Pydantic）──
    try:
        args_model = tool.get_args_schema()
        validated_args = args_model.model_validate(tool_call.arguments)
        # ★ LLM 填的原始 dict → 按 schema 校验成 Pydantic 对象
    except Exception as e:
        msg = f"Invalid arguments: {str(e)}"
        return ToolResult(success=False, result_for_llm=msg, error=msg)
        # ★ 参数格式错 → 返回错误（让 LLM 重新填）

    # ── 步骤 4：transform_args（行级安全/脱敏）──
    transform_result = await self.transform_args(
        tool=tool, args=validated_args, user=context.user, context=context)
    if isinstance(transform_result, ToolRejection):
        return ToolResult(success=False, result_for_llm=transform_result.reason, error=transform_result.reason)
        # ★ 行级安全拒绝（如无表权限）

    final_args = transform_result   # 可能是被改写过的参数

    # ── 步骤 5：审计（放行记录）──
    if self.audit_logger and self.audit_config.log_tool_access_checks:
        await self.audit_logger.log_tool_access_check(
            user=context.user, tool_name=tool_call.name, access_granted=True, ...)
    if self.audit_logger and self.audit_config.log_tool_invocations:
        await self.audit_logger.log_tool_invocation(
            user=context.user, tool_call=tool_call, ...)

    # ── 步骤 6：真正执行（带超时统计）──
    try:
        start_time = time.perf_counter()
        result = await tool.execute(context, final_args)   # ★ 真正调工具
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        result.metadata["execution_time_ms"] = execution_time_ms   # 记录耗时

        # 审计：工具结果
        if self.audit_logger and self.audit_config.log_tool_results:
            await self.audit_logger.log_tool_result(user=..., tool_call=..., result=result, ...)

        return result
    except Exception as e:
        msg = f"Execution failed: {str(e)}"
        return ToolResult(success=False, result_for_llm=msg, error=msg)
        # ★ 执行异常 → 返回错误（让 LLM 知道）
```

### execute 六步流水线（一图）

```
execute(tool_call, context)
  │
  ├─ ① 找工具 get_tool(name)         → 不存在？返回错误
  ├─ ② 工具级权限 _validate_tool_permissions → 无权限？拒绝+审计
  ├─ ③ 参数校验 model_validate         → 格式错？返回错误
  ├─ ④ transform_args（行级/脱敏）     → 拒绝？返回错误
  ├─ ⑤ 审计（放行记录）
  └─ ⑥ 真正执行 tool.execute()        → 异常？返回错误
       └─ 记录耗时 + 审计结果
```

**核心设计**：
1. **任何一步失败都返回 ToolResult(success=False)**——不抛异常，错误回喂给 LLM 让它修正
2. **安全关卡前置**——权限/校验在真正执行之前
3. **审计贯穿**——拒绝和放行都记录

---

## 七、对照 ai_assistant 的改造动作

你的 `pipeline.py` 现在权限检查硬编码。Registry 式改造：

```python
# 现在（pipeline 里硬编码）
def _handle_indicator_query(self, query, user_role, trace_id):
    ...
    if not self.permission.check(indicator_name, user_role):
        return "无权限"          # ★ 权限判断硬编码在 pipeline

# 改造：引入 ToolRegistry，权限下沉到工具粒度
class CreditToolRegistry(ToolRegistry):
    """信贷工具注册表"""

    async def transform_args(self, tool, args, user, context):
        # 表级权限：校验 SQL 引用的表
        if tool.name == "run_sql":
            allowed = get_user_tables(user.id)
            for t in extract_tables(args.sql):
                if t not in allowed:
                    return ToolRejection(reason=f"无权限访问表 {t}")
        return args

# 注册带权限的工具
registry = CreditToolRegistry()
registry.register_local_tool(
    QueryIndicatorTool(...),
    access_groups=["analyst"],   # ★ 权限在注册时声明
)

# pipeline 不再写权限判断，只调 registry.execute
result = await registry.execute(tool_call, context)
# → execute 内部自动做：权限/校验/transform/执行/审计
```

**改造要点**：
1. 权限判断从 pipeline → Registry（`register_local_tool` 的 access_groups + `transform_args`）
2. 你的 `_handle_indicator_query` 里权限检查删掉 → 交给 registry
3. 审计也交给 registry（放行/拒绝都记录）

---

## 八、小结

| 学到 | 一句话 |
|------|--------|
| register_local_tool | 注册工具（可带权限），装饰器包装 |
| _LocalToolWrapper | 不改工具，只套权限层 |
| get_schemas | 按用户过滤工具 → 控制 LLM 能看到什么 |
| transform_args | 行级安全/脱敏的钩子 |
| **execute 六步** | 找→权限→校验→transform→审计→执行 |
| 错误处理 | 任何失败返回 ToolResult(success=False)，回喂 LLM |

> **核心心法**：Registry 是工具中枢，execute = 权限 + 校验 + 转换 + 执行 + 审计。你的 ai_assistant 权限判断应从 pipeline 移到 Registry 的工具粒度。
