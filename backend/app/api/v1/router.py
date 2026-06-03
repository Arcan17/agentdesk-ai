"""Aggregates all v1 routers. Domain routers are added in later phases."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, documents, health, tickets, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tickets.router)
api_router.include_router(documents.router)
