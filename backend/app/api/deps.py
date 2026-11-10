import os
import jwt
from typing import Optional
from fastapi import Header, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import User, RevokedToken, generate_uuid, utc_now

JWT_SECRET = os.environ.get("JWT_SECRET", "intervyn_jwt_secret_key_prod_auth_2026_super_secure_32b")
JWT_ALGORITHM = "HS256"

def get_current_user(
    authorization: Optional[str] = Header(None),
    x_expected_user_id: Optional[str] = Header(None, alias="X-Expected-User-Id"),
    x_session_generation: Optional[str] = Header(None, alias="X-Session-Generation"),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to extract and verify the authenticated User via signed JWT.
    Guarantees strict multi-tenant authentication, token revocation enforcement,
    and cross-tab session generation verification.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required"
        )

    raw_token = authorization.replace("Bearer ", "").strip()
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing"
        )

    if "@" in raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token format. Email addresses cannot be used as tokens."
        )

    # 1. Attempt to decode and verify signed JWT
    try:
        payload = jwt.decode(raw_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        jti = payload.get("jti")
        session_gen = payload.get("session_gen")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Check explicit token revocation list
        if jti:
            is_revoked = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
            if is_revoked:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication token has been revoked. Please log in again."
                )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account associated with this token does not exist"
            )

        # Enforce session generation validity (prevent use of tokens from prior login sessions)
        if user.session_generation and session_gen and user.session_generation != session_gen:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication session has expired or been terminated. Please log in again."
            )

        # Validate client-provided precondition headers if passed
        if x_expected_user_id and x_expected_user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account context mismatch: Current authenticated user does not match the expected user."
            )

        if x_session_generation and session_gen and x_session_generation != session_gen:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session generation mismatch: Operation belongs to a stale session."
            )

        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please log in again."
        )
    except jwt.PyJWTError:
        pass

    # 2. Strict rejection: Raw user IDs, mock_token_*, google_token_*, or unverified strings
    # MUST NEVER authenticate as legitimate accounts.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or unverified authentication credentials"
    )

def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    x_expected_user_id: Optional[str] = Header(None, alias="X-Expected-User-Id"),
    x_session_generation: Optional[str] = Header(None, alias="X-Session-Generation"),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional user dependency: returns authenticated User if a valid, unrevoked signed JWT
    is present and session matches. Returns None if credentials missing or revoked.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    raw_token = authorization.replace("Bearer ", "").strip()
    if not raw_token or "@" in raw_token:
        return None

    try:
        payload = jwt.decode(raw_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        jti = payload.get("jti")
        session_gen = payload.get("session_gen")

        if not user_id:
            return None

        # Check explicit token revocation
        if jti:
            is_revoked = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
            if is_revoked:
                return None

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        # Enforce session generation check
        if user.session_generation and session_gen and user.session_generation != session_gen:
            return None

        # Check preconditions if provided
        if x_expected_user_id and x_expected_user_id != user.id:
            return None
        if x_session_generation and session_gen and x_session_generation != session_gen:
            return None

        return user
    except Exception:
        return None
