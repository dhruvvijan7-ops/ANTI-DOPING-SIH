"""API v1 router assembly."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import alerts, analysis, auth, health, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="")
api_router.include_router(users.router, prefix="")
api_router.include_router(analysis.router, prefix="")
api_router.include_router(alerts.router, prefix="")
