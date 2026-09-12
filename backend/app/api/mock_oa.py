from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import MockOAVariant, MockOAAttempt, QuestionBank, User
from backend.app.schemas.schemas import (
    MockOAStartRequest, MockOAVariantOut, QuestionOut, MockOASubmitRequest, MockOAReportOut,
    RunCodeRequest, RunCodeResponse, TestCaseResult
)
from backend.app.agents.mock_oa_agent import MockOAAgent
from backend.app.agents.evaluator_agent import EvaluatorAgent
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/mock-oa", tags=["Mock OA Engine"])

@router.post("/run", response_model=RunCodeResponse)
def run_code(payload: RunCodeRequest, db: Session = Depends(get_db)):
    """
    HackerRank/LeetCode-grade immediate code execution against sample & custom test cases.
    Supports C, C++ (17/20/23), Java, Python 3, JavaScript, TypeScript, Go, Rust, and SQL.
    """
    from backend.app.engines.sandbox_runner import SandboxRunner

    question = db.query(QuestionBank).filter(QuestionBank.id == payload.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    test_cases = question.test_cases_json or []
    if not payload.custom_input:
        test_cases = [tc for tc in test_cases if not tc.get("is_hidden")]

    res = SandboxRunner.evaluate_code(
        user_code=payload.code,
        language=payload.language,
        test_cases=test_cases,
        custom_input=payload.custom_input,
        approach=question.approach or "O(N) Time, O(1) Space",
        timeout_seconds=4.0
    )

    tc_results = [
        TestCaseResult(
            test_case_index=r.get("test_case_index", idx + 1),
            input_data=str(r.get("input_data", "")),
            expected_output=str(r.get("expected_output", "")),
            actual_output=str(r.get("actual_output", "")),
            passed=bool(r.get("passed", False)),
            runtime_ms=float(r.get("runtime_ms", 1.0)),
            memory_mb=float(r.get("memory_mb", 14.0))
        )
        for idx, r in enumerate(res.get("test_case_results", []))
    ]

    total_time = sum([r.runtime_ms or 0.0 for r in tc_results])
    max_mem = max([r.memory_mb or 0.0 for r in tc_results], default=14.0)

    return RunCodeResponse(
        status=res.get("status", "ACCEPTED" if res.get("is_correct") else "WRONG_ANSWER"),
        runtime_ms=round(total_time, 2),
        memory_mb=round(max_mem, 1),
        test_case_results=tc_results,
        compiler_output=res.get("compiler_output"),
        feedback=res.get("feedback")
    )

@router.post("/start", response_model=MockOAVariantOut)
def start_mock_oa(payload: MockOAStartRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = current_user.id

    variant, attempt, days_remaining = MockOAAgent.start_mock_oa(
        db=db,
        user_id=user_id,
        company=payload.company,
        role=payload.role
    )

    questions = db.query(QuestionBank).filter(QuestionBank.id.in_(variant.question_ids)).all()
    q_outs = [
        QuestionOut(
            id=q.id,
            subject=q.subject,
            topic=q.topic,
            subtopic=q.subtopic,
            question_type=q.question_type,
            difficulty=q.difficulty,
            title=q.title,
            prompt=q.prompt,
            options=q.options_json,
            starter_code=q.starter_code,
            test_cases=[tc for tc in (q.test_cases_json or []) if not tc.get("is_hidden")]
        )
        for q in questions
    ]

    return MockOAVariantOut(
        id=variant.id,
        company=variant.company,
        role=variant.role,
        time_window_id=variant.time_window_id,
        attempt_number=variant.attempt_number,
        user_attempt_count=attempt.user_attempt_count,
        duration_minutes=variant.duration_minutes,
        window_expires_in_days=days_remaining,
        questions=q_outs,
        mock_oa_attempt_id=attempt.id
    )

@router.post("/attempts/{id}/submit", response_model=MockOAReportOut)
def submit_mock_oa(id: str, payload: MockOASubmitRequest, db: Session = Depends(get_db)):
    attempt = db.query(MockOAAttempt).filter(MockOAAttempt.id == id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Mock OA Attempt not found")

    variant = db.query(MockOAVariant).filter(MockOAVariant.id == attempt.mock_oa_variant_id).first()

    eval_data = EvaluatorAgent.evaluate_mock_oa_attempt(
        db=db,
        attempt=attempt,
        answers=payload.answers,
        time_spent_per_question=payload.time_spent_per_question,
        proctoring_data=payload.proctoring_data
    )

    return MockOAReportOut(
        attempt_id=attempt.id,
        company=variant.company if variant else "Company",
        role=variant.role if variant else "Role",
        attempt_number=variant.attempt_number if variant else 1,
        total_score=eval_data["overall_score"],
        max_possible_score=eval_data["max_score"],
        percentage=eval_data["overall_score"],
        accuracy_by_topic=eval_data["accuracy_by_topic"],
        strong_topics=eval_data["strong_topics"],
        weak_topics=eval_data["weak_topics"],
        time_spent_seconds=eval_data["time_spent_seconds"],
        questions_review=eval_data["questions_review"],
        submitted_at=attempt.submitted_at,
        proctoring_summary=eval_data.get("proctoring_summary")
    )

@router.get("/attempts/{id}/report", response_model=MockOAReportOut)
def get_mock_oa_report(id: str, db: Session = Depends(get_db)):
    attempt = db.query(MockOAAttempt).filter(MockOAAttempt.id == id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    variant = db.query(MockOAVariant).filter(MockOAVariant.id == attempt.mock_oa_variant_id).first()
    eval_data = attempt.evaluation_json or {}

    return MockOAReportOut(
        attempt_id=attempt.id,
        company=variant.company if variant else "Company",
        role=variant.role if variant else "Role",
        attempt_number=variant.attempt_number if variant else 1,
        total_score=eval_data.get("overall_score", 0.0),
        max_possible_score=eval_data.get("max_score", 100.0),
        percentage=eval_data.get("overall_score", 0.0),
        accuracy_by_topic=eval_data.get("accuracy_by_topic", {}),
        strong_topics=eval_data.get("strong_topics", []),
        weak_topics=eval_data.get("weak_topics", []),
        time_spent_seconds=eval_data.get("time_spent_seconds", 0),
        questions_review=eval_data.get("questions_review", []),
        submitted_at=attempt.submitted_at or attempt.started_at,
        proctoring_summary=eval_data.get("proctoring_summary")
    )
