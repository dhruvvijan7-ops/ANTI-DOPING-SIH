"""Core logging configuration.

Never log passwords, tokens, secrets or confidential intelligence contents.
"""
from __future__ import annotations

import logging
import sys
import uuid

LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": (
                "%(asctime)s | %(levelname)s | %(name)s | "
                "req=%(request_id)s | %(message)s"
            ),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": sys.stdout,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
        "propagate": True,
    },
    "loggers": {
        "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "uvicorn.access": {"level": "WARNING", "propagate": False},
        "sqlalchemy.engine": {"level": "WARNING", "propagate": False},
        "clean_sport": {"level": "INFO", "handlers": ["console"], "propagate": False},
    },
}


def request_id_filter() -> str:
    """Generate a request correlation id."""
    return f"req_{uuid.uuid4().hex[:12]}"


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
