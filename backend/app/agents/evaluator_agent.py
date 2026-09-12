from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.models import MockOAAttempt, MockOAVariant, QuestionBank, utc_now
from backend.app.engines.evaluator_registry import EvaluatorRegistry

class EvaluatorAgent:
    """
    Agent 5: Evaluation & Feedback Agent.
    Evaluates complete Mock OA attempts using the Evaluator Registry,
    generating deterministic topic-level accuracy, strong/weak categories, and evidence.
    """

    @classmethod
    def evaluate_mock_oa_attempt(
        cls,
        db: Session,
        attempt: MockOAAttempt,
        answers: Dict[str, Any],
        time_spent_per_question: Dict[str, int] = None,
        proctoring_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        variant = db.query(MockOAVariant).filter(MockOAVariant.id == attempt.mock_oa_variant_id).first()
        if not variant:
            raise ValueError("Variant not found")

        questions = db.query(QuestionBank).filter(QuestionBank.id.in_(variant.question_ids)).all()
        q_map = {q.id: q for q in questions}

        time_spent = time_spent_per_question or {}
        total_time_seconds = sum(time_spent.values())

        total_earned = 0.0
        total_possible = float(len(questions)) * 100.0 if questions else 100.0

        topic_stats: Dict[str, Dict[str, Any]] = {}
        question_reviews: List[Dict[str, Any]] = []

        for q_id, q in q_map.items():
            user_ans = answers.get(q_id, "")
            spent = time_spent.get(q_id, 0)

            q_dict = {
                "id": q.id,
                "question_type": q.question_type,
                "solution": q.solution,
                "approach": q.approach,
                "test_cases": q.test_cases_json,
                "prompt": q.prompt
            }

            eval_res = EvaluatorRegistry.evaluate(q.question_type, user_ans, q_dict)
            frac = eval_res.get("score_fraction", 0.0)
            q_score = round(frac * 100.0, 1)
            total_earned += q_score

            # Update topic stats
            t_name = q.topic
            if t_name not in topic_stats:
                topic_stats[t_name] = {"earned": 0.0, "possible": 0.0, "questions_count": 0}
            topic_stats[t_name]["earned"] += q_score
            topic_stats[t_name]["possible"] += 100.0
            topic_stats[t_name]["questions_count"] += 1

            question_reviews.append({
                "question_id": q.id,
                "title": q.title or q.topic,
                "subject": q.subject,
                "topic": q.topic,
                "subtopic": q.subtopic,
                "difficulty": q.difficulty,
                "question_type": q.question_type,
                "prompt": q.prompt,
                "user_answer": user_ans,
                "correct_answer": q.solution,
                "approach": q.approach,
                "score": q_score,
                "is_correct": eval_res.get("is_correct", False),
                "feedback": eval_res.get("feedback", ""),
                "test_case_results": eval_res.get("test_case_results", []),
                "time_spent_seconds": spent
            })

        overall_score = round(total_earned / len(questions), 1) if questions else 0.0
        strong_topics = []
        weak_topics = []

        for t_name, stat in topic_stats.items():
            acc = round((stat["earned"] / stat["possible"]) * 100.0, 1) if stat["possible"] > 0 else 0.0
            stat["accuracy_percentage"] = acc
            if acc >= 75.0:
                strong_topics.append(t_name)
            elif acc < 60.0:
                weak_topics.append(t_name)

        evaluation_data = {
            "overall_score": overall_score,
            "max_score": 100.0,
            "accuracy_by_topic": topic_stats,
            "strong_topics": strong_topics,
            "weak_topics": weak_topics,
            "time_spent_seconds": total_time_seconds,
            "questions_review": question_reviews,
            "proctoring_summary": proctoring_data
        }

        attempt.submitted_at = utc_now()
        attempt.answers_json = answers
        attempt.evaluation_json = evaluation_data
        attempt.score = overall_score
        db.commit()
        db.refresh(attempt)

        return evaluation_data
