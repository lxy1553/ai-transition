"""
评分卡映射 — 违约概率 → 信用评分 (300-900)

标准评分卡公式:
  score = base_score + factor * ln(odds)
  其中 odds = (1-p)/p, factor = PDO / ln(2)

参数说明:
  base_score: 基准分（对应 base_odds 的分数）
  base_odds: 基准 odds（如 20:1 即好人:坏人=20:1）
  PDO (Points to Double Odds): odds 翻倍时增加的分数

  设计: 使信用评分在 300-900 之间，评分越高表示风险越低。

参考设计文档: 01_金融信贷风控 AI 应用系统 — 系统架构设计.md §5.3 _prob_to_score()
"""

import numpy as np


class ScorecardMapper:
    """
    评分卡映射器。

    配置示例:
        base_score = 600   # odds=20:1 时得 600 分
        pdo = 50           # odds 翻倍到 40:1 时得 650 分
        min_score = 300
        max_score = 900
        pass_threshold = 500  # 低于此分拒绝或转人工
    """

    def __init__(
        self,
        base_score: float = 600,
        base_odds: float = 20,
        pdo: float = 50,
        min_score: float = 300,
        max_score: float = 900,
        pass_threshold: float = 500,
    ):
        self.base_score = base_score
        self.base_odds = base_odds
        self.pdo = pdo
        self.min_score = min_score
        self.max_score = max_score
        self.pass_threshold = pass_threshold

        # factor = PDO / ln(2)
        self.factor = pdo / np.log(2)

        # offset = base_score - factor * ln(base_odds)
        self.offset = base_score - self.factor * np.log(base_odds)

    def prob_to_score(self, prob: float) -> float:
        """
        违约概率 → 信用评分。

        公式: score = offset + factor * ln((1-p)/p)
        """
        prob_clipped = np.clip(prob, 1e-10, 1 - 1e-10)
        odds = (1 - prob_clipped) / prob_clipped
        score = self.offset + self.factor * np.log(odds)
        return float(np.clip(score, self.min_score, self.max_score))

    def score_to_prob(self, score: float) -> float:
        """
        信用评分 → 违约概率（反向映射）。
        """
        # score = offset + factor * ln((1-p)/p)
        # → (1-p)/p = exp((score - offset) / factor)
        # → p = 1 / (1 + exp((score - offset) / factor))
        odds = np.exp((score - self.offset) / self.factor)
        return float(1 / (1 + odds))

    def prob_to_decision(self, prob: float) -> str:
        """违约概率 → 审批决策"""
        score = self.prob_to_score(prob)
        return self.score_to_decision(score)

    def score_to_decision(self, score: float) -> str:
        """评分 → 审批决策"""
        if score >= self.pass_threshold:
            return "APPROVE"
        elif score >= self.pass_threshold - 50:
            return "MANUAL_REVIEW"
        else:
            return "REJECT"

    def score_bucket(self, score: float) -> str:
        """评分分档（用于监控和分群）"""
        if score >= 750:
            return "A+"
        elif score >= 700:
            return "A"
        elif score >= 650:
            return "B+"
        elif score >= 600:
            return "B"
        elif score >= 500:
            return "C"
        else:
            return "D"

    def batch_score(self, probs: np.ndarray) -> np.ndarray:
        """批量转换概率为评分"""
        probs_clipped = np.clip(probs, 1e-10, 1 - 1e-10)
        odds = (1 - probs_clipped) / probs_clipped
        scores = self.offset + self.factor * np.log(odds)
        return np.clip(scores, self.min_score, self.max_score)
