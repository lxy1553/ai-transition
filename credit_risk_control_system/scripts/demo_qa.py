"""
AI 数据问答层 —— 演示脚本

小白理解：这个脚本就是"打开水龙头"，让你实际跑一遍，看数据是怎么流转的。

运行方式（在 credit_risk_control_system 目录下）：
    python3 scripts/demo_qa.py

它会模拟一个用户问"上个月逾期率是多少"，然后打印出整条链路每一步的结果。
建议对照 pipeline.py 的代码一起看，理解每一步在干什么。
"""

import sys
from pathlib import Path

# 把项目根目录加进 sys.path，这样才能 import src 下的模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ai_assistant.llm_client import create_llm
from src.ai_assistant.schema_catalog import SchemaCatalog
from src.ai_assistant.pipeline import QAPipeline


def main():
    print("=" * 60)
    print("AI 数据问答层 演示")
    print("=" * 60)

    # ── 1. 组装：用工厂函数选 LLM（有 Key 用真 DeepSeek，没有用 Mock）──
    catalog = SchemaCatalog()
    llm = create_llm(catalog=catalog)
    pipeline = QAPipeline(llm=llm, catalog=catalog)

    # ── 2. 模拟用户提问 ──
    questions = [
        "上个月逾期率是多少？",          # 指标查询 → 完整链路
        "逾期率是什么意思？",            # 口径解释 → RAG 直接回答
        "你吃了吗？",                   # 闲聊 → 直接 LLM 回答
    ]

    for q in questions:
        print(f"\n👤 用户问：{q}")
        print("-" * 60)

        answer = pipeline.ask(q, user_id="user_001", user_role="analyst")

        print(f"🤖 系统答：{answer.answer}")
        if answer.sql:
            print(f"\n📝 执行的 SQL：\n{answer.sql}")
        print(f"🔍 trace_id：{answer.trace_id}")

    # ── 3. 展示审计日志（看看日志记了什么）──
    print("\n" + "=" * 60)
    print("审计日志（脱敏后）")
    print("=" * 60)
    import json
    for log in pipeline.audit.get_all():
        print(json.dumps(log, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
