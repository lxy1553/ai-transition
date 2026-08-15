"""
Vanna 2.0 阶段1学习：基于"当前真实 API"的最小可运行 Agent

背景：仓库的 examples/ 目录全部基于过时的旧 API（send_message(user=...)），
但当前 Agent.__init__ 要求 user_resolver + agent_memory，send_message 要 RequestContext。
本脚本不抄示例，而是直接基于源码里确认的真实 API 组装一个能跑的 Agent。

运行：cd github/project/vanna && PYTHONPATH=src python3 ../study/vanna/01_最小可运行Agent.py
"""

import asyncio
import os
import sys

# 让 python 能 import vanna（vanna 在 src/ 下）
SRC = os.path.join(os.path.dirname(__file__), "..", "..", "vanna", "src")
sys.path.insert(0, os.path.abspath(SRC))

# ── 从当前真实 API 导入 ──
from vanna import (
    Agent, AgentConfig, User, ToolCall, ToolContext,
    ToolRegistry, UiComponent,
)
# RequestContext 在 vanna.core.user，不在顶层导出
from vanna.core.user.request_context import RequestContext
from vanna.core.user.resolver import UserResolver
from vanna.integrations.local.agent_memory.in_memory import DemoAgentMemory
from vanna.integrations.mock.llm import MockLlmService
from vanna.integrations.sqlite.sql_runner import SqliteRunner
from vanna.tools.run_sql import RunSqlTool


class StaticUserResolver(UserResolver):
    """
    最简单的 UserResolver：不管 RequestContext 里是什么，都返回同一个测试用户。
    生产环境会从 Cookie/Header/JWT 里解析真实用户（见 vanna/core/user/resolver.py 的 docstring 示例）。
    """

    def __init__(self, user: User):
        self._user = user

    async def resolve_user(self, request_context: RequestContext) -> User:
        return self._user


async def main() -> None:
    # ── 1. 组装依赖 ──
    test_user = User(id="user123", username="testuser", group_memberships=["admin"])

    # 1.1 LLM 服务（用 Mock，不花钱不联网）
    llm_service = MockLlmService(
        response_content="你好！我是用 Vanna 2.0 组装的最小 Agent。"
    )

    # 1.2 工具注册表 + 注册 SQL 工具（连 Chinook 数据库）
    database_path = os.path.join(os.path.dirname(__file__), "..", "..", "vanna", "src", "Chinook.sqlite")
    tool_registry = ToolRegistry()
    tool_registry.register_local_tool(
        RunSqlTool(sql_runner=SqliteRunner(database_path=database_path)),
        access_groups=[],   # 空 = 所有人可用
    )

    # 1.3 用户解析器 + 记忆（Agent 必填的两个参数）
    user_resolver = StaticUserResolver(test_user)
    agent_memory = DemoAgentMemory()

    # ── 2. 组装 Agent（用当前真实签名）──
    agent = Agent(
        llm_service=llm_service,
        tool_registry=tool_registry,
        user_resolver=user_resolver,
        agent_memory=agent_memory,
        config=AgentConfig(stream_responses=False),
    )

    # ── 3. 发送消息（用 RequestContext，不是 user=）──
    request_ctx = RequestContext(
        headers={"Authorization": "Bearer test-token"},
        metadata={"user_id": test_user.id},
    )

    print("👤 用户：你好")
    print("🤖 Agent：", end="", flush=True)

    async for component in agent.send_message(
        request_context=request_ctx,
        message="你好",
        conversation_id="conv-001",
    ):
        # 从组件里取文本内容
        text = None
        if component.rich_component and hasattr(component.rich_component, "content"):
            text = component.rich_component.content
        elif component.simple_component and hasattr(component.simple_component, "text"):
            text = component.simple_component.text
        if text:
            print(text, end="", flush=True)

    print("\n\n✅ 阶段1 最小 Agent 跑通！")


if __name__ == "__main__":
    asyncio.run(main())
