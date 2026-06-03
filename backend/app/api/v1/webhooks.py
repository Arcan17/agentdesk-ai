"""Webhook configuration and delivery inspection (admin only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import Role, User
from app.models.webhook_delivery import WebhookDelivery
from app.rbac import require_role
from app.schemas.webhook import WebhookConfig, WebhookDeliveryOut, WebhookOut
from app.services import webhook_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("", response_model=WebhookOut | None)
async def get_webhook(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin)),
) -> WebhookOut | None:
    webhook = await webhook_service.get_config(db, organization_id=current.organization_id)
    return WebhookOut.model_validate(webhook) if webhook else None


@router.put("", response_model=WebhookOut)
async def put_webhook(
    body: WebhookConfig,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin)),
) -> WebhookOut:
    webhook = await webhook_service.upsert_config(
        db,
        organization_id=current.organization_id,
        url=str(body.url),
        secret=body.secret,
        is_active=body.is_active,
    )
    return WebhookOut.model_validate(webhook)


@router.get("/deliveries", response_model=list[WebhookDeliveryOut])
async def list_deliveries(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.admin)),
) -> list[WebhookDeliveryOut]:
    rows = await db.scalars(
        select(WebhookDelivery)
        .where(WebhookDelivery.organization_id == current.organization_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(100)
    )
    return [WebhookDeliveryOut.model_validate(r) for r in rows]
