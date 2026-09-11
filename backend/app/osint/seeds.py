"""Default OSINT source registry (gate §30-§36, §47, §405).

These rows are CONFIGURATION for real public sources — never fabricated articles.
Seeding them makes the source registry immediately usable; collection itself only
ever writes records fetched from the live external source.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.osint import (
    AUTHORITY_OFFICIAL,
    AUTHORITY_PUBLIC_NEWS,
    HEALTH_ACTIVE,
    OsintSource,
)

logger = logging.getLogger("clean_sport.osint")

DEFAULT_OSINT_SOURCES: list[dict] = [
    {
        "source_id": "gdelt-global",
        "name": "GDELT Global News (anti-doping)",
        "connector_type": "gdelt",
        "url": "https://api.gdeltproject.org/api/v2/doc/doc",
        "authority": AUTHORITY_PUBLIC_NEWS,
        "jurisdiction": "GLOBAL",
        "poll_frequency_min": 60,
        "rate_limit_per_min": 4,
        "extra_config": {
            "base_query": "anti-doping OR doping OR performance-enhancing drugs",
            "probe_query": "anti-doping",
        },
    },
    {
        "source_id": "gdelt-official",
        "name": "GDELT Official anti-doping authorities",
        "connector_type": "gdelt",
        "url": "https://api.gdeltproject.org/api/v2/doc/doc",
        "authority": AUTHORITY_OFFICIAL,
        "jurisdiction": "GLOBAL",
        "poll_frequency_min": 60,
        "rate_limit_per_min": 4,
        "extra_config": {
            "base_query": (
                "(anti-doping OR doping) AND (domain:wada-ama.org OR domain:ita.sport "
                "OR domain:nadaindia.org OR domain:ndtl.nic.in)"
            ),
            "probe_query": "anti-doping domain:wada-ama.org",
        },
    },
    {
        "source_id": "wada-news-rss",
        "name": "WADA News (official RSS)",
        "connector_type": "rss",
        "url": "https://www.wada-ama.org/en/rss.xml",
        "authority": AUTHORITY_OFFICIAL,
        "jurisdiction": "GLOBAL",
        "poll_frequency_min": 120,
        "rate_limit_per_min": 4,
    },
    {
        "source_id": "wada-news-releases",
        "name": "WADA News & Releases (official page)",
        "connector_type": "web_doc",
        "url": "https://www.wada-ama.org/en/media/news/releases",
        "authority": AUTHORITY_OFFICIAL,
        "jurisdiction": "GLOBAL",
        "poll_frequency_min": 720,
        "rate_limit_per_min": 4,
    },
    {
        "source_id": "nadaindia-site",
        "name": "NADA India public notices",
        "connector_type": "web_doc",
        "url": "https://www.nadaindia.org/",
        "authority": AUTHORITY_OFFICIAL,
        "jurisdiction": "INDIA",
        "poll_frequency_min": 1440,
        "rate_limit_per_min": 2,
        # Disabled until an operator confirms a stable public notices URL.
        "enabled": False,
    },
]


def seed_default_osint_sources(db: Session) -> None:
    """Idempotently create the default source registry rows."""
    created = 0
    for cfg in DEFAULT_OSINT_SOURCES:
        existing = db.scalar(
            select(OsintSource).where(OsintSource.source_id == cfg["source_id"])
        )
        if existing is not None:
            continue
        row = OsintSource(
            source_id=cfg["source_id"],
            name=cfg["name"],
            connector_type=cfg["connector_type"],
            url=cfg["url"],
            authority=cfg["authority"],
            jurisdiction=cfg.get("jurisdiction"),
            enabled=cfg.get("enabled", True),
            poll_frequency_min=cfg.get("poll_frequency_min"),
            rate_limit_per_min=cfg.get("rate_limit_per_min", 5),
            health=HEALTH_ACTIVE,
            consecutive_failures=0,
            extra_config=cfg.get("extra_config"),
            created_at=datetime.now(timezone.utc),
        )
        db.add(row)
        created += 1
    if created:
        db.commit()
        logger.info("Seeded %d default OSINT sources (configuration only)", created)