import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import verify_password, create_access_token
from app.core.admin_dependencies import get_current_admin
from app.crud.admin import (
    get_admin_by_email,
    get_all_users,
    get_user_by_id_admin,
    get_global_stats,
    get_user_stats,
    get_all_flags,
    mark_flag_reviewed,
    ban_user,
    unban_user,
)
from app.schemas.admin import (
    AdminLoginRequest,
    AdminTokenResponse,
    GlobalStats,
    UserCard,
    UserDetail,
    UserStats,
    FlagRead,
)
from app.models.admin import Admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/login", response_model=AdminTokenResponse)
def admin_login(payload: AdminLoginRequest, db: Session = Depends(get_db)):
    admin = get_admin_by_email(db, payload.email)
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": str(admin.id), "role": "admin"})
    return AdminTokenResponse(access_token=token)


@router.get("/dashboard", response_model=GlobalStats)
def dashboard(
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    return get_global_stats(db)


@router.get("/users", response_model=list[UserCard])
def list_users(
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    return get_all_users(db)


@router.get("/users/{user_id}", response_model=UserDetail)
def get_user_detail(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    user = get_user_by_id_admin(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    stats = get_user_stats(db, user_id)
    return UserDetail(
        user=UserCard.model_validate(user),
        stats=UserStats(**stats),
    )


@router.post("/users/{user_id}/ban", response_model=UserCard)
def ban(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    user = ban_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users/{user_id}/unban", response_model=UserCard)
def unban(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    user = unban_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/flags", response_model=list[FlagRead])
def list_flags(
    reviewed: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    return get_all_flags(db, reviewed=reviewed)


@router.patch("/flags/{flag_id}/review", response_model=FlagRead)
def review_flag(
    flag_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    flag = mark_flag_reviewed(db, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    return flag