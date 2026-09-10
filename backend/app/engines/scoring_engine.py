from typing import List, Dict, Any, Tuple

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
    @staticmethod
    def correct_possible(depth_level: int = 1, difficulty: str = None) -> float:
        """
        When answer is correct/good, weightage grows progressively with depth & toughness:
        - Depth 1 (Introductory / Easy): 4.5 to 5.5 pts (low weightage, correct was expected) -> below 6!
        - Depth 2 (Follow-up 1 / Moderate): 8.0 to 9.5 pts
        - Depth 3 (Follow-up 2 / Deeper trade-offs): 11.5 to 13.5 pts -> above 9!
        - Depth 4 (Follow-up 3 / Advanced constraints): 15.0 to 17.5 pts -> way above 9!
        - Depth 5 (Follow-up 4 / Extreme scale/internals): 18.5 to 21.0 pts -> massive reward!
        """
        base = 5.0 + 3.5 * (max(1, depth_level) - 1)
        if difficulty:
            d = difficulty.strip().lower()
            if d == "hard":
                base += 2.0
            elif d == "easy":
                base = min(base, 5.5)
        return round(base, 1)

    @staticmethod
    def incorrect_possible(depth_level: int = 1, difficulty: str = None) -> float:
        """
        When answer is incorrect/weak (Asymmetric penalty protection):
        - Depth 1 (Failed introductory/easy question): 10.0 to 11.5 pts in denominator! Heavy penalty drag because basics are required.
        - Depth 2 (Follow-up 1): 5.0 to 6.0 pts.
        - Depth 3 (Follow-up 2 / in-depth question): 2.5 to 3.0 pts! Candidate is protected from tough question penalties!
        - Depth 4 (Follow-up 3 / advanced internals): 2.0 to 2.5 pts!
        - Depth 5 (Follow-up 4 / extreme edge-cases): 1.5 to 2.0 pts!
        """
        d = max(1, depth_level)
        if d == 1:
            base = 11.0
        elif d == 2:
            base = 5.5
        elif d == 3:
            base = 2.8
        elif d == 4:
            base = 2.2
        else:
            base = 1.8

        if difficulty:
            diff = difficulty.strip().lower()
            if diff == "hard":
                base = min(base, 2.5)
            elif diff == "easy":
                base = max(base, 10.5)

        # In-depth follow-up protection: any depth >= 3 question has low failure denominator
        if d >= 3:
            base = min(base, 3.0)

        return round(base, 1)

    @staticmethod
    def midpoint(depth_level: int = 1, difficulty: str = None) -> float:
        return round((ScoringEngine.correct_possible(depth_level, difficulty) + ScoringEngine.incorrect_possible(depth_level, difficulty)) / 2.0, 1)

    @classmethod
    def evaluate_quality_points(
        cls,
        quality_band: str,
        depth_level: int = 1,
        difficulty: str = None,
        score_pct: float = None,
        suggested_possible: float = None,
        suggested_earned: float = None,
        is_non_answer: bool = False,
        is_clarification_attempt: bool = False
    ) -> Tuple[float, float, str]:
        """
        Dynamically and intelligently computes (earned_points, possible_points, severity).
        Decides marks dynamically based on question difficulty, project relevance, and answer substance:
        - Easy question + correct = low positive impact (possible 3.5 - 5.5 pts)
        - Easy question + wrong/non-answer = high negative impact (possible 9.0 - 12.0 pts, earned 0)
        - Hard question + correct = strong positive impact (possible 12.0 - 18.0 pts)
        - Hard question + wrong/non-answer = low negative impact (possible 2.0 - 3.2 pts, earned 0)
        - Non-answer / deflection (e.g. "i am totally aware about this"): earned points is strictly 0.0!
        - 2nd-Go Clarification Attempt:
          * If candidate provides specifications: Minute penalty (~12%), generous score.
          * If candidate still fails specifications after explicit prompting: High weightage (9.5 - 12.0 pts), 0.0 earned.
        """
        band = quality_band.strip().capitalize()
        if band not in ["Excellent", "Good", "Average", "Weak", "Incorrect"]:
            band = "Average"

        diff = (difficulty or "").strip().lower()
        if diff not in ["easy", "medium", "hard"]:
            diff = "hard" if depth_level >= 3 else ("easy" if depth_level == 1 else "medium")

        # 1. Determine severity
        if band in ["Excellent", "Good"]:
            severity = "NONE"
        elif band == "Average":
            severity = "MINOR"
        elif band == "Weak":
            severity = "MODERATE"
        else:
            severity = "SEVERE"

        # 2. Strict non-answer / deflection handling: no free points for empty answers
        is_empty_or_dodged = (
            is_non_answer
            or band == "Incorrect"
            or (score_pct is not None and score_pct <= 5.0)
        )

        if is_empty_or_dodged:
            earned = 0.0
            if is_clarification_attempt:
                # Failing after explicit specification prompt: heavy drag
                possible = suggested_possible if (suggested_possible and 9.0 <= suggested_possible <= 13.0) else 10.5
                severity = "SEVERE"
            elif diff == "easy":
                # Failing/dodging an easy question carries a strong negative drag
                possible = suggested_possible if (suggested_possible and 8.5 <= suggested_possible <= 12.5) else 10.5
            elif diff == "hard":
                # Failing/dodging a hard in-depth question carries low drag (candidate protected)
                possible = suggested_possible if (suggested_possible and 1.8 <= suggested_possible <= 3.5) else 2.6
            else:  # medium
                possible = suggested_possible if (suggested_possible and 4.5 <= suggested_possible <= 8.5) else 6.0
            return round(earned, 1), round(possible, 1), severity

        # 3. Dynamic possible points with intelligent context-aware bounds
        if suggested_possible and suggested_possible > 0:
            possible = float(suggested_possible)
            # Sanity guardrails based on the core principles
            if diff == "hard":
                if band in ["Excellent", "Good"]:
                    possible = max(11.0, min(possible, 20.0))
                else:
                    possible = max(2.0, min(possible, 3.5))
            elif diff == "easy":
                if band in ["Excellent", "Good"]:
                    possible = max(3.0, min(possible, 5.5))
                else:
                    possible = max(8.5, min(possible, 12.5))
            else:  # medium
                possible = max(5.0, min(possible, 9.0))
        else:
            # Dynamic fallback based on depth and difficulty
            if band in ["Excellent", "Good"]:
                if diff == "hard":
                    possible = 12.0 + 1.5 * max(0, depth_level - 2)
                elif diff == "easy":
                    possible = 4.5
                else:
                    possible = 7.5
            elif band == "Average":
                possible = 6.0 if diff != "hard" else 7.0
            else:  # Weak
                if diff == "hard":
                    possible = 2.6
                elif diff == "easy":
                    possible = 10.0
                else:
                    possible = 5.5

        # 4. Dynamic earned points
        if suggested_earned is not None and suggested_earned >= 0:
            earned = min(possible, max(0.0, float(suggested_earned)))
        else:
            if score_pct is not None and 0.0 <= score_pct <= 100.0:
                pct = score_pct / 100.0
            else:
                pct = 0.92 if band == "Excellent" else (0.76 if band == "Good" else (0.52 if band == "Average" else 0.22))
            earned = round(pct * possible, 1)

        # Minute penalty if answered correctly upon 2nd-go clarification (~12% deduction)
        if is_clarification_attempt and band in ["Excellent", "Good", "Average"]:
            earned = round(earned * 0.88, 1)

        earned = max(0.0, min(earned, possible))
        return round(earned, 1), round(possible, 1), severity

    @classmethod
    def compute_aggregate_score(cls, evidence_records: List[Dict[str, Any]]) -> float:
        """
        project_score or subject_score = SUM(earned_points) / SUM(possible_points) * 100
        """
        if not evidence_records:
            return 0.0
        total_earned = sum(r.get("earned_points", 0.0) for r in evidence_records)
        total_possible = sum(r.get("possible_points", 0.0) for r in evidence_records)
        if total_possible <= 0:
            return 0.0
        return round((total_earned / total_possible) * 100.0, 1)

    @classmethod
    def compute_star_rating(cls, score_100: float) -> float:
        """
        5-star rating = score / 20 (fractional, not rounded to whole integer)
        """
        return round(min(5.0, max(0.0, score_100 / 20.0)), 2)

    @classmethod
    def compute_resume_weighted_score(
        cls,
        item_scores: List[Dict[str, Any]],
        section_weights: Dict[str, float] = None
    ) -> float:
        """
        resume_related_score = SUM(item_score * item_relevance_weight) / SUM(item_relevance_weight)
        """
        if not item_scores:
            return 0.0
        total_weighted_points = 0.0
        total_weights = 0.0
        for item in item_scores:
            score = item.get("score", 0.0)
            weight = item.get("relevance_weight", 1.0)
            total_weighted_points += score * weight
            total_weights += weight

        if total_weights <= 0:
            return 0.0
        return round(total_weighted_points / total_weights, 1)
