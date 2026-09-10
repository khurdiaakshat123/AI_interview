from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.app.database import get_db
from backend.app.models.models import QuestionBank
from backend.app.schemas.schemas import ReviewQueueItem, ReviewDecisionRequest

router = APIRouter(prefix="/api/admin", tags=["Admin & Question Review Queue"])

@router.get("/review-queue", response_model=List[ReviewQueueItem])
def get_review_queue(db: Session = Depends(get_db)):
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
def approve_question(id: str, payload: ReviewDecisionRequest = None, db: Session = Depends(get_db)):
    q = db.query(QuestionBank).filter(QuestionBank.id == id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    q.status = "PUBLISHED"
    db.commit()
    return {"message": "Question approved and published to Question Bank", "question_id": q.id}

@router.post("/review-queue/{id}/reject")
def reject_question(id: str, payload: ReviewDecisionRequest = None, db: Session = Depends(get_db)):
    q = db.query(QuestionBank).filter(QuestionBank.id == id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    q.status = "FAILED"
    db.commit()
    return {"message": "Question marked as failed and excluded from bank", "question_id": q.id}
