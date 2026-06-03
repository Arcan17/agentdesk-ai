"""Admin metrics endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import Role, User
from app.rbac import require_role
from app.schemas.metrics import Metrics
from app.services import metrics_service

router = APIRouter(prefix="/admin", tags=["metrics"])


@router.get("/metrics", response_model=Metrics)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin)),
) -> Metrics:
    return await metrics_service.compute(db, organization_id=current.organization_id)
