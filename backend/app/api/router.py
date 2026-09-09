"""API v1 router assembly."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    ai,
    alerts,
    analysis,
    auth,
    dashboard,
    health,
    intelligence,
    investigations,
    relationships,
    reports,
    subjects,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="")
api_router.include_router(users.router, prefix="")
api_router.include_router(analysis.router, prefix="")
api_router.include_router(alerts.router, prefix="")
api_router.include_router(investigations.router, prefix="")
api_router.include_router(reports.router, prefix="")
api_router.include_router(ai.router, prefix="")
api_router.include_router(dashboard.router, prefix="")
api_router.include_router(subjects.router, prefix="")
api_router.include_router(intelligence.router, prefix="")
api_router.include_router(relationships.router, prefix="")
