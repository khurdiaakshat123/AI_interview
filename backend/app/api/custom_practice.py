from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from backend.app.database import get_db
from backend.app.models.models import User
from backend.app.api.deps import get_current_user_optional
from backend.app.engines.custom_practice_service import CustomPracticeService

router = APIRouter(prefix="/api/practice/custom-session", tags=["Custom Practice & Assessment Sessions"])


class PrepareSessionPayload(BaseModel):
    title: Optional[str] = "Timed Practice Assessment"
    session_type: str = "hybrid"  # "mcq" | "dsa" | "hybrid"
    duration_minutes: int = 30
    marking_scheme: Optional[Dict[str, float]] = None
    sections: List[Dict[str, Any]] = []


class SubmitSessionPayload(BaseModel):
    mcq_answers: Dict[str, Optional[str]] = {}
    coding_submissions: Dict[str, Any] = {}
    time_spent_seconds: int = 0


@router.get("/metadata")
def get_session_metadata():
    """
    Returns available topics and question catalogs for building custom assessments.
    """
    try:
        return CustomPracticeService.get_metadata()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metadata: {str(e)}")


@router.post("/prepare")
def prepare_session(
    payload: PrepareSessionPayload,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Compiles a custom assessment with MCQ, DSA, or Hybrid sections,
    supporting topic-wise difficulty permutations and negative marking.
    """
    try:
        user_id = current_user.id if current_user else None
        return CustomPracticeService.prepare_session(
            payload=payload.model_dump(),
            db=db,
            creator_user_id=user_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to prepare session: {str(e)}")


@router.get("/{session_id}")
def get_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves a shared or prepared practice session by ID.
    Answers and solution keys are omitted for examinee integrity.
    """
    session_data = CustomPracticeService.get_session(session_id, db=db)
    if not session_data:
        raise HTTPException(status_code=404, detail=f"Practice session '{session_id}' not found.")
    return session_data


@router.post("/{session_id}/submit")
def submit_session(
    session_id: str,
    payload: SubmitSessionPayload,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Submits and grades candidate answers:
    - Calculates MCQ positive & negative scores (+1.0 / -0.25).
    - Evaluates DSA submissions and testcases.
    - Unlocks full review and detailed explanations.
    """
    try:
        user_id = current_user.id if current_user else None
        return CustomPracticeService.submit_session(
            session_id=session_id,
            submission_payload=payload.model_dump(),
            db=db,
            user_id=user_id
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to grade submission: {str(e)}")
