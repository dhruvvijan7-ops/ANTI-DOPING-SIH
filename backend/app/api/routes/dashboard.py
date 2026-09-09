"""Dashboard API: computed read-only summary of platform activity over real data."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_any_permission
from app.db.session import get_db
from app.security.rbac import Permissions
from app.services.domain_reads import dashboard_summary

router = APIRouter(tags=["dashboard"])

# Any viewer/investigator/analyst/admin with at least one read capability can open
# the dashboard; the summary itself only contains data those roles may already read.
_DASHBOARD_READ = [
    Permissions.ALERTS_READ,
    Permissions.INVESTIGATIONS_READ,
    Permissions.INTELLIGENCE_READ,
    Permissions.ANALYSIS_READ,
    Permissions.ATHLETES_READ,
]


@router.get(
    "/dashboard",
    dependencies=[Depends(require_any_permission(_DASHBOARD_READ))],
    summary="Platform dashboard summary",
)
def get_dashboard(db: Session = Depends(get_db)) -> dict:
    return dashboard_summary(db)