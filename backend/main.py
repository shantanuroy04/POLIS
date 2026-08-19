"""POLIS FastAPI application factory.

WEEK 1 SCOPE: app factory, CORS, security headers, and `/health` only. This
exists so Implementation Plan task 1.14 ("every member has started the API") is
verifiable on day one. Routers, auth, RBAC, and audit arrive in Phase 5
(Weeks 5-10) per TRD §11.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.config import Settings, get_settings
from backend.scheduler import create_scheduler

log = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """SEC-14, SEC-22, SEC-26. Applied from Week 1 so no route ever ships without them."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        return response


@contextlib.asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start the scheduler with the app, stop it with the app. ⟵ ADR-011

    The scheduler lives inside the API process because the free tier gives one
    always-on service and the pipeline is I/O-bound and idle most of every tick.
    `app.state.scheduler` is None when disabled, so a test client never starts a
    background thread it did not ask for.
    """
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler is not None:
        scheduler.start()
        log.info("scheduler started: pipeline_cycle every %s min", _interval_of(scheduler))
    try:
        yield
    finally:
        if scheduler is not None:
            # wait=False: a shutdown must not block on a running cycle. The
            # advisory lock is transaction-scoped, so an interrupted run releases
            # it rather than locking the pipeline out until a human notices.
            scheduler.shutdown(wait=False)
            log.info("scheduler stopped")


def _interval_of(scheduler) -> str:
    job = scheduler.get_job("pipeline_cycle")
    return str(getattr(job.trigger, "interval", "?")) if job else "?"


def create_app(settings: Settings | None = None, *, with_scheduler: bool = False) -> FastAPI:
    """Build the app.

    `with_scheduler` defaults to False so that importing the app — in a test, in
    Alembic, in a REPL — never starts polling the internet. The deployed entry
    point opts in explicitly.
    """
    settings = settings or get_settings()
    settings.assert_production_safe()

    app = FastAPI(
        title="POLIS API",
        version="0.1.0",
        # Auto-generated docs are a reconnaissance surface outside local (SEC-19).
        docs_url=f"{API_PREFIX}/docs" if settings.is_local else None,
        redoc_url=None,
        openapi_url=f"{API_PREFIX}/openapi.json" if settings.is_local else None,
        lifespan=_lifespan,
    )

    app.state.scheduler = create_scheduler(settings) if with_scheduler else None

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # explicit list, never "*" (SEC-15)
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get(f"{API_PREFIX}/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Public liveness probe. Deliberately leaks nothing internal (TRD §12.9).

        The detailed variant (`/health/detail`, admin-only) arrives in Phase 5.
        """
        return {"status": "ok"}

    return app


app = create_app()
