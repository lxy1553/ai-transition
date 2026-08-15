"""
Vanna 2.0 阶段1学习（进阶）：触发真实的工具调用循环

这个脚本验证最核心的能力——Agent 的 while 循环：
  1. LLM 返回 ToolCall（说"我要调 run_sql"）
  2. Agent 找到工具、执行 SQL
  3. 把 SQL 结果作为 tool 消息回喂给 LLM
  4. LLM 基于结果生成最终回答

我们用"假 LLM"（ToolCallingLlm）模拟真实 LLM 的行为：第一次返回工具调用，
看到工具结果后再返回最终回答。这让我们不联网也能看到完整循环。

运行：cd github/project/vanna && PYTHONPATH=src python3 ../study/vanna/02_触发工具调用.py
"""

import asyncio
import os
import sys

SRC = os.path.join(os.path.dirname(__file__), "..", "..", "vanna", "src")
sys.path.insert(0, os.path.abspath(SRC))

from vanna import (
    Agent, AgentConfig, User, ToolRegistry, LlmRequest, LlmResponse, ToolCall,
)
from vanna.core.user.request_context import RequestContext
from vanna.core.user.resolver import UserResolver
from vanna.integrations.local.agent_memory.in_memory import DemoAgentMemory
from vanna.integrations.sqlite.sql_runner import SqliteRunner
from vanna.tools.run_sql import RunSqlTool
from vanna.core.llm.base import LlmService


class ToolCallingLlm(LlmService):
    """
    模拟"会调用工具"的 LLM。

    第一次收到请求 → 返回 ToolCall("run_sql", 一条 SQL)
    之后收到（带了工具结果的请求）→ 返回最终自然语言回答

    这就是真实 LLM（DeepSeek/GPT）的简化版——真实 LLM 靠 prompt 和 function calling
    决定何时返回 ToolCall，这里用"第几次请求"来模拟同样的行为。
    """

    def __init__(self):
        self.request_count = 0

    async def send_request(self, request: LlmRequest) -> LlmResponse:
        self.request_count += 1
        await asyncio.sleep(0.1)

        if self.request_count == 1:
            # 第一次：LLM 决定要查数据库 → 返回工具调用
            return LlmResponse(
                content="让我查一下数据库里的客户数量...",
                tool_calls=[
                    ToolCall(
                        id="call_001",
                        name="run_sql",
                        arguments={"sql": "SELECT COUNT(*) AS total FROM Customer"},
                    )
                ],
                finish_reason="tool_calls",
            )
        else:
            # 第二次：LLM 看到了工具结果 → 生成最终回答
            # 从 request 里找到工具结果（最后一条 tool 消息）
            tool_result = ""
            for msg in request.messages:
                if msg.role == "tool":
                    tool_result = msg.content
            return LlmResponse(
                content=f"查到了！数据库里共有 {tool_result.strip()} 个客户。",
                finish_reason="stop",
            )

    async def stream_request(self, request: LlmRequest):
        yield LlmResponse(content="（流式）", finish_reason="stop")

    async def validate_tools(self, tools):
        return []


class StaticUserResolver(UserResolver):
    def __init__(self, user: User):
        self._user = user

    async def resolve_user(self, request_context: RequestContext) -> User:
        return self._user


async def main() -> None:
    test_user = User(id="user123", username="testuser", group_memberships=["admin"])

    # 组装：工具注册表 + 模拟LLM + 用户解析 + 记忆
    database_path = os.path.join(os.path.dirname(__file__), "..", "..", "vanna", "src", "Chinook.sqlite")
    tool_registry = ToolRegistry()
    tool_registry.register_local_tool(
        RunSqlTool(sql_runner=SqliteRunner(database_path=database_path)),
        access_groups=[],
    )

    agent = Agent(
        llm_service=ToolCallingLlm(),
        tool_registry=tool_registry,
        user_resolver=StaticUserResolver(test_user),
        agent_memory=DemoAgentMemory(),
        config=AgentConfig(stream_responses=False),
    )

    request_ctx = RequestContext(metadata={"user_id": test_user.id})

    print("👤 用户：数据库里有多少客户？")
    print("=" * 50)

    async for component in agent.send_message(
        request_context=request_ctx,
        message="数据库里有多少客户？",
        conversation_id="conv-002",
    ):
        text = None
        if component.rich_component and hasattr(component.rich_component, "content"):
            text = component.rich_component.content
        elif component.simple_component and hasattr(component.simple_component, "text"):
            text = component.simple_component.text
        if text:
            print(f"🤖 {text}")

    print("=" * 50)
    print("✅ 工具调用循环跑通：LLM返回ToolCall → Agent执行SQL → 结果回喂 → 最终回答")


if __name__ == "__main__":
    asyncio.run(main())
