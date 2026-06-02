"""Aggregates all v1 routers. Domain routers are added in later phases."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router)
