"""User management within an organization (admin-only callers)."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import Role, User
from app.services.auth_service import ConflictError


async def list_users(db: AsyncSession, *, organization_id: uuid.UUID) -> list[User]:
    result = await db.scalars(
        select(User).where(User.organization_id == organization_id).order_by(User.created_at)
    )
    return list(result)


async def create_user(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    email: str,
    password: str,
    role: Role,
) -> User:
    existing = await db.scalar(
        select(User).where(
            User.organization_id == organization_id,
            func.lower(User.email) == email.lower(),
        )
    )
    if existing is not None:
        raise ConflictError("A user with this email already exists in the organization")

    user = User(
        organization_id=organization_id,
        email=email.lower(),
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
