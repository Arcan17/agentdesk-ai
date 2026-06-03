"""User management endpoints (admin only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import Role, User
from app.rbac import require_role
from app.schemas.user import UserCreate, UserOut
from app.services import user_service
from app.services.auth_service import ConflictError

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin)),
) -> list[User]:
    return await user_service.list_users(db, organization_id=current.organization_id)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin)),
) -> User:
    try:
        return await user_service.create_user(
            db,
            organization_id=current.organization_id,
            email=body.email,
            password=body.password,
            role=body.role,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
