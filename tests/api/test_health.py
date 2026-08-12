"""API smoke tests — Implementation Plan task 1.9. Full endpoint suite lands in Phase 5."""

from __future__ import annotations


def test_health_returns_ok(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_leaks_nothing_internal(client):
    """TRD §12.9 — the public probe must not hand a caller a reconnaissance surface."""
    body = client.get("/api/v1/health").json()
    assert set(body) == {"status"}


def test_security_headers_present(client):
    """SEC-14, SEC-26 — applied from Week 1 so no route ever ships without them."""
    h = client.get("/api/v1/health").headers
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in h["Content-Security-Policy"]


def test_openapi_disabled_outside_local(client):
    """SEC-19 — the test app runs with POLIS_ENV=test, so docs must be off."""
    assert client.get("/api/v1/docs").status_code == 404
    assert client.get("/api/v1/openapi.json").status_code == 404
