# LLM API 调用：从 Prompt 到 Function Calling

> 目标：掌握 LLM API 的核心调用模式，能设计 Prompt、处理流式响应、实现 Function Calling。

---

## 一、主流 LLM API 对比（15min）

### 1.1 国内可用的大模型

| 模型 | API 地址 | 价格（百万 token） | 优势 | 场景 |
|------|---------|:---------------:|------|------|
| **DeepSeek V4** | api.deepseek.com | 输入 0.5元 / 输出 2元 | ⭐ 性价比极高，中文强 | 日常开发 |
| **通义千问 Qwen** | dashscope.aliyun.com | 输入 0.8元 / 输出 2元 | 阿里系集成好 | 企业场景 |
| **GLM-4** | open.bigmodel.cn | 输入 0.1元 / 输出 0.1元 | 最便宜，中文好 | 批量任务 |
| **Claude 3.5** | api.anthropic.com | 输入 3元 / 输出 15元 | 推理最强 | 复杂任务 |
| **GPT-4o** | api.openai.com | 输入 5元 / 输出 20元 | 综合最强 | 关键决策 |
| **DeepSeek R1** | api.deepseek.com | 输入 1元 / 输出 4元 | 推理链超强 | 工程分析 |

---

## 二、API 调用的四种模式（1h）

### 模式 1：基础 Prompt 调用

```python
from openai import OpenAI

# DeepSeek 兼容 OpenAI SDK
client = OpenAI(
    api_key="sk-your-key",
    base_url="https://api.deepseek.com"  # 改 base_url 即可切换模型
)

def chat(prompt: str, model: str = "deepseek-chat",
         temperature: float = 0.0) -> str:
    """
    temperature = 0.0 → 确定性输出（适合代码生成、SQL生成）
    temperature = 0.7 → 创意性输出（适合文案、头脑风暴）
    temperature = 1.0 → 高度随机（适合创意写作）
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一位 SQL 专家。"},  # System Prompt
            {"role": "user", "content": prompt},                    # User Message
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content
```

### 模式 2：流式输出（Streaming）

```python
def chat_stream(prompt: str):
    """
    流式输出: 一个字一个字显示，而不是等全部生成完。

    适用于: 需要实时显示回复的场景（对话机器人、代码生成）
    不适用于: 需要完整结果再做后续处理的场景
    """
    stream = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        stream=True,  # ← 流式模式
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
            # 每次 yield 一小段文本，前端可以实时渲染

# 使用
for text in chat_stream("写一段 SQL 查询最近 7 天的通过率"):
    print(text, end="", flush=True)
```

### 模式 3：多轮对话

```python
def multi_turn_chat():
    """
    多轮对话: 保留历史消息，让 LLM 理解上下文。

    关键: messages 列表每次增加一条 user 和 assistant 消息
    注意: 消息数越多 → token 消耗越大 → 注意窗口长度
    """
    messages = [
        {"role": "system",
         "content": "你是风控数据仓库的 AI 助手。"}
    ]

    print("开始对话（输入 'q' 退出）")
    while True:
        user_input = input("\n你: ")
        if user_input.lower() == 'q':
            break

        # 添加用户消息
        messages.append({"role": "user", "content": user_input})

        # 调用 LLM
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.0,
        )

        reply = response.choices[0].message.content
        print(f"AI: {reply}")

        # 添加助手回复（用于下一轮对话的上下文）
        messages.append({"role": "assistant", "content": reply})

        # ★ 重要: 控制消息数量
        if len(messages) > 20:  # 超过 10 轮对话
            # 丢弃最早的消息，但保留 system prompt
            messages = [messages[0]] + messages[-19:]
```

### 模式 4：Function Calling

