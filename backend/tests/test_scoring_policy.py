import unittest
from backend.app.engines.question_profile import QuestionProfile, QuestionKind
from backend.app.engines.answer_evaluator import SemanticEvaluationResult, CandidateClaimExtraction
from backend.app.engines.scoring_policy import ScoringPolicy
from backend.app.engines.scoring_engine import ScoringEngine


class TestScoringPolicy(unittest.TestCase):

    def test_asymmetry_formula_mathematical_behavior(self):
        """
        Verifies the behavior of A = D*Q + (1-D)*(1-Q) and resulting question weight W:
        - easy + poor -> higher denominator
        - easy + strong -> lower denominator
        - hard + poor -> lower denominator (protected failure)
        - hard + strong -> higher denominator (high reward)
        """
        # Easy question (D = 0.10)
        a_easy_poor = ScoringPolicy.compute_asymmetry(difficulty=0.10, evidence_score=0.0)
        a_easy_strong = ScoringPolicy.compute_asymmetry(difficulty=0.10, evidence_score=1.0)
        self.assertGreater(a_easy_poor, a_easy_strong)
        self.assertAlmostEqual(a_easy_poor, 0.90, places=2)
        self.assertAlmostEqual(a_easy_strong, 0.10, places=2)

        # Hard question (D = 0.90)
        a_hard_poor = ScoringPolicy.compute_asymmetry(difficulty=0.90, evidence_score=0.0)
        a_hard_strong = ScoringPolicy.compute_asymmetry(difficulty=0.90, evidence_score=1.0)
        self.assertGreater(a_hard_strong, a_hard_poor)
        self.assertAlmostEqual(a_hard_poor, 0.10, places=2)
        self.assertAlmostEqual(a_hard_strong, 0.90, places=2)

        # Resulting weights W
        profile_easy = QuestionProfile(
            question_id="q_easy",
            objective="Factual tool inquiry",
            topic="Basics",
            difficulty=0.10,
            cognitive_complexity=0.10,
            technical_complexity=0.10,
            reasoning_requirement=0.10
        )
        profile_hard = QuestionProfile(
            question_id="q_hard",
            objective="Distributed consensus under network partition",
            topic="Consensus",
            difficulty=0.90,
            cognitive_complexity=0.90,
            technical_complexity=0.90,
            reasoning_requirement=0.90
        )

        eval_poor = SemanticEvaluationResult(
            answer_understanding="Poor attempt",
            reasoning_summary="Incorrect response",
            correctness=0.0,
            objective_coverage=0.0,
            completeness=0.0,
            technical_validity=0.0,
            depth_demonstrated=0.0,
            directness=0.0,
            confidence=0.5
        )

        eval_strong = SemanticEvaluationResult(
            answer_understanding="Strong attempt",
            reasoning_summary="Flawless explanation",
            correctness=1.0,
            objective_coverage=1.0,
            completeness=1.0,
            technical_validity=1.0,
            depth_demonstrated=1.0,
            reasoning_quality=1.0,
            specificity=1.0,
            ownership=1.0,
            directness=1.0,
            confidence=1.0
        )

        earned_ep, w_easy_poor, _ = ScoringPolicy.calculate_turn_score(eval_poor, profile_easy)
        earned_es, w_easy_strong, _ = ScoringPolicy.calculate_turn_score(eval_strong, profile_easy)
        earned_hp, w_hard_poor, _ = ScoringPolicy.calculate_turn_score(eval_poor, profile_hard)
        earned_hs, w_hard_strong, _ = ScoringPolicy.calculate_turn_score(eval_strong, profile_hard)

        # Easy + poor -> higher denominator than easy + strong
        self.assertGreater(w_easy_poor, w_easy_strong)
        # Hard + strong -> higher denominator than hard + poor
        self.assertGreater(w_hard_strong, w_hard_poor)
        # Earned points strictly non-negative
        self.assertEqual(earned_ep, 0.0)
        self.assertGreater(earned_hs, 0.0)

    def test_dimension_renormalization_when_optional_is_none(self):
        """
        Verifies that if optional dimensions (reasoning_quality, specificity, ownership) are None,
        they are excluded and active weights are renormalized rather than treating None as 0.0.
        """
        eval_with_none = SemanticEvaluationResult(
            answer_understanding="Factual one-word answer",
            reasoning_summary="Direct answer without reasoning",
            correctness=1.0,
            objective_coverage=1.0,
            completeness=1.0,
            technical_validity=1.0,
            depth_demonstrated=1.0,
            reasoning_quality=None,  # Excluded!
            specificity=None,        # Excluded!
            ownership=None,          # Excluded!
            directness=1.0,
            confidence=1.0
        )

        # Since all active dimensions are 1.0, E must equal exactly 1.0!
        # If None were treated as 0.0, E would be ~0.80. Renormalization guarantees 1.0!
        e_score = ScoringPolicy.compute_semantic_evidence_score(eval_with_none)
        self.assertEqual(e_score, 1.0)

    def test_one_word_factual_answer_can_receive_e_one(self):
        """
        A one-word factual answer (e.g. 'PostgreSQL') can receive E=1.0 and full possible points.
        """
        factual_eval = SemanticEvaluationResult(
            answer_understanding="PostgreSQL",
            reasoning_summary="Direct factual tool identification",
            correctness=1.0,
            objective_coverage=1.0,
            completeness=1.0,
            technical_validity=1.0,
            depth_demonstrated=0.5,
            reasoning_quality=None,
            specificity=1.0,
            ownership=None,
            directness=1.0,
            confidence=1.0
        )
        profile = QuestionProfile(
            question_id="q_fact",
            objective="Name database",
            topic="DB",
            difficulty=0.2,
            reasoning_requirement=0.1
        )

        earned, possible, severity = ScoringPolicy.calculate_turn_score(factual_eval, profile)
        self.assertGreaterEqual(earned, possible * 0.90)
        self.assertEqual(severity, "NONE")

    def test_strict_non_answer_handling(self):
        """
        Non-answers strictly yield E=0.0, earned_points=0.0, severity=SEVERE. No negative points.
        """
        evasion_eval = SemanticEvaluationResult(
            answer_understanding="Candidate deflected",
            reasoning_summary="No knowledge",
            is_non_answer=True,
            correctness=0.0,
            objective_coverage=0.0
        )
        earned, possible, severity = ScoringPolicy.calculate_turn_score(evasion_eval)
        self.assertEqual(earned, 0.0)
        self.assertGreater(possible, 0.0)
        self.assertEqual(severity, "SEVERE")

    def test_aggregate_item_score(self):
        """
        score = sum(earned) / sum(possible) * 100
        Untested item must return None (NOT a fake default).
        """
        # 1. Untested item returns None
        self.assertIsNone(ScoringPolicy.aggregate_item_score([]))

        # 2. Tested item with evidence
        records = [
            {"earned_points": 3.0, "possible_points": 4.0},
            {"earned_points": 5.0, "possible_points": 6.0},
        ]
        # total_earned = 8.0, total_possible = 10.0 -> 80.0%
        score = ScoringPolicy.aggregate_item_score(records)
        self.assertEqual(score, 80.0)

    def test_aggregate_relevance_weighted_experience_score(self):
        """
        Overall Experience Score = Σ(item_score × item_relevance) / Σ(item_relevance)
        The weighted pool includes BOTH Work Experience and Projects.
        Untested items are strictly excluded.
        """
        # Work Exp 1: score 90.0, weight 0.90
        # Work Exp 2: untested (score=None) -> must be excluded!
        # Project 1: score 80.0, weight 0.80
        # Project 2: score 70.0, weight 0.50
        item_scores = [
            {"item_id": "exp_1", "item_type": "WORK_EXPERIENCE", "score": 90.0, "relevance_weight": 0.90},
            {"item_id": "exp_2", "item_type": "WORK_EXPERIENCE", "score": None, "relevance_weight": 0.60},
            {"item_id": "proj_1", "item_type": "PROJECT", "score": 80.0, "relevance_weight": 0.80},
            {"item_id": "proj_2", "item_type": "PROJECT", "score": 70.0, "relevance_weight": 0.50},
        ]

        # Weighted: (90 * 0.9 + 80 * 0.8 + 70 * 0.5) / (0.9 + 0.8 + 0.5)
        # = (81.0 + 64.0 + 35.0) / 2.2 = 180.0 / 2.2 = 81.818... -> 81.8
        overall = ScoringPolicy.aggregate_relevance_weighted_experience_score(item_scores)
        self.assertEqual(overall, 81.8)

        # If all untested: returns None
        self.assertIsNone(ScoringPolicy.aggregate_relevance_weighted_experience_score([
            {"score": None, "relevance_weight": 1.0}
        ]))

    def test_aggregate_subject_score(self):
        """
        Subject Knowledge Score = Σ(subject earned) / Σ(subject possible) * 100
        Completely separate from experience scores. Returns None if untested.
        """
        # Untested returns None
        self.assertIsNone(ScoringPolicy.aggregate_subject_score([]))

        subject_records = [
            {"earned_points": 7.5, "possible_points": 10.0},
            {"earned_points": 8.5, "possible_points": 10.0},
        ]
        # (16.0 / 20.0) * 100 = 80.0%
        subj_score = ScoringPolicy.aggregate_subject_score(subject_records)
        self.assertEqual(subj_score, 80.0)

    def test_star_rating(self):
        """star_rating converts 0-100 to 0-5.0, or None if score is None."""
        self.assertIsNone(ScoringPolicy.star_rating(None))
        self.assertEqual(ScoringPolicy.star_rating(100.0), 5.0)
        self.assertEqual(ScoringPolicy.star_rating(80.0), 4.0)
        self.assertEqual(ScoringPolicy.star_rating(0.0), 0.0)
        self.assertEqual(ScoringPolicy.star_rating(72.5), 3.62)

    def test_scoring_engine_adapter_compatibility(self):
        """Verifies ScoringEngine adapter correctly routes to ScoringPolicy."""
        earned, possible, severity = ScoringEngine.evaluate_quality_points(
            quality_band="Good",
            difficulty="medium",
            suggested_possible=999.0,  # Ignored!
            suggested_earned=888.0    # Ignored!
        )
        self.assertLess(possible, 11.0)
        self.assertGreaterEqual(earned, 0.0)
        self.assertIn(severity, ["NONE", "MINOR", "MODERATE", "SEVERE"])


if __name__ == "__main__":
    unittest.main()
