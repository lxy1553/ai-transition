---
id: L110
source: learning
category: LLM与AI工程
title: 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的API 调用的四种模式（1h）
generated: 2026-07-23T15:41:19.873912
---

# 请讲讲LLM API 调用：从 Prompt 到 Function Calling中的API 调用的四种模式（1h）

> 来源: 学习复习计划 | 分类: LLM与AI工程

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