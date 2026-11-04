from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from backend.app.database import get_db
from backend.app.models.models import User
from backend.app.api.deps import get_current_user, get_current_user_optional
from backend.app.engines.mcq_service import MCQQuestionService
from backend.app.engines.mcq_topics import validate_all_subparts

router = APIRouter(prefix="/api/practice/mcq", tags=["MCQ Practice Bank"])

class SubmitAnswerPayload(BaseModel):
    selected_option: str

class SaveNotesPayload(BaseModel):
    notes: str

class GenerateQuizPayload(BaseModel):
    topics: Optional[List[str]] = None
    difficulties: Optional[List[str]] = None
    count: int = 10
    mode: str = "random"

@router.get("/topics")
def get_mcq_topics(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Returns the 9 broad topics with aggregated question counts,
    difficulty distribution, and candidate mastery progress.
    """
    user_id = current_user.id if current_user else None
    return MCQQuestionService.get_topics(db=db, user_id=user_id)

@router.get("/questions")
def list_mcq_questions(
    topic: str = Query("all", description="Single broad topic: all | os | dbms | computer-networks | oop | dsa | pseudocode | applied-systems | data-science | aptitude"),
    topics: Optional[str] = Query(None, description="Comma-separated broad topics: e.g. 'os,dbms'"),
    difficulty: str = Query("all", description="Difficulty: all | Easy | Medium | Hard"),
    status: str = Query("all", description="Status: all | solved | attempted | todo"),
    search: Optional[str] = Query(None, description="Search query across question prompt, code, options, topics"),
    has_code: Optional[bool] = Query(None, description="Filter questions that include code snippets"),
    starred_only: bool = Query(False, description="Filter only bookmarked / starred questions"),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    sort_by: str = Query("id", description="Sort by: id | difficulty | random"),
    order: str = Query("asc", description="Sort order: asc | desc"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Retrieves paginated MCQ questions with comprehensive broad-topic filtering,
    multi-select, difficulty filters, search, and user state.
    """
    user_id = current_user.id if current_user else None
    return MCQQuestionService.list_questions(
        db=db,
        user_id=user_id,
        topic=topic,
        topics=topics,
        difficulty=difficulty,
        status=status,
        search=search,
        has_code=has_code,
        starred_only=starred_only,
        page=page,
        limit=limit,
        sort_by=sort_by,
        order=order
    )

@router.get("/questions/{question_id}")
def get_mcq_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Retrieves full details for a single MCQ question.
    """
    user_id = current_user.id if current_user else None
    q = MCQQuestionService.get_question(question_id=question_id, db=db, user_id=user_id)
    if not q:
        raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found")
    return q

@router.post("/questions/{question_id}/submit")
def submit_mcq_answer(
    question_id: str,
    payload: SubmitAnswerPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits an answer option ('A', 'B', 'C', 'D') for evaluation, returns immediate
    explanation & validation, and updates candidate progress.
    """
    try:
        return MCQQuestionService.submit_answer(
            question_id=question_id,
            selected_option=payload.selected_option,
            db=db,
            user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/questions/{question_id}/star")
def toggle_mcq_star(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Toggles bookmark / star status for a question.
    """
    try:
        return MCQQuestionService.toggle_star(
            question_id=question_id,
            db=db,
            user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/questions/{question_id}/notes")
def save_mcq_notes(
    question_id: str,
    payload: SaveNotesPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Saves candidate notes on a question.
    """
    try:
        return MCQQuestionService.save_notes(
            question_id=question_id,
            notes=payload.notes,
            db=db,
            user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/quiz/generate")
def generate_mcq_quiz(
    payload: GenerateQuizPayload,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Generates a randomized or targeted practice quiz across selected broad topics.
    """
    user_id = current_user.id if current_user else None
    return MCQQuestionService.generate_quiz(
        topics=payload.topics,
        difficulties=payload.difficulties,
        count=payload.count,
        mode=payload.mode,
        db=db,
        user_id=user_id
    )

@router.get("/analytics")
def get_mcq_analytics(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Returns candidate analytics across broad topics, difficulty breakdowns, and accuracy.
    """
    user_id = current_user.id if current_user else None
    return MCQQuestionService.get_analytics(db=db, user_id=user_id)

@router.get("/validation")
def get_mapping_validation():
    """
    Exposes mapping validation report verifying that all 39 subparts and 1,500 questions
    map to exactly one broad topic with zero omissions.
    """
    MCQQuestionService._ensure_loaded()
    discovered = list({q["subpart_id"] for q in MCQQuestionService._questions_list})
    return validate_all_subparts(discovered)
