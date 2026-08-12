"""POLIS FastAPI application factory.

WEEK 1 SCOPE: app factory, CORS, security headers, and `/health` only. This
exists so Implementation Plan task 1.14 ("every member has started the API") is
verifiable on day one. Routers, auth, RBAC, and audit arrive in Phase 5
(Weeks 5-10) per TRD §11.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.config import Settings, get_settings

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


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.assert_production_safe()

    app = FastAPI(
        title="POLIS API",
        version="0.1.0",
        # Auto-generated docs are a reconnaissance surface outside local (SEC-19).
        docs_url=f"{API_PREFIX}/docs" if settings.is_local else None,
        redoc_url=None,
        openapi_url=f"{API_PREFIX}/openapi.json" if settings.is_local else None,
    )

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
