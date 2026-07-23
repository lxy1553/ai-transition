"""
规则引擎 — 轻量级信贷审批决策引擎

设计原则:
- 使用 Python AST 安全求值条件表达式（无 eval() 风险）
- YAML 决策表定义规则，支持热更新
- 三层优先级短路：硬拒绝 → 风险评估 → 额度策略
- 每笔决策完整记录触达的规则和原因码

PRODUCTION 对比:
- 本实现: Python AST 安全求值器，适用 1000 条以下规则
- 大规模场景: 可替换为 Drools（Java）或自研 DSL 编译为字节码
  本模块定义了 RuleEngine 接口，替换只需实现相同 interface

参考设计文档:
- 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §5.1 决策表规则引擎
- 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §5.2 规则引擎伪代码
"""

import ast
import operator
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, Union

import yaml


# ═══════════════════════════════════════════════════════════
# 数据类型
# ═══════════════════════════════════════════════════════════


class Decision(str, Enum):
    """决策结果类型"""
    REJECT = "REJECT"               # 拒绝
    APPROVE = "APPROVE"             # 通过
    MANUAL_REVIEW = "MANUAL_REVIEW" # 转人工审核
    REDUCE_LIMIT = "REDUCE_LIMIT"   # 降低额度


@dataclass
class RuleResult:
    """单条规则的评估结果"""
    rule_id: str
    decision: Decision
    reason_code: str
    reason_desc: str
    triggered: bool = False
    eval_time_us: float = 0.0       # 条件求值耗时（微秒）

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "decision": self.decision.value,
            "reason_code": self.reason_code,
            "reason_desc": self.reason_desc,
            "triggered": self.triggered,
        }


@dataclass
class RuleDefinition:
    """规则定义（从YAML加载）"""
    id: str
    condition: str
    decision: Decision
    reason_code: str
    reason_desc: str
    priority: int
    overridable: bool = True
    action: Optional[dict] = None


# ═══════════════════════════════════════════════════════════
# AST 安全表达式求值器
# ═══════════════════════════════════════════════════════════

class SafeExpressionEvaluator:
    """
    基于 Python AST 的安全表达式求值器。

    安全保证:
    1. 只允许 ast.Compare, ast.BoolOp, ast.Name, ast.Constant 节点
    2. 变量值只能来自传入的 context 字典
    3. 不支持函数调用、属性访问等危险操作

    PRODUCTION NOTE:
    大规模规则（10万+条）建议使用编译型方案:
    - 将规则编译为 Python bytecode / C 扩展
    - 或使用 Apache Drools (Java) 的规则 Rete 算法
    """

    # 白名单: 允许的操作符
    _OP_MAP = {
        ast.Gt: operator.gt,
        ast.Lt: operator.lt,
        ast.GtE: operator.ge,
        ast.LtE: operator.le,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
    }

    def __init__(self):
        self._compiled_cache: dict[str, ast.Expression] = {}

    def evaluate(self, condition: str, context: dict[str, Any]) -> bool:
        """
        安全求值条件表达式。

        Args:
            condition: 如 "age >= 18 and age <= 65 and fraud_score < 0.8"
            context: 变量值字典

        Returns:
            条件是否为真

        Raises:
            ValueError: 表达式包含不允许的语法
        """
        try:
            tree = self._compile(condition)
            return self._eval_node(tree.body, context)
        except SyntaxError as e:
            raise ValueError(f"条件表达式语法错误: {condition!r} — {e}")
        except Exception as e:
            # 生产环境需要记录异常到监控
            raise ValueError(f"表达式求值失败: {condition!r} — {e}")

    def _compile(self, condition: str) -> ast.Expression:
        """编译表达式（带缓存）"""
        if condition not in self._compiled_cache:
            self._compiled_cache[condition] = ast.parse(
                condition, mode='eval'
            )
        return self._compiled_cache[condition]

    def _eval_node(self, node: ast.AST, context: dict) -> Any:
        """递归求值 AST 节点"""

        # 比较运算: a > b, a == b, a <= b
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            for op_node, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context)
                op_func = self._OP_MAP.get(type(op_node))
                if op_func is None:
                    raise ValueError(f"不支持的操作符: {type(op_node).__name__}")
                if not op_func(left, right):
                    return False
                left = right  # 链式比较 a < b < c
            return True

        # 布尔运算: a and b, a or b
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._eval_node(v, context) for v in node.values)
            elif isinstance(node.op, ast.Or):
                return any(self._eval_node(v, context) for v in node.values)

        # 一元操作: not a
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return not self._eval_node(node.operand, context)

        # 字面常量: 18, 0.8, "hello", True
        elif isinstance(node, ast.Constant):
            return node.value

        # 变量名: age, fraud_score
        elif isinstance(node, ast.Name):
            if node.id not in context:
                raise ValueError(
                    f"变量 '{node.id}' 未在上下文中定义。"
                    f"可用变量: {list(context.keys())}"
                )
            return context[node.id]

        raise ValueError(f"不支持的 AST 节点类型: {type(node).__name__}")


# ═══════════════════════════════════════════════════════════
# 规则引擎
# ═══════════════════════════════════════════════════════════

