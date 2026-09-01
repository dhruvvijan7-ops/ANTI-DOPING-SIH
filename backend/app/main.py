"""FastAPI application entry point."""
from __future__ import annotations

import logging.config as _logging_config
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import add_request_id_middleware, register_exception_handlers
from app.core.logging import LOGGING_CONFIG, get_logger
from app.db.seed import run_seed
from app.db.session import SessionLocal
from app.models.identity import User

_logging_config.dictConfig(LOGGING_CONFIG)
logger = get_logger("clean_sport")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s v%s (env=%s)",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )
    # Seed development RBAC + users if configured. Fail fast on seed errors so dev
    # never runs without a usable identity baseline.
    if settings.deploy_initial_users and not settings.is_production:
        db = SessionLocal()
        try:
            run_seed(db)
            user_count = db.scalar(select(func.count(User.id)))
            logger.info("DB seeded and ready; user count=%s", user_count)
        finally:
            db.close()
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    add_request_id_middleware(app)
    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
