from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from backend.app.engines.question_profile import QuestionProfile
from backend.app.engines.answer_evaluator import SemanticEvaluationResult


class ScoringPolicy:
    """
    Deterministic Mathematical Scoring Policy.
    
    INVARIANTS:
    - Continuous [0, 1] evaluation dimensions.
    - Asymmetric risk/reward via A = D*Q + (1-D)*(1-Q).
    - Excludes non-applicable dimensions and renormalizes.
    - No negative points.
    - No LLM points hallucination.
    - Untested items receive None (never a fabricated score).
    """

    W_MIN: float = 1.0
    W_MAX: float = 10.0

    # Evaluator dimension baseline weights summing to 1.00
    DIMENSION_WEIGHTS: Dict[str, float] = {
        "correctness_validity": 0.30,
        "objective_coverage": 0.20,
        "completeness": 0.15,
        "reasoning_quality": 0.10,
        "depth_demonstrated": 0.10,
        "specificity": 0.05,
        "ownership": 0.05,
        "directness": 0.05,
    }

    @classmethod
    def compute_semantic_evidence_score(
        cls,
        eval_result: SemanticEvaluationResult
    ) -> float:
        """
        Computes continuous semantic evidence score E_i in [0, 1] from evaluator dimensions.
        Excludes None/null dimensions and renormalizes active weights.
        """
        if eval_result.is_non_answer:
            return 0.0

        # Combine correctness and technical validity for the 0.30 weight block
        corr = eval_result.correctness
        tech_val = eval_result.technical_validity
        if corr is not None and tech_val is not None:
            combined_validity = (corr + tech_val) / 2.0
        elif corr is not None:
            combined_validity = corr
        elif tech_val is not None:
            combined_validity = tech_val
        else:
            combined_validity = None

        raw_dimensions: Dict[str, Optional[float]] = {
            "correctness_validity": combined_validity,
            "objective_coverage": eval_result.objective_coverage,
            "completeness": eval_result.completeness,
            "reasoning_quality": eval_result.reasoning_quality,
            "depth_demonstrated": eval_result.depth_demonstrated,
            "specificity": eval_result.specificity,
            "ownership": eval_result.ownership,
            "directness": eval_result.directness,
        }

        # Filter active non-None dimensions and renormalize
        active_weight_sum = 0.0
        weighted_val_sum = 0.0

        for dim_key, base_weight in cls.DIMENSION_WEIGHTS.items():
            val = raw_dimensions.get(dim_key)
            if val is not None:
                clamped_val = max(0.0, min(1.0, float(val)))
                weighted_val_sum += clamped_val * base_weight
                active_weight_sum += base_weight

        if active_weight_sum <= 0.0:
            return 0.5  # Fallback if all dimensions are somehow absent

        e_score = weighted_val_sum / active_weight_sum
        return max(0.0, min(1.0, round(e_score, 4)))

    @classmethod
    def compute_characteristic_complexity(
        cls,
        question_profile: Optional[QuestionProfile],
        fallback_difficulty: float = 0.5
    ) -> float:
        """
        Computes continuous question complexity C in [0, 1] from QuestionProfile.
        """
        if not question_profile:
            return max(0.0, min(1.0, fallback_difficulty))

        c = (
            0.35 * question_profile.cognitive_complexity
            + 0.35 * question_profile.technical_complexity
            + 0.30 * question_profile.reasoning_requirement
        )
        return max(0.0, min(1.0, round(c, 4)))

    @classmethod
    def compute_asymmetry(cls, difficulty: float, evidence_score: float) -> float:
        """
        A = D*Q + (1-D)*(1-Q)
        - easy (D~0) + poor (Q~0) -> A~1.0 (high denominator, heavy penalty)
        - easy (D~0) + strong (Q~1) -> A~0.0 (low denominator, modest reward)
        - hard (D~1) + poor (Q~0) -> A~0.0 (low denominator, protected failure)
        - hard (D~1) + strong (Q~1) -> A~1.0 (high denominator, high reward)
        """
        d = max(0.0, min(1.0, difficulty))
        q = max(0.0, min(1.0, evidence_score))
        a = (d * q) + ((1.0 - d) * (1.0 - q))
        return max(0.0, min(1.0, round(a, 4)))

    @classmethod
    def calculate_turn_score(
        cls,
        eval_result: SemanticEvaluationResult,
        question_profile: Optional[QuestionProfile] = None,
        fallback_difficulty: float = 0.5
    ) -> Tuple[float, float, str]:
        """
        Calculates (earned_points, possible_points, severity).
        
        W_i = clamp(W_MIN + (W_MAX - W_MIN) * (0.65*A + 0.35*C), W_MIN, W_MAX)
        M_i = W_i * E_i
        earned_points = M_i
        possible_points = W_i
        """
        # 1. Compute Semantic Evidence E_i (Q)
        e_i = cls.compute_semantic_evidence_score(eval_result)

        # 2. Get Difficulty D and Complexity C
        d = question_profile.difficulty if question_profile else fallback_difficulty
        c = cls.compute_characteristic_complexity(question_profile, fallback_difficulty=d)

        # 3. Compute Asymmetry Factor A
        a = cls.compute_asymmetry(difficulty=d, evidence_score=e_i)

        # 4. Compute Question Weight W_i (possible points)
        w_raw = cls.W_MIN + (cls.W_MAX - cls.W_MIN) * (0.65 * a + 0.35 * c)
        w_i = max(cls.W_MIN, min(cls.W_MAX, round(w_raw, 2)))

        # 5. Compute Earned Points M_i
        m_i = round(w_i * e_i, 2)
        m_i = max(0.0, min(m_i, w_i))

        # 6. Determine Severity
        if e_i >= 0.75:
            severity = "NONE"
        elif e_i >= 0.50:
            severity = "MINOR"
        elif e_i >= 0.25:
            severity = "MODERATE"
        else:
            severity = "SEVERE"

        return m_i, w_i, severity

    @classmethod
    def aggregate_item_score(
        cls,
        evidence_records: List[Dict[str, Any]]
    ) -> Optional[float]:
        """
        score = sum(earned_points) / sum(possible_points) * 100
        An untested item receives None (NOT a fake score).
        """
        if not evidence_records:
            return None

        total_earned = sum(float(r.get("earned_points", 0.0)) for r in evidence_records)
        total_possible = sum(float(r.get("possible_points", 0.0)) for r in evidence_records)

        if total_possible <= 0.0:
            return None

        return round((total_earned / total_possible) * 100.0, 1)

    @classmethod
    def aggregate_relevance_weighted_experience_score(
        cls,
        item_scores: List[Dict[str, Any]]
    ) -> Optional[float]:
        """
        Overall Experience Score = Σ(item_score × item_relevance) / Σ(item_relevance)
        The weighted pool includes BOTH Work Experience and Projects.
        Untested items (item_score is None) are strictly excluded from denominator and numerator.
        """
        if not item_scores:
            return None

        total_weighted_points = 0.0
        total_weights = 0.0

        for item in item_scores:
            score = item.get("score") if item.get("score") is not None else item.get("item_score")
            weight = float(item.get("relevance_weight", 1.0))
            if score is not None:
                total_weighted_points += float(score) * weight
                total_weights += weight

        if total_weights <= 0.0:
            return None

        return round(total_weighted_points / total_weights, 1)

    @classmethod
    def aggregate_subject_score(
        cls,
        subject_evidence_records: List[Dict[str, Any]]
    ) -> Optional[float]:
        """
        Subject Knowledge Score = Σ(subject earned) / Σ(subject possible) × 100
        Completely separate from experience scores. Returns None if untested.
        """
        if not subject_evidence_records:
            return None

        tot_earned = sum(float(r.get("earned_points", 0.0)) for r in subject_evidence_records)
        tot_possible = sum(float(r.get("possible_points", 0.0)) for r in subject_evidence_records)

        if tot_possible <= 0.0:
            return None

        return round((tot_earned / tot_possible) * 100.0, 1)

    @classmethod
    def star_rating(cls, score: Optional[float]) -> Optional[float]:
        """
        Converts 0-100 score to 5.0 star rating. Returns None if score is None.
        """
        if score is None:
            return None
        return round(min(5.0, max(0.0, float(score) / 20.0)), 2)
