from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import User, generate_uuid, utc_now
from backend.app.schemas.schemas import UserSignup, UserLogin, UserOut, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/signup", response_model=TokenResponse)
def signup(payload: UserSignup, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=generate_uuid(),
        name=payload.name,
        email=payload.email,
        password_hash="hashed_" + payload.password,
        created_at=utc_now()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=f"mock_token_{user.id}",
        user=UserOut.model_validate(user)
    )

@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # For demo purposes, auto-create if not found
        user = User(
            id=generate_uuid(),
            name=payload.email.split("@")[0].title(),
            email=payload.email,
            password_hash="hashed_" + payload.password,
            created_at=utc_now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return TokenResponse(
        access_token=f"mock_token_{user.id}",
        user=UserOut.model_validate(user)
    )

@router.get("/me", response_model=UserOut)
def get_me(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        user = User(
            id=generate_uuid(),
            name="Alex Mercer",
            email="candidate@intervyn.ai",
            password_hash="hashed",
            created_at=utc_now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return UserOut.model_validate(user)
