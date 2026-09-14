from typing import List, Dict, Any, Tuple, Optional
from backend.app.engines.scoring_policy import ScoringPolicy
from backend.app.engines.answer_evaluator import SemanticEvaluationResult

DEFAULT_SECTION_WEIGHTS = {
    "work_experience": 0.30,
    "projects": 0.30,
    "skills": 0.15,
    "education": 0.10,
    "certifications": 0.05,
    "achievements": 0.05,
    "extracurricular": 0.05,
    "other": 0.00,
}


class ScoringEngine:
    """
    Scoring Engine Adapter Layer.
    Directs all scoring operations to the deterministic ScoringPolicy.
    
    Retired features (no longer control scoring):
    - correct_possible() polynomial
    - incorrect_possible() polynomial
    - midpoint() scoring
    - LLM suggested_possible_points
    - LLM suggested_earned_points
    """

    @classmethod
    def evaluate_quality_points(
        cls,
        quality_band: str = "Average",
        depth_level: int = 1,
        difficulty: str = None,
        score_pct: float = None,
        suggested_possible: float = None,
        suggested_earned: float = None,
        is_non_answer: bool = False,
        is_clarification_attempt: bool = False,
        eval_result: Optional[SemanticEvaluationResult] = None,
        question_profile: Optional[Any] = None
    ) -> Tuple[float, float, str]:
        """
        Deterministic scoring interface.
        Uses continuous [0, 1] evaluation dimensions from eval_result or continuous mapping.
        Completely ignores LLM suggested points or legacy polynomial tables.
        """
        # If a SemanticEvaluationResult is provided, use it directly
        if eval_result is not None:
            return ScoringPolicy.calculate_turn_score(
                eval_result=eval_result,
                question_profile=question_profile
            )

        # Fallback continuous mapping for callers providing only qualitative band
        diff_val = 0.85 if difficulty == "hard" else (0.20 if difficulty == "easy" else 0.50)
        
        band_scores = {
            "Excellent": 1.00,
            "Good": 0.80,
            "Average": 0.50,
            "Weak": 0.20,
            "Incorrect": 0.00
        }
        evidence_score = band_scores.get(quality_band.strip().capitalize(), 0.50)
        if score_pct is not None and 0.0 <= score_pct <= 100.0:
            evidence_score = round(score_pct / 100.0, 4)

        synthetic_eval = SemanticEvaluationResult(
            answer_understanding="Candidate answer evaluated via continuous deterministic scoring policy.",
            reasoning_summary="Evaluated via deterministic ScoringPolicy.",
            correctness=evidence_score,
            objective_coverage=evidence_score,
            completeness=evidence_score,
            technical_validity=evidence_score,
            depth_demonstrated=min(1.0, depth_level / 5.0),
            reasoning_quality=evidence_score if not is_non_answer else 0.0,
            directness=1.0,
            confidence=0.85,
            is_non_answer=is_non_answer or quality_band == "Incorrect"
        )

        return ScoringPolicy.calculate_turn_score(
            eval_result=synthetic_eval,
            question_profile=question_profile,
            fallback_difficulty=diff_val
        )

    @classmethod
    def compute_aggregate_score(cls, evidence_records: List[Dict[str, Any]]) -> float:
        """
        Legacy adapter: returns float score /100.
        score = sum(earned_points) / sum(possible_points) * 100
        """
        score = ScoringPolicy.aggregate_item_score(evidence_records)
        return score if score is not None else 0.0

    @classmethod
    def compute_star_rating(cls, score_100: Optional[float]) -> float:
        """
        Legacy adapter: returns float star rating /5.0.
        """
        rating = ScoringPolicy.star_rating(score_100)
        return rating if rating is not None else 0.0

    @classmethod
    def compute_resume_weighted_score(
        cls,
        item_scores: List[Dict[str, Any]],
        section_weights: Dict[str, float] = None
    ) -> float:
        """
        Legacy adapter: returns overall weighted experience score /100.
        """
        score = ScoringPolicy.aggregate_relevance_weighted_experience_score(item_scores)
        return score if score is not None else 0.0

    # Direct access to pure ScoringPolicy methods
    aggregate_item_score = ScoringPolicy.aggregate_item_score
    aggregate_relevance_weighted_experience_score = ScoringPolicy.aggregate_relevance_weighted_experience_score
    aggregate_subject_score = ScoringPolicy.aggregate_subject_score
    star_rating = ScoringPolicy.star_rating
