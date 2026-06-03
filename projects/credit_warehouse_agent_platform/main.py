"""准生产金融信贷离线/实时仓库 + Agent 项目入口。

这个入口负责把数据接入、数仓治理、指标加工、实时事件聚合、Agent 问答、
审计日志和评测报告串起来。项目不依赖外部数据库和真实模型，便于本地演示；
生产落地时可以把 SQLite、规则 Agent 和样例数据替换成真实数仓、流处理和 LLM 服务。
"""

from __future__ import annotations

import argparse
import json

from app.platform import CreditWarehouseAgentPlatform


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数。

    用 CLI 是为了让项目先具备稳定交付入口，后续接 FastAPI 或调度系统时，
    可以复用同一套平台能力，而不是把逻辑散落在不同脚本里。
    """

    parser = argparse.ArgumentParser(description="金融信贷离线/实时仓库 + Agent 平台")
    parser.add_argument("--run-all", action="store_true", help="执行全链路并生成全部交付产物")
    parser.add_argument("--ingest", action="store_true", help="执行离线与实时数据接入")
    parser.add_argument("--serve-demo", action="store_true", help="运行内置 Agent 问答示例")
    parser.add_argument("--eval", action="store_true", help="运行固定评测集")
    parser.add_argument("--question", help="单独向 Agent 提问")
    parser.add_argument("--role", default="risk_analyst", help="用户角色")
    return parser


def main() -> None:
    """执行命令行任务。"""

    parser = build_parser()
    args = parser.parse_args()
    platform = CreditWarehouseAgentPlatform()

    if args.run_all:
        result = platform.run_all()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.ingest:
        result = platform.build_warehouse()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.serve_demo:
        result = platform.run_demo_questions()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.eval:
        result = platform.run_evaluation()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.question:
        answer = platform.answer_question(question=args.question, role=args.role)
        print(json.dumps(answer, ensure_ascii=False, indent=2))

    if not any([args.run_all, args.ingest, args.serve_demo, args.eval, args.question]):
        parser.print_help()


if __name__ == "__main__":
    main()
