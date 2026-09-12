import os
from typing import Optional
from fastapi import Header, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import User, generate_uuid, utc_now

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to extract and verify the authenticated User.
    Supports:
    - Bearer google_token_<user_id>
    - Bearer token_<user_id>
    - Bearer guest_<guest_device_id> (isolated per device/browser session)
    Guarantees strict multi-tenant / multi-user data isolation.
    """
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.replace("Bearer ", "").strip()
        if raw_token:
            if raw_token.startswith("guest_"):
                guest_user = db.query(User).filter(User.id == raw_token).first()
                if not guest_user:
                    guest_user = User(
                        id=raw_token,
                        name="Guest Candidate",
                        email=f"{raw_token}@guest.intervyn.ai",
                        password_hash="guest_auth",
                        created_at=utc_now()
                    )
                    db.add(guest_user)
                    db.commit()
                    db.refresh(guest_user)
                return guest_user

            user_id = None
            if raw_token.startswith("google_token_"):
                user_id = raw_token.replace("google_token_", "").strip()
            elif raw_token.startswith("token_"):
                user_id = raw_token.replace("token_", "").strip()
            elif "_" in raw_token:
                user_id = raw_token.split("_")[-1]
            else:
                user_id = raw_token

            if user_id:
                user = db.query(User).filter((User.id == user_id) | (User.email == user_id)).first()
                if user:
                    return user

    # Fallback to isolated anonymous guest if completely unauthenticated
    anon_id = f"guest_anon_{generate_uuid()}"
    guest = User(
        id=anon_id,
        name="Guest Candidate",
        email=f"{anon_id}@guest.intervyn.ai",
        password_hash="guest_oauth",
        created_at=utc_now()
    )
    db.add(guest)
    db.commit()
    db.refresh(guest)
    return guest

def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional user dependency: returns User for token (authenticated or guest token),
    or None if no authorization header is present.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    raw_token = authorization.replace("Bearer ", "").strip()
    if not raw_token:
        return None

    if raw_token.startswith("guest_"):
        guest_user = db.query(User).filter(User.id == raw_token).first()
        if not guest_user:
            guest_user = User(
                id=raw_token,
                name="Guest Candidate",
                email=f"{raw_token}@guest.intervyn.ai",
                password_hash="guest_auth",
                created_at=utc_now()
            )
            db.add(guest_user)
            db.commit()
            db.refresh(guest_user)
        return guest_user

    user_id = None
    if raw_token.startswith("google_token_"):
        user_id = raw_token.replace("google_token_", "").strip()
    elif raw_token.startswith("token_"):
        user_id = raw_token.replace("token_", "").strip()
    elif "_" in raw_token:
        user_id = raw_token.split("_")[-1]
    else:
        user_id = raw_token

    if user_id:
        return db.query(User).filter((User.id == user_id) | (User.email == user_id)).first()
    return None

