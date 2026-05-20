"""Day 10 - 结构化输出校验 Demo。

这个脚本模拟模型返回 JSON 后，服务端如何做格式校验和业务校验。
用途是说明：AI 应用不能只看模型是否返回一段文字，还要确认字段完整、类型正确、业务规则成立。
"""

import json
from typing import Any, Optional


REQUIRED_FIELDS = {
    "summary": str,
    "risk_level": str,
    "can_publish": bool,
    "risks": list,
    "missing_context": list,
    "suggestions": list,
}

VALID_RISK_LEVELS = {"low", "medium", "high"}


MODEL_RESPONSE = """
{
  "summary": "统计指定日期每个城市的活跃用户数",
  "risk_level": "medium",
  "can_publish": false,
  "risks": [
    "需要确认 active_users 的业务口径",
    "group by city 可能带来聚合开销"
  ],
  "missing_context": [
    "user_events 表结构",
    "活跃用户定义"
  ],
  "suggestions": [
    "补充 user_events 字段说明",
    "确认 dt 是否为分区字段"
  ]
}
"""


def validate_required_fields(data: dict[str, Any]) -> list[str]:
    """校验模型输出是否包含系统需要的字段和类型。

    JSON 能解析不代表业务能用。
    如果缺少 `risk_level`、`can_publish` 等字段，下游流程就无法做风险判断。
    """
    errors: list[str] = []

    for field_name, expected_type in REQUIRED_FIELDS.items():
        if field_name not in data:
            errors.append(f"missing field: {field_name}")
            continue

        if not isinstance(data[field_name], expected_type):
            errors.append(f"field {field_name} should be {expected_type.__name__}")

    return errors


def validate_business_rules(data: dict[str, Any]) -> list[str]:
    """校验字段之间是否符合业务规则。

    结构合法只是第一步，还要检查业务含义是否矛盾。
    例如高风险 SQL 不能被标记为可上线，缺少上下文时也不能直接放行。
    """
    errors: list[str] = []

    risk_level = data.get("risk_level")
    can_publish = data.get("can_publish")
    missing_context = data.get("missing_context")

    if isinstance(risk_level, str) and risk_level not in VALID_RISK_LEVELS:
        errors.append(f"risk_level should be one of {sorted(VALID_RISK_LEVELS)}")

    if risk_level == "high" and can_publish is not False:
        errors.append("high risk SQL should not be publishable")

    if isinstance(missing_context, list) and missing_context and can_publish is True:
        errors.append("SQL with missing context should require review before publish")

    return errors


def validate_model_response(raw_response: str) -> tuple[Optional[dict[str, Any]], list[str]]:
    """解析并校验模型原始输出。

    这里把 JSON 解析、字段校验、业务校验放在一个入口里。
    调用方只需要看返回的 data 和 errors，就能决定是否进入人工复核或继续流程。
    """
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        return None, [f"invalid json: {exc}"]

    errors = validate_required_fields(data)
    errors.extend(validate_business_rules(data))
    return data, errors


def main() -> None:
    """运行结构化输出校验，并根据校验结果做流程决策。

    这个流程对应生产系统里的自动风控：模型输出不可信时不能直接进入下一步。
    """
    data, errors = validate_model_response(MODEL_RESPONSE)

    print("=== SQL Risk Check Output ===")
    if data is not None:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    print()

    print("=== Validation Result ===")
    if errors:
        print("failed")
        for error in errors:
            print(f"- {error}")
    else:
        print("passed")

    print()
    print("=== Workflow Decision ===")
    if not data or errors:
        print("进入人工复核：模型输出不可信或格式不符合要求。")
    elif data["can_publish"]:
        print("允许上线：当前未发现阻断风险。")
    else:
        print("暂不允许上线：需要补充上下文或处理风险。")


if __name__ == "__main__":
    main()
