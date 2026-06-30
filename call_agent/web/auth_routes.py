"""Auth endpoints: signup, login, and a token-protected `me`."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from call_agent.database import get_db
from call_agent.security import (
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)
from db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    name: str | None = None


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None = None


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/signup", response_model=TokenResponse)
def signup(body: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = _normalize_email(body.email)
    user = User(email=email, password_hash=hash_password(body.password), name=body.name)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    db.refresh(user)
    return TokenResponse(token=create_token(user.id, user.email))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = _normalize_email(body.email)
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return TokenResponse(token=create_token(user.id, user.email))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=current_user.id, email=current_user.email, name=current_user.name)
