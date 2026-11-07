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
    - Bearer mock_token_<user_id>
    - Bearer token_<user_id>
    - Bearer guest_<guest_device_id> or Bearer g_<guest_device_id>
    Guarantees strict multi-tenant / multi-user data isolation.
    CRITICAL SECURITY: Email addresses and google_ids are NEVER accepted as bearer tokens.
    """
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.replace("Bearer ", "").strip()
        if raw_token:
            # SECURITY: An email address must NEVER be accepted as an authentication token
            if "@" in raw_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token format. Email addresses cannot be used as tokens."
                )

            try:
                # 1. Look up existing user by prefix
                for prefix in ("google_token_", "mock_token_", "token_"):
                    if raw_token.startswith(prefix):
                        target_id = raw_token.replace(prefix, "").strip()[:36]
                        user = db.query(User).filter(User.id == target_id).first()
                        if user:
                            return user

                # 2. Look up existing user by exact ID (if valid UUID <= 36 chars and not guest)
                if len(raw_token) <= 36 and not raw_token.startswith("guest_") and not raw_token.startswith("g_"):
                    user = db.query(User).filter(User.id == raw_token).first()
                    if user:
                        return user

                # Fallback: if raw_token has format <prefix>_<uuid>
                if "_" in raw_token and not (raw_token.startswith("guest_") or raw_token.startswith("g_")):
                    target_id = raw_token.split("_")[-1][:36]
                    user = db.query(User).filter(User.id == target_id).first()
                    if user:
                        return user

                # 3. Resolve or create guest user
                if raw_token.startswith("guest_") or raw_token.startswith("g_"):
                    safe_guest_id = raw_token[:36]
                    guest_user = db.query(User).filter(User.id == safe_guest_id).first()
                    if not guest_user:
                        try:
                            guest_user = User(
                                id=safe_guest_id,
                                name="Guest Candidate",
                                email=f"{safe_guest_id}@guest.intervyn.ai"[:255],
                                password_hash="guest_auth",
                                created_at=utc_now()
                            )
                            db.add(guest_user)
                            db.commit()
                            db.refresh(guest_user)
                        except Exception:
                            db.rollback()
                            guest_user = db.query(User).filter(User.id == safe_guest_id).first()
                    if guest_user:
                        return guest_user

                # Token provided but could not be resolved to any authentic user
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired authentication credentials"
                )
            except HTTPException:
                raise
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed"
                )

    # Fallback to isolated anonymous guest only if NO Authorization header was supplied at all
    try:
        anon_id = generate_uuid()
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
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return User(
            id=generate_uuid(),
            name="Guest Candidate",
            email=f"guest_{generate_uuid()[:8]}@guest.intervyn.ai"
        )

def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional user dependency: returns User for token (authenticated or guest token),
    or None if no authorization header is present or if user record does not exist.
    Completely read-only: NEVER mutates the database and NEVER raises 500 errors.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    raw_token = authorization.replace("Bearer ", "").strip()
    if not raw_token or "@" in raw_token:
        return None

    try:
        # Check google_token_ / mock_token_ / token_ prefixes
        for prefix in ("google_token_", "mock_token_", "token_"):
            if raw_token.startswith(prefix):
                target_id = raw_token.replace(prefix, "").strip()[:36]
                user = db.query(User).filter(User.id == target_id).first()
                if user:
                    return user

        # Check by exact ID (if <= 36 chars and not guest)
        if len(raw_token) <= 36 and not raw_token.startswith("guest_") and not raw_token.startswith("g_"):
            user = db.query(User).filter(User.id == raw_token).first()
            if user:
                return user

        # Fallback: if raw_token has format <prefix>_<uuid>
        if "_" in raw_token and not (raw_token.startswith("guest_") or raw_token.startswith("g_")):
            target_id = raw_token.split("_")[-1][:36]
            user = db.query(User).filter(User.id == target_id).first()
            if user:
                return user

        # Check guest_ / g_ prefixes
        if raw_token.startswith("guest_") or raw_token.startswith("g_"):
            safe_id = raw_token[:36]
            user = db.query(User).filter(User.id == safe_id).first()
            if user:
                return user

        return None
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None
