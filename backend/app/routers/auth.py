import hashlib
import logging
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.db.database import get_db
from app.models.models import PasswordResetToken, User
from app.schemas.user import PasswordResetConfirm, PasswordResetRequest, Token, UserCreate, UserOut
from app.services.email_service import send_password_reset_email

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)
RESET_REQUEST_MESSAGE = "If an active account uses that email, a password reset link will be sent."


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    email = data.email.lower().strip()

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # The very first user becomes admin, everyone after is a farmer
    role = "admin" if db.query(User).count() == 0 else "farmer"

    user = User(
        email=email,
        full_name=data.full_name.strip(),
        hashed_password=hash_password(data.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 form calls the email field "username"
    user = db.query(User).filter(User.email == form.username.lower().strip()).first()

    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    return Token(access_token=create_access_token(str(user.id)))


@router.post("/password-reset/request")
def request_password_reset(data: PasswordResetRequest, db: Session = Depends(get_db)):
    mail_configured = bool(settings.SMTP_HOST and settings.SMTP_FROM)
    if not mail_configured and not settings.PASSWORD_RESET_DEV_MODE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset is not configured. Set SMTP settings or enable local development mode.",
        )

    user = (
        db.query(User)
        .filter(User.email == str(data.email).lower().strip(), User.is_active.is_(True))
        .first()
    )
    if user is None:
        return {"message": RESET_REQUEST_MESSAGE}

    token = secrets.token_urlsafe(32)
    now = _utc_now_naive()
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).delete(synchronize_session=False)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_reset_token(token),
        expires_at=now + timedelta(minutes=30),
    )
    db.add(reset_token)
    db.commit()

    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?{urlencode({'token': token})}"
    if mail_configured:
        try:
            send_password_reset_email(user.email, reset_url)
        except (OSError, smtplib.SMTPException) as exc:
            logger.exception("Failed to send password reset email")
            db.delete(reset_token)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not send the reset email. Please try again later.",
            ) from exc
        return {"message": RESET_REQUEST_MESSAGE}

    logger.warning("Development password reset link for %s: %s", user.email, reset_url)
    return {"message": RESET_REQUEST_MESSAGE, "reset_url": reset_url}


@router.post("/password-reset/confirm")
def confirm_password_reset(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    now = _utc_now_naive()
    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == _hash_reset_token(data.token))
        .first()
    )
    if reset_token is None or reset_token.used_at is not None or reset_token.expires_at <= now:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")

    user = db.query(User).filter(User.id == reset_token.user_id, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")

    user.hashed_password = hash_password(data.password)
    reset_token.used_at = now
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.id != reset_token.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
    db.commit()
    return {"message": "Password updated. You can now log in with your new password."}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user