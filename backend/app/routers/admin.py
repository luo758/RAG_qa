from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import UserAdminRead, UserRoleUpdate

router = APIRouter(prefix="/admin", tags=["管理员"])


def _require_manager(user: User) -> None:
    if user.role not in {"super_admin", "admin"}:
        raise HTTPException(status_code=403, detail="需要管理员权限")


@router.get("/users", response_model=list[UserAdminRead])
def list_users(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[User]:
    _require_manager(user)
    return list(db.scalars(select(User).order_by(User.role, User.username)).all())


@router.patch("/users/{user_id}/role", response_model=UserAdminRead)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if user.role != "super_admin":
        raise HTTPException(status_code=403, detail="只有超级管理员可以设置管理员")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.role == "super_admin":
        raise HTTPException(status_code=400, detail="不能修改超级管理员角色")
    target.role = payload.role
    db.commit()
    db.refresh(target)
    return target
