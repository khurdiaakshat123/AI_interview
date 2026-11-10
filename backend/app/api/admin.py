import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.app.database import get_db
from backend.app.models.models import QuestionBank, User
from backend.app.schemas.schemas import ReviewQueueItem, ReviewDecisionRequest
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/admin", tags=["Admin & Question Review Queue"])

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Enforces authentication and admin role permissions on all administrative endpoints.
    Rejects unauthenticated requests with 401 and unauthorized non-admin users with 403.
    """
    admin_emails = [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "admin@intervyn.ai").split(",") if e.strip()]
    user_email = (current_user.email or "").strip().lower()
    is_admin = user_email in admin_emails or getattr(current_user, "is_admin", False)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrative privileges required to access review queue"
        )
    return current_user

@router.get("/review-queue", response_model=List[ReviewQueueItem])
def get_review_queue(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    questions = db.query(QuestionBank).order_by(QuestionBank.created_at.desc()).all()
    results = []
    for q in questions:
        results.append(ReviewQueueItem(
            id=q.id,
            subject=q.subject,
            topic=q.topic,
            subtopic=q.subtopic,
            question_type=q.question_type,
            difficulty=q.difficulty,
            title=q.title,
            prompt=q.prompt,
            status=q.status,
            review_report=q.review_report_json or {},
            created_at=q.created_at
        ))
    return results

@router.post("/review-queue/{id}/approve")
def approve_question(id: str, payload: ReviewDecisionRequest = None, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    q = db.query(QuestionBank).filter(QuestionBank.id == id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    q.status = "PUBLISHED"
    db.commit()
    return {"message": "Question approved and published to Question Bank", "question_id": q.id}

@router.post("/review-queue/{id}/reject")
def reject_question(id: str, payload: ReviewDecisionRequest = None, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    q = db.query(QuestionBank).filter(QuestionBank.id == id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    q.status = "FAILED"
    db.commit()
    return {"message": "Question marked as failed and excluded from bank", "question_id": q.id}