```python
# ★ Function Calling = 让 LLM 可以调用你的代码函数
# 这是 Agent 架构的基础 — LLM 通过 Function Calling 操作外部系统

# Step 1: 定义工具函数
def query_data_warehouse(sql: str) -> str:
    """执行 SQL 查询，返回结果。这是调用数据仓库的准入门"""
    import sqlite3
    # 这里是演示，实际连接数据仓库
    conn = sqlite3.connect(":memory:")
    try:
        cursor = conn.execute(sql)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        return f"列名: {columns}\n数据: {results[:10]}"
    except Exception as e:
        return f"SQL 错误: {e}"

def get_user_profile(user_id: str) -> str:
    """获取用户基本信息"""
    return f"用户 {user_id}: 30岁, 月收入 8000, 信用评分 672"


# Step 2: 定义函数 Schema（告诉 LLM 有哪些函数可用）
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_data_warehouse",
            "description": "执行 SQL 查询数据仓库",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL 查询语句"
                    }
                },
                "required": ["sql"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": "获取用户基本信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户 ID"
                    }
                },
                "required": ["user_id"]
            }
        }
    }
]

# Step 3: 请求 LLM 决定是否调用函数
def agent(query: str) -> str:
    """
    Function Calling 流程:
    1. 把用户问题 + tools 定义发给 LLM
    2. LLM 判断: 需要调用函数吗？
    3. 如果要 → LLM 返回函数名 + 参数
    4. 执行函数 → 结果返回 LLM → LLM 综合回答
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": query}],
        tools=tools,           # ← 告诉 LLM 有哪些工具
        tool_choice="auto",    # ← 让 LLM 自己决定是否调用
    )

    message = response.choices[0].message

    # LLM 决定调用函数
    if message.tool_calls:
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            # 执行函数
            if func_name == "query_data_warehouse":
                result = query_data_warehouse(**func_args)
            elif func_name == "get_user_profile":
                result = get_user_profile(**func_args)

            # 把函数结果发给 LLM，让它综合回答
            second_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": query},
                    message,
                    {"role": "tool", "content": result,
                     "tool_call_id": tool_call.id}
                ],
                tools=tools,
            )
            return second_response.choices[0].message.content

    # LLM 没有调用函数，直接回答
    return message.content


# 测试
print(agent("查询 2026-07-01 各渠道通过率"))
print(agent("帮我查一下 user_000042 的基本信息"))
```

---

## 三、Prompt 工程设计原则（30min）

### 3.1 好的 Prompt 模板

```python
# 通用 Prompt 结构
SYSTEM_PROMPT_TEMPLATE = """你是一个{角色}。

## 背景
{项目背景}

## 可用信息
{上下文}

## 规则
1. {规则1}
2. {规则2}

## 要求
- {要求1}
- {要求2}

## 输出格式
{格式说明}
"""


# 示例: NL2SQL Prompt
NL2SQL_PROMPT = """你是一个 SQL 专家，专门查询信贷风控数据仓库。

## 可用表
表 ads.ads_model_monitor_daily:
  channel STRING -- 渠道
  approval_rate DOUBLE -- 通过率 0-1
  dt STRING -- 日期 YYYY-MM-DD

## 规则
1. 只生成 SELECT 语句
2. 必须包含 dt 分区过滤
3. 比例值用小数表示（如 65% = 0.65）

## 输出
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

## 四、Token 管理与成本控制

```python
# Token 计数 — 每条消息的 token 数 = 输入 token + 输出 token

def estimate_cost(prompt_tokens: int, response_tokens: int,
                  model: str = "deepseek-chat") -> float:
    """估算单次 API 调用的成本"""
    prices = {
        "deepseek-chat": {"input": 0.5, "output": 2},   # 元/百万 token
        "gpt-4o":        {"input": 5, "output": 20},
        "claude-3":      {"input": 3, "output": 15},
    }

    p = prices[model]
    input_cost = prompt_tokens / 1_000_000 * p["input"]
    output_cost = response_tokens / 1_000_000 * p["output"]
    return input_cost + output_cost

# 典型 token 消耗（中文）:
# 100 字 ≈ 130 token
# 1 轮对话 ≈ 500-1000 input token
# 1 条 SQL 生成 ≈ 50-100 output token
# 1 天 1000 次 NL2SQL 调用 ≈ 1-2 元（DeepSeek）
```

---

## 五、动手练习

```python
"""
练习 1: 实现一个多轮对话的"风控分析师 AI 助手"

要求:
1. 支持连续提问（多轮对话）
2. 当用户问"查数据"时，调用函数生成 SQL 并执行
3. 当用户问"什么是 XXX"时，检索 RAG 知识库
4. 控制上下文长度不超过 10 轮

练习 2: 设计一个 NL2SQL 的 System Prompt

场景: 电商数据仓库
  表: ads.ads_daily_gmv (dt, channel, gmv, order_cnt)
  表: ads.ads_product_rank (dt, product_id, sales, category)

要求: 让用户问"昨天的 GMV""最畅销品类"等，LLM 生成正确的 SQL
"""
```

---

## 六、常见问题

### Q1: temperature 不同值的效果？

```
temperature=0.0 → 每次输出完全一样（确定性的）→ SQL 生成 ✅
temperature=0.3 → 稍有变化 → 客服回复 ✅
temperature=0.7 → 富有创意 → 文案生成 ✅
temperature=1.0 → 高度随机 → 创作 ✅
```

### Q2: System Prompt 和 User Message 有什么区别？

```
System Prompt:  指导 LLM 行为的"指令" — 通常不被用户看到
User Message:  用户的实际问题

相当于: System = "你是一个 SQL 专家"（角色设定）
         User = "上周通过率是多少？"（具体任务）

好的 System Prompt 是 RAG 和 NL2SQL 成功的一半。
```
