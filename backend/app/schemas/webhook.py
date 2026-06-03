"""Webhook configuration and delivery schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.webhook_delivery import DeliveryStatus


class WebhookConfig(BaseModel):
    url: HttpUrl
    secret: str = Field(min_length=16, max_length=255)
    is_active: bool = True


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    url: str
    is_active: bool
    created_at: datetime
    # secret intentionally not serialized


class WebhookDeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event: str
    status: DeliveryStatus
    attempts: int
    last_status_code: int | None
    last_error: str | None
    created_at: datetime
