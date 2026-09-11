"""Role and permission constants.

These keys are the single source of truth for RBAC. The backend enforces them; the
frontend never supplies them (directive §36, §60).
"""
from __future__ import annotations


class Roles:
    ADMINISTRATOR = "ADMINISTRATOR"
    INVESTIGATOR = "INVESTIGATOR"
    INTELLIGENCE_ANALYST = "INTELLIGENCE_ANALYST"
    VIEWER = "VIEWER"

    ALL = [ADMINISTRATOR, INVESTIGATOR, INTELLIGENCE_ANALYST, VIEWER]


# Permission keys (capabilities). Role->permission mapping is seeded in the DB.
class Permissions:
    # Users & administration
    USERS_MANAGE = "users:manage"
    ROLES_MANAGE = "roles:manage"
    RULES_CONFIGURE = "rules:configure"
    MODELS_MANAGE = "models:manage"
    CONFIGURATION_MANAGE = "configuration:manage"
    AUDIT_READ = "audit:read"

    # Intelligence
    INTELLIGENCE_READ = "intelligence:read"
    INTELLIGENCE_CREATE = "intelligence:create"
    INTELLIGENCE_MODIFY = "intelligence:modify"
    SOURCES_MANAGE = "sources:manage"

    # Analytics
    ANALYSIS_RUN = "analysis:run"
    ANALYSIS_READ = "analysis:read"

    # Alerts
    ALERTS_READ = "alerts:read"
    ALERTS_REVIEW = "alerts:review"
    ALERTS_DISMISS = "alerts:dismiss"
    ALERTS_CONVERT = "alerts:convert"

    # Subjects
    ATHLETES_READ = "athletes:read"

    # Investigations
    INVESTIGATIONS_READ = "investigations:read"
    INVESTIGATIONS_CREATE = "investigations:create"
    INVESTIGATIONS_MODIFY = "investigations:modify"
    INVESTIGATIONS_ASSIGN = "investigations:assign"

    # Evidence
    EVIDENCE_CREATE = "evidence:create"
    EVIDENCE_MODIFY = "evidence:modify"

    # Reports
    REPORTS_GENERATE = "reports:generate"
    REPORTS_READ = "reports:read"

    # Batch data import
    IMPORTS_READ = "imports:read"
    IMPORTS_CREATE = "imports:create"
    IMPORTS_COMMIT = "imports:commit"

    # OSINT (real public/open-source collection)
    OSINT_READ = "osint:read"
    OSINT_COLLECT = "osint:collect"
    OSINT_ADMIN = "osint:admin"

    # Resources
    RESOURCES_READ = "resources:read"
