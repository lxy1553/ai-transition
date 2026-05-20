"""Day 9 - Prompt 模板练习。

这个脚本把常见任务写成可复用 PromptTemplate，而不是临时拼一段 prompt。
用途是练习把 prompt 当成可维护资产：有角色、任务、约束和输出格式，后续才能版本化和回归测试。
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class PromptTemplate:
    """一个可复用的 prompt 模板。

    模板把角色、任务、约束和输出格式拆开，避免每次写 prompt 都从零开始。
    真实项目里也会用类似结构管理 RAG、NL2SQL、SQL 解释等不同任务。
    """

    name: str
    role: str
    task: str
    constraints: list[str]
    output_format: list[str]

    def render(self, context: str) -> str:
        """把模板和上下文合成最终 prompt。

        context 是每次调用时变化的业务资料，比如表结构、指标口径、用户问题。
        模板保持稳定，上下文动态注入，这样更容易维护和测试。
        """
        constraints = "\n".join(f"- {item}" for item in self.constraints)
        output_format = "\n".join(f"{index}. {item}" for index, item in enumerate(self.output_format, start=1))
        return f"""[{self.name}]
角色：
{self.role}

任务：
{self.task}

上下文：
{context}

约束：
{constraints}

输出格式：
{output_format}
"""


TEMPLATES = [
    PromptTemplate(
        name="SQL 解释模板",
        role="你是一个数据仓库 SQL 解释助手。",
        task="解释 SQL 的业务含义、关键字段和潜在风险。",
        constraints=["不编造表结构", "信息不足时说明缺少什么", "优先使用面试可复述的表达"],
        output_format=["业务含义", "字段解释", "风险提示", "需要补充的上下文"],
    ),
    PromptTemplate(
        name="数据问答模板",
        role="你是一个数据分析助手。",
        task="根据表结构说明回答业务问题，并指出口径风险。",
        constraints=["只基于已给上下文回答", "先说明时间范围和统计口径", "无法判断时不要猜测"],
        output_format=["结论", "推理依据", "口径风险", "建议 SQL 思路"],
    ),
    PromptTemplate(
        name="简历项目包装模板",
        role="你是一个 AI 应用工程师简历优化助手。",
        task="把学习项目改写成简历项目描述。",
        constraints=["不夸大真实经历", "突出数据背景迁移", "每条 bullet 包含动作、技术和价值"],
        output_format=["项目名称", "技术栈", "项目描述", "面试讲解亮点"],
    ),
]


def main() -> None:
    """渲染所有 prompt 模板，并保存成 Markdown 产物。

    保存到文件是为了后续复盘和比较不同模板效果。
    prompt 不能只散落在代码里，否则很难审查、回滚和复用。
    """
    context = "当前用户有数据仓库背景，正在转向 RAG / NL2SQL / 数据问答方向。"
    rendered_templates = []
    for template in TEMPLATES:
        rendered = template.render(context)
        rendered_templates.append(rendered)
        print(rendered)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "prompt_templates.md"
    output_file.write_text("\n---\n\n".join(rendered_templates), encoding="utf-8")
    print(f"Saved templates to: {output_file}")


if __name__ == "__main__":
    main()