class RuleEngine:
    """
    轻量级信贷审批规则引擎。

    工作流程:
    1. 加载 YAML 规则定义文件
    2. 按 rule_groups 优先级排序
    3. 逐组逐条评估条件
    4. hard_reject 组命中 → 短路返回（不再评估后续组）
    5. 记录每条触发规则的 reason_code

    使用示例:
        engine = RuleEngine("config/rules/credit_policy.yaml")
        results = engine.evaluate({
            "age": 25, "fraud_score": 0.3,
            "multi_head_cnt_7d": 2, "debt_to_income_ratio": 0.4,
            ...
        })
        # results = [RuleResult(...), ...]

    PRODUCTION NOTE — 生产环境扩展方向:
    1. 规则热更新: 使用 inotify/watchdog 监听YAML文件变化，自动 reload
    2. 规则版本管理: 每次更新记录版本号，决策日志携带 rule_version
    3. 规则灰度: 支持对部分流量先应用新规则
    4. 规则效能分析: 统计每条规则的命中率和贡献度
    """

    def __init__(self, rules_config_path: Union[str, Path]):
        """
        初始化规则引擎。

        Args:
            rules_config_path: 规则 YAML 配置文件路径
        """
        self.config_path = Path(rules_config_path)
        self.evaluator = SafeExpressionEvaluator()
        self.rule_groups: list[dict] = []
        self._all_rules: list[RuleDefinition] = []
        self._load_rules()

    def _load_rules(self) -> None:
        """加载并解析 YAML 规则配置"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        self.rule_groups = config.get('rule_groups', [])
        self._all_rules = []

        # 按优先级排序规则组
        self.rule_groups.sort(key=lambda g: g.get('priority', 999))

        # 解析所有规则为 RuleDefinition 对象
        for group in self.rule_groups:
            group_priority = group.get('priority', 999)
            for rule_def in group.get('rules', []):
                # action-only rules default to APPROVE (额度策略等)
                decision = rule_def.get('decision', 'APPROVE')
                self._all_rules.append(RuleDefinition(
                    id=rule_def['id'],
                    condition=rule_def.get('condition', 'True'),
                    decision=Decision(decision),
                    reason_code=rule_def.get('reason_code', 'RC_DEFAULT'),
                    reason_desc=rule_def.get('reason_desc', ''),
                    priority=group_priority,
                    overridable=rule_def.get('overridable', True),
                    action=rule_def.get('action'),
                ))

    def reload(self) -> None:
        """
        热更新: 重新加载规则配置文件。

        PRODUCTION: 在 Kubernetes ConfigMap 更新后调用此方法。
        可配合文件监听（watchdog）自动触发。
        """
        self._load_rules()

    def evaluate(self, context: dict[str, Any]) -> list[RuleResult]:
        """
        按优先级执行所有规则组，执行决策。

        Args:
            context: 特征字典 + 特殊变量
                如: {
                    'age': 25, 'fraud_score': 0.3,
                    'multi_head_cnt_7d': 2, ...
                    'user_id_in_blacklist': False,  # 业务方注入
                    'device_rooted_flag': 0,
                    'identity_verified': True,
                }

        Returns:
            触发的规则结果列表（按优先级排序）

            最短: 只有一条 REJECT（硬拒绝短路）
            默认: 不触发任何规则时，返回一条 APPROVE
        """
        results: list[RuleResult] = []
        is_hard_rejected = False

        for group in self.rule_groups:
            group_name = group.get('name', 'unknown')

            for rule_def in group.get('rules', []):
                # 评估条件
                t0 = time.perf_counter()
                try:
                    condition = rule_def.get('condition', 'True')
                    matched = self.evaluator.evaluate(
                        condition, context
                    )
                except ValueError as e:
                    # 条件中包含上下文中不存在的变量
                    # PRODUCTION: 这种情况应记录错误日志 + 告警
                    matched = False

                eval_time_us = (time.perf_counter() - t0) * 1_000_000

                if matched:
                    decision = rule_def.get('decision', 'APPROVE')
                    result = RuleResult(
                        rule_id=rule_def['id'],
                        decision=Decision(decision),
                        reason_code=rule_def.get('reason_code', 'RC_DEFAULT'),
                        reason_desc=rule_def.get('reason_desc', ''),
                        triggered=True,
                        eval_time_us=eval_time_us,
                    )
                    results.append(result)

                    # 硬拒绝短路逻辑
                    if (group_name == 'hard_reject' and
                            not rule_def.get('overridable', True)):
                        is_hard_rejected = True
                        break

            if is_hard_rejected:
                break

        # 无规则触发 → 默认通过
        if not results:
            results.append(RuleResult(
                rule_id="DEFAULT_APPROVE",
                decision=Decision.APPROVE,
                reason_code="RC_OK",
                reason_desc="通过所有规则检查",
                triggered=True,
            ))

        return results

    def get_rule(self, rule_id: str) -> Optional[RuleDefinition]:
        """根据 ID 查找规则定义"""
        for rule in self._all_rules:
            if rule.id == rule_id:
                return rule
        return None

    def get_statistics(self) -> dict:
        """获取规则引擎统计信息（用于监控）"""
        return {
            "total_rule_groups": len(self.rule_groups),
            "total_rules": len(self._all_rules),
            "rules_by_decision": {
                d.value: sum(1 for r in self._all_rules if r.decision == d)
                for d in Decision
            },
            "config_path": str(self.config_path),
        }
