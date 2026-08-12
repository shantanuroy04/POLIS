"""Configuration guardrails — Implementation Plan task 1.9."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.config import Settings


def _settings(**overrides) -> Settings:
    base = {
        "polis_env": "test",
        "jwt_secret": "test-secret-at-least-32-characters-long",
        "_env_file": None,
    }
    return Settings(**{**base, **overrides})


def test_cors_origins_parsed_as_list():
    s = _settings(cors_allowed_origins="http://a.test, http://b.test")
    assert s.cors_origins == ["http://a.test", "http://b.test"]


def test_poll_interval_above_latency_budget_is_rejected():
    """PRD §11.1 — stage A must be <=10 min or NFR-1.5a is unmet.

    This is the guardrail that makes the latency budget enforceable rather than
    aspirational: a well-meaning "let's poll less often to save quota" change
    fails at startup instead of silently missing the NFR.
    """
    with pytest.raises(ValidationError):
        _settings(ingest_interval_minutes=15)


def test_poll_interval_at_budget_limit_is_accepted():
    assert _settings(ingest_interval_minutes=10).ingest_interval_minutes == 10


def test_production_rejects_debug_mode():
    with pytest.raises(RuntimeError, match="POLIS_DEBUG"):
        _settings(polis_env="demo", polis_debug=True).assert_production_safe()


def test_production_rejects_short_jwt_secret():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _settings(polis_env="demo", jwt_secret="tooshort").assert_production_safe()


def test_production_rejects_cors_wildcard():
    with pytest.raises(RuntimeError, match="CORS"):
        _settings(polis_env="demo", cors_allowed_origins="*").assert_production_safe()


def test_local_skips_production_checks():
    """Local development must not require a 32-char secret to start."""
    _settings(polis_env="local", polis_debug=True, jwt_secret="x").assert_production_safe()


def test_secrets_are_not_exposed_by_repr():
    """SEC-20 — a stray log/print of settings must not leak credentials."""
    s = _settings(jwt_secret="super-secret-value-that-must-not-leak-anywhere")
    assert "super-secret-value" not in repr(s)
    assert "super-secret-value" not in str(s)
