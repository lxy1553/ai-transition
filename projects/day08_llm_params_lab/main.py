"""Day 8 - LLM 参数实验。

这个脚本不调用真实模型，而是在本地整理 prompt 结构、参数含义和成本估算。
用途是先理解一次 LLM 调用需要关注哪些工程要素：system/user prompt、temperature、max_tokens 和成本。
"""

from dataclasses import dataclass


@dataclass
class LLMExperiment:
    """记录一组 LLM 参数实验。

    每组实验说明参数适合什么场景，避免以后只知道参数名字，却不知道为什么要这样设置。
    """

    name: str
    temperature: float
    top_p: float
    max_tokens: int
    scenario: str
    expected_behavior: str


SYSTEM_PROMPT = """你是一个面向数据仓库工程师的 SQL 解释助手。
请准确解释 SQL 的业务含义、关键字段和潜在风险。
如果缺少表结构，请明确说明缺少哪些上下文。"""

USER_PROMPT = """请解释下面 SQL 的含义，并指出可能的性能风险：

select user_id, count(*) as order_cnt
from orders
where dt = '2026-05-08'
group by user_id;"""


EXPERIMENTS = [
    LLMExperiment(
        name="stable_sql_explanation",
        temperature=0.1,
        top_p=1.0,
        max_tokens=300,
        scenario="SQL 解释、RAG 问答、结构化输出",
        expected_behavior="回答更稳定，适合需要准确性的场景。",
    ),
    LLMExperiment(
        name="balanced_summary",
        temperature=0.5,
        top_p=1.0,
        max_tokens=500,
        scenario="总结、改写、普通问答",
        expected_behavior="表达有一定变化，但仍然比较可控。",
    ),
    LLMExperiment(
        name="creative_brainstorming",
        temperature=0.9,
        top_p=1.0,
        max_tokens=800,
        scenario="创意发散、文案草稿",
        expected_behavior="回答更发散，不适合严肃数据解释和事实问答。",
    ),
]


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数，让实验不依赖真实模型服务。

    真实 token 计算会由具体模型 tokenizer 决定。
    这里用近似算法，是为了先建立“输入越长、成本越高”的工程意识。
    """
    chinese_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    other_chars = len(text) - chinese_chars
    return round(chinese_chars * 0.75 + other_chars / 4)


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """按假设价格估算一次调用成本。

    这不是某个真实厂商的价格表，而是帮助理解成本结构：
    输入 token 和输出 token 都会计费，输出通常更贵。
    """
    input_price_per_1k = 0.001
    output_price_per_1k = 0.003
    return input_tokens / 1000 * input_price_per_1k + output_tokens / 1000 * output_price_per_1k


def print_prompt_structure() -> None:
    """打印 system prompt 和 user prompt。

    system prompt 放长期规则，user prompt 放本次具体任务。
    生产项目里把两者分清楚，才能稳定控制模型角色和任务边界。
    """
    print("=== Prompt Structure ===")
    print("[System Prompt]")
    print(SYSTEM_PROMPT)
    print()
    print("[User Prompt]")
    print(USER_PROMPT)
    print()


def print_experiments() -> None:
    """打印不同参数组合适合的场景。

    SQL 解释、RAG、结构化输出这类任务更重视稳定性，通常用低 temperature。
    创意类任务可以更发散，但不适合严肃数据解释。
    """
    print("=== Parameter Experiments ===")
    for index, experiment in enumerate(EXPERIMENTS, start=1):
        print(f"{index}. {experiment.name}")
        print(f"   temperature: {experiment.temperature}")
        print(f"   top_p: {experiment.top_p}")
        print(f"   max_tokens: {experiment.max_tokens}")
        print(f"   scenario: {experiment.scenario}")
        print(f"   expected: {experiment.expected_behavior}")
        print()


def print_cost_example() -> None:
    """展示一次调用的大致 token 和成本。

    这个例子提醒后续做 RAG 时不要无限塞上下文，
    因为上下文越长，延迟和成本都会上升。
    """
    input_tokens = estimate_tokens(SYSTEM_PROMPT + "\n" + USER_PROMPT)
    output_tokens = 300
    cost = estimate_cost(input_tokens=input_tokens, output_tokens=output_tokens)

    print("=== Rough Cost Example ===")
    print(f"estimated input tokens: {input_tokens}")
    print(f"assumed output tokens: {output_tokens}")
    print(f"estimated cost: ${cost:.6f}")
    print()
    print("Note: this is only a local estimate for learning. Real cost depends on the model provider and pricing.")


def main() -> None:
    """运行 Day 8 参数实验的三个部分：prompt、参数和成本。"""
    print_prompt_structure()
    print_experiments()
    print_cost_example()


if __name__ == "__main__":
    main()
