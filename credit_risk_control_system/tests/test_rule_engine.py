"""规则引擎测试"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.decision_engine.rule_engine import (
    RuleEngine, SafeExpressionEvaluator, Decision, RuleResult
)


class TestSafeExpressionEvaluator:
    """AST 安全表达式求值器测试"""

    def setup_method(self):
        self.evaluator = SafeExpressionEvaluator()

    def test_simple_comparison(self):
        assert self.evaluator.evaluate("age > 18", {"age": 25}) is True
        assert self.evaluator.evaluate("age > 18", {"age": 15}) is False

    def test_equality(self):
        assert self.evaluator.evaluate("status == 'active'", {"status": "active"}) is True
        assert self.evaluator.evaluate("status == 'active'", {"status": "inactive"}) is False

    def test_and_condition(self):
        assert self.evaluator.evaluate(
            "age >= 18 and age <= 65",
            {"age": 30}
        ) is True
        assert self.evaluator.evaluate(
            "age >= 18 and age <= 65",
            {"age": 70}
        ) is False

    def test_or_condition(self):
        assert self.evaluator.evaluate(
            "fraud_score > 0.8 or age < 18",
            {"fraud_score": 0.9, "age": 30}
        ) is True
        assert self.evaluator.evaluate(
            "fraud_score > 0.8 or age < 18",
            {"fraud_score": 0.3, "age": 30}
        ) is False

    def test_not_condition(self):
        assert self.evaluator.evaluate(
            "not identity_verified",
            {"identity_verified": False}
        ) is True

    def test_boolean_var(self):
        assert self.evaluator.evaluate(
            "user_id_in_blacklist == True",
            {"user_id_in_blacklist": True}
        ) is True

    def test_missing_variable(self):
        with pytest.raises(ValueError, match="未在上下文中定义"):
            self.evaluator.evaluate("unknown_var > 0", {})

    def test_complex_expression(self):
        context = {
            "age": 25, "fraud_score": 0.3,
            "debt_to_income_ratio": 0.6, "multi_head_cnt_7d": 2,
        }
        result = self.evaluator.evaluate(
            "age >= 18 and age <= 65 and fraud_score <= 0.8 and "
            "debt_to_income_ratio <= 0.7 and multi_head_cnt_7d < 3",
            context,
        )
        assert result is True


class TestRuleEngine:
    """规则引擎集成测试"""

    def setup_method(self):
        self.engine = RuleEngine("config/rules/credit_policy.yaml")

    def test_load_rules(self):
        stats = self.engine.get_statistics()
        assert stats['total_rule_groups'] == 3
        assert stats['total_rules'] > 0

    def test_hard_reject_blacklist(self):
        """命中黑名单 → 直接拒绝"""
        context = {
            "user_id_in_blacklist": True,
            "age": 25, "fraud_score": 0.3,
        }
        results = self.engine.evaluate(context)
        assert len(results) == 1
        assert results[0].decision == Decision.REJECT
        assert results[0].rule_id == "BLACKLIST_HIT"

    def test_hard_reject_age(self):
        """年龄不满足 → 拒绝"""
        context = {
            "user_id_in_blacklist": False,
            "age": 16, "fraud_score": 0.3,
        }
        results = self.engine.evaluate(context)
        assert any(r.rule_id == "AGE_RESTRICTION" for r in results)

    def test_hard_reject_fraud(self):
        """欺诈分过高 → 拒绝"""
        context = {
            "user_id_in_blacklist": False,
            "age": 30, "fraud_score": 0.9,
        }
        results = self.engine.evaluate(context)
        assert any(r.rule_id == "FRAUD_SCORE_HIGH" for r in results)

    def test_pass_all_rules(self):
        """通过所有规则 → 默认批准"""
        context = {
            "user_id_in_blacklist": False,
            "age": 30,
            "fraud_score": 0.1,
            "device_rooted_flag": 0,
            "identity_verified": True,
            "multi_head_cnt_7d": 1,
            "debt_to_income_ratio": 0.3,
        }
        results = self.engine.evaluate(context)
        assert results[-1].decision == Decision.APPROVE
        assert results[-1].rule_id == "DEFAULT_APPROVE"

    def test_multi_head_manual_review(self):
        """多头借贷多 → 人工审核"""
        context = {
            "user_id_in_blacklist": False,
            "age": 30,
            "fraud_score": 0.1,
            "multi_head_cnt_7d": 6,
            "debt_to_income_ratio": 0.3,
        }
        results = self.engine.evaluate(context)
        assert any(
            r.decision == Decision.MANUAL_REVIEW
            for r in results
        )

    def test_debt_ratio_reduce_limit(self):
        """负债率高 → 降低额度"""
        context = {
            "user_id_in_blacklist": False,
            "age": 30,
            "fraud_score": 0.1,
            "multi_head_cnt_7d": 1,
            "debt_to_income_ratio": 0.75,
        }
        results = self.engine.evaluate(context)
        assert any(
            r.decision == Decision.REDUCE_LIMIT
            for r in results
        )
