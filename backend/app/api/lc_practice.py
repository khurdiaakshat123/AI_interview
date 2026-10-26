from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from backend.app.database import get_db
from backend.app.models.models import User
from backend.app.api.deps import get_current_user
from backend.app.engines.lc_service import LCQuestionService

router = APIRouter(prefix="/api/practice/lc", tags=["LeetCode Practice Bank"])

class CodeExecutionPayload(BaseModel):
    code: str
    language: str = "cpp"
    custom_input: Optional[str] = None

@router.get("/questions")
def list_questions(
    category: str = Query("all", description="Top category: all | dsa | database"),
    subcategory: Optional[str] = Query(None, description="Topic/subcategory slug"),
    difficulty: str = Query("all", description="Difficulty: all | Easy | Medium | Hard"),
    status: str = Query("all", description="Status: all | solved | attempted | todo"),
    search: Optional[str] = Query(None, description="Search term for title, # or tag"),
    my_list_only: bool = Query(False, description="Filter by starred / My List"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    sort_by: str = Query("id", description="Sort by: id | title | difficulty"),
    order: str = Query("asc", description="Sort order: asc | desc"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    user_id = current_user.id if current_user else None
    return LCQuestionService.list_questions(
        db=db,
        user_id=user_id,
        category=category,
        subcategory=subcategory,
        difficulty=difficulty,
        status=status,
        search=search,
        my_list_only=my_list_only,
        page=page,
        limit=limit,
        sort_by=sort_by,
        order=order
    )

@router.get("/questions/{id_or_slug}")
def get_question(
    id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    user_id = current_user.id if current_user else None
    q = LCQuestionService.get_question(id_or_slug=id_or_slug, db=db, user_id=user_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q

@router.get("/analytics")
def get_analytics(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    user_id = current_user.id if current_user else None
    return LCQuestionService.get_analytics(db=db, user_id=user_id)

@router.post("/questions/{id_or_slug}/run")
def run_code(
    id_or_slug: str,
    payload: CodeExecutionPayload
):
    return LCQuestionService.run_code(
        question_id=id_or_slug,
        code=payload.code,
        language=payload.language
    )

@router.post("/questions/{id_or_slug}/debug")
def debug_code(
    id_or_slug: str,
    payload: CodeExecutionPayload
):
    return LCQuestionService.debug_code(
        question_id=id_or_slug,
        code=payload.code,
        language=payload.language,
        custom_input=payload.custom_input
    )

@router.post("/questions/{id_or_slug}/submit")
def submit_code(
    id_or_slug: str,
    payload: CodeExecutionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return LCQuestionService.submit_code(
        db=db,
        user_id=current_user.id,
        question_id=id_or_slug,
        code=payload.code,
        language=payload.language
    )

@router.post("/questions/{id_or_slug}/star")
def toggle_star(
    id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    is_starred = LCQuestionService.toggle_star(
        db=db,
        user_id=current_user.id,
        question_id=id_or_slug
    )
    return {"question_id": id_or_slug, "isStarred": is_starred}

@router.get("/questions/{id_or_slug}/submissions")
def get_submissions(
    id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = LCQuestionService.get_question(id_or_slug=id_or_slug, db=db, user_id=current_user.id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"submissions": q.get("prevSubmissions", [])}
