"""模型训练与评估测试"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pytest

from src.models.evaluator import ModelEvaluator
from src.models.scorecard import ScorecardMapper
from src.models.woe_iv import WOECalculator


class TestWOEIV:
    """WOE/IV 计算测试"""

    def test_basic_woe(self):
        import pandas as pd
        np.random.seed(42)
        df = pd.DataFrame({
            'feature': np.concatenate([
                np.random.normal(0, 1, 500),   # 好人
                np.random.normal(3, 1, 100),   # 坏人（分布差异更大，避免分箱合并）
            ]),
            'label': [0] * 500 + [1] * 100,
        })

        calc = WOECalculator(bins=5)
        results = calc.calculate(df, ['feature'])

        assert len(results) == 1
        # 分布有差异 → IV > 0
        assert results[0].total_iv > 0

    def test_no_predictive_power(self):
        """随机特征 → IV ≈ 0"""
        import pandas as pd
        df = pd.DataFrame({
            'feature': np.random.normal(0, 1, 500),
            'label': np.random.choice([0, 1], 500),
        })
        calc = WOECalculator(bins=5)
        results = calc.calculate(df, ['feature'])
        # 随机特征 IV 应很小
        assert results[0].total_iv < 0.1


class TestScorecardMapper:
    """评分卡映射测试"""

    def setup_method(self):
        self.mapper = ScorecardMapper(
            base_score=600, base_odds=20,
            pdo=50, min_score=300, max_score=900,
        )

    def test_prob_zero(self):
        score = self.mapper.prob_to_score(0.01)
        assert score > 700  # 极低违约概率 → 高分

    def test_prob_one(self):
        score = self.mapper.prob_to_score(0.50)
        assert score < 600  # 高违约概率 → 低分

    def test_roundtrip(self):
        """概率 → 分数 → 概率，应近似相等"""
        for prob in [0.05, 0.10, 0.20, 0.30]:
            score = self.mapper.prob_to_score(prob)
            prob_back = self.mapper.score_to_prob(score)
            assert abs(prob - prob_back) < 0.05

    def test_score_range(self):
        """评分在 300-900 之间"""
        for prob in [1e-6, 0.5, 1 - 1e-6]:
            score = self.mapper.prob_to_score(prob)
            assert 300 <= score <= 900

    def test_decision_threshold(self):
        """评分 → 决策映射"""
        assert self.mapper.score_to_decision(650) == "APPROVE"
        assert self.mapper.score_to_decision(480) == "MANUAL_REVIEW"
        assert self.mapper.score_to_decision(300) == "REJECT"

    def test_batch_score(self):
        probs = np.array([0.05, 0.10, 0.20, 0.30, 0.50])
        scores = self.mapper.batch_score(probs)
        assert len(scores) == 5
        # 概率越高，分数越低（单调递减）
        assert np.all(np.diff(scores) < 0)


class TestModelEvaluator:
    """模型评估器测试"""

    def setup_method(self):
        self.evaluator = ModelEvaluator()

    def test_ks_perfect(self):
        """完美分离 → KS ≈ 1.0"""
        y_true = np.array([0] * 100 + [1] * 100)
        y_pred = np.array([0.1] * 100 + [0.9] * 100)
        ks = self.evaluator._calculate_ks(y_true, y_pred)
        assert ks > 0.9

    def test_ks_random(self):
        """随机预测 → KS ≈ 0"""
        np.random.seed(42)
        y_true = np.array([0] * 100 + [1] * 100)
        y_pred = np.random.random(200)
        ks = self.evaluator._calculate_ks(y_true, y_pred)
        assert ks < 0.3

    def test_psi_same(self):
        """相同分布 → PSI ≈ 0"""
        expected = np.random.beta(3, 5, 1000)
        actual = np.random.beta(3, 5, 1000)
        psi = self.evaluator._calculate_psi(expected, actual)
        assert psi < 0.1

    def test_psi_different(self):
        """不同分布 → PSI > 0"""
        expected = np.random.beta(3, 5, 1000)   # mean ≈ 0.38
        actual = np.random.beta(8, 2, 1000)      # mean ≈ 0.80
        psi = self.evaluator._calculate_psi(expected, actual)
        assert psi > 0.5
