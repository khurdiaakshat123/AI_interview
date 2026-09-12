from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from backend.app.database import get_db
from backend.app.models.models import PracticeSession, QuestionBank, User, TimeWindow
from backend.app.schemas.schemas import (
    PracticeSessionCreate, QuestionOut, CheckAnswerRequest, CheckAnswerResponse,
    HintResponse, ApproachResponse, SolutionResponse
)
from backend.app.agents.practice_agent import PracticeAgent
from backend.app.agents.mock_oa_agent import MockOAAgent
from backend.app.engines.evaluator_registry import EvaluatorRegistry
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/practice", tags=["Practice Engine"])

@router.post("/sessions")
def create_practice_session(payload: PracticeSessionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_id = current_user.id

    # Get active window
    window = MockOAAgent.get_or_create_active_window(db, payload.company, payload.role)

    session = PracticeAgent.get_or_create_practice_session(
        db=db,
        user_id=user_id,
        company=payload.company,
        role=payload.role,
        time_window_id=window.id,
        selected_topics=payload.selected_topics,
        proficiency_vector=payload.proficiency_vector,
        total_questions=payload.total_questions,
        allocation_mode=payload.allocation_mode,
        question_bank_level=payload.question_bank_level,
        role_profile_id=payload.role_profile_id
    )

    # Fetch questions
    questions = db.query(QuestionBank).filter(QuestionBank.id.in_(session.question_ids)).all()
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

    return {
        "id": session.id,
        "practice_generation_key": session.practice_generation_key,
        "company": session.company,
        "role": session.role,
        "selected_topics": session.selected_topics_json,
        "total_questions": len(q_outs),
        "questions": q_outs,
        "allocation_mode": session.allocation_mode
    }

@router.get("/sessions/{id}")
def get_practice_session(id: str, db: Session = Depends(get_db)):
    session = db.query(PracticeSession).filter(PracticeSession.id == id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")

    questions = db.query(QuestionBank).filter(QuestionBank.id.in_(session.question_ids)).all()
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

    return {
        "id": session.id,
        "practice_generation_key": session.practice_generation_key,
        "company": session.company,
        "role": session.role,
        "selected_topics": session.selected_topics_json,
        "total_questions": len(q_outs),
        "questions": q_outs,
        "allocation_mode": session.allocation_mode
    }

@router.post("/questions/{id}/check-answer", response_model=CheckAnswerResponse)
def check_answer(id: str, payload: CheckAnswerRequest, db: Session = Depends(get_db)):
    q = db.query(QuestionBank).filter(QuestionBank.id == id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    q_data = {
        "id": q.id,
        "question_type": q.question_type,
        "solution": q.solution,
        "approach": q.approach,
        "test_cases": q.test_cases_json,
        "prompt": q.prompt
    }

    eval_result = EvaluatorRegistry.evaluate(q.question_type, payload.answer, q_data)

    return CheckAnswerResponse(
        question_id=q.id,
        is_correct=eval_result.get("is_correct", False),
        score_fraction=eval_result.get("score_fraction", 0.0),
        feedback=eval_result.get("feedback", ""),
        test_case_results=eval_result.get("test_case_results"),
        optimal_complexity=eval_result.get("optimal_complexity")
    )

@router.get("/questions/{id}/hint", response_model=HintResponse)
def get_hint(id: str, db: Session = Depends(get_db)):
    q = db.query(QuestionBank).filter(QuestionBank.id == id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return HintResponse(
        question_id=q.id,
        hint=q.hint or "Focus on identifying invariants and decomposing the problem into smaller subproblems."
    )

@router.get("/questions/{id}/approach", response_model=ApproachResponse)
def get_approach(id: str, db: Session = Depends(get_db)):
    q = db.query(QuestionBank).filter(QuestionBank.id == id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return ApproachResponse(
        question_id=q.id,
        approach=q.approach or "Consider dynamic programming or greedy two-pointer invariants."
    )

@router.get("/questions/{id}/solution", response_model=SolutionResponse)
def get_solution(id: str, db: Session = Depends(get_db)):
    q = db.query(QuestionBank).filter(QuestionBank.id == id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return SolutionResponse(
        question_id=q.id,
        solution=q.solution or "",
        explanation=q.approach or ""
    )
