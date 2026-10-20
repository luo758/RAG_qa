from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..captcha import captcha_image_data, create_captcha, verify_captcha
from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import (
    CaptchaResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["认证"])


@router.get("/captcha", response_model=CaptchaResponse)
def get_captcha(db: Session = Depends(get_db)) -> CaptchaResponse:
    captcha, code = create_captcha(db)
    return CaptchaResponse(
        captcha_id=captcha.id,
        image_data=captcha_image_data(code),
        expires_in=settings.captcha_expire_seconds,
        debug_code=code if settings.is_test else None,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的密码不一致")
    if not verify_captcha(db, payload.captcha_id, payload.captcha_code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    exists = db.scalar(select(User).where(User.username == payload.username))
    if exists:
        raise HTTPException(status_code=409, detail="用户名已存在")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.username)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if not verify_captcha(db, payload.captcha_id, payload.captcha_code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    token = create_access_token(user.id, user.username)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)
