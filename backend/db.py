"""Engine, sessions, and the advisory lock the scheduler depends on. ⟵ TRD §6.2, §10

One engine per process. The scheduler and the API share it, because TRD §4
deploys a single FastAPI process hosting both — two pools in one process would
double the connection count against a free-tier database for no benefit.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.config import get_settings

log = logging.getLogger(__name__)

# Stable, arbitrary. PostgreSQL advisory locks are keyed by integer, and every
# POLIS lock lives under this namespace so it cannot collide with anything else
# sharing the database.
ADVISORY_LOCK_NAMESPACE = 0x504F_4C49  # "POLI"

_JOB_LOCK_IDS = {
    "pipeline": 1,
    "retention": 2,
}


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        # SecretStr on purpose: the URL carries a password, and SEC-17 keeps it
        # out of logs and repr(). Unwrapped only here, at the point of use.
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,  # free-tier databases drop idle connections silently
        pool_size=5,
        max_overflow=5,
        future=True,
        echo=False,
    )


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Commit on success, roll back on any exception, always close.

    Used by the scheduler jobs. FastAPI routes get their session from a
    dependency instead, so that a request's transaction is tied to the request.
    """
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def with_job_lock(session: Session, job: str) -> bool:
    """Try to take the transaction-scoped advisory lock for `job`. ⟵ TRD §6.2

    Returns False rather than blocking when another run already holds it. That
    is the intended behaviour: `pipeline_cycle` runs every 10 minutes and a run
    that overlaps its predecessor should be skipped, not queued behind it — the
    next tick is 10 minutes away and the work is idempotent.

    `pg_try_advisory_xact_lock` releases at transaction end, including on crash.
    The session-scoped variant would survive a process kill and leave the
    pipeline permanently locked out with no way to notice.
    """
    if job not in _JOB_LOCK_IDS:
        raise ValueError(f"unknown job lock: {job}")

    acquired = session.execute(
        text("SELECT pg_try_advisory_xact_lock(:ns, :id)"),
        {"ns": ADVISORY_LOCK_NAMESPACE, "id": _JOB_LOCK_IDS[job]},
    ).scalar_one()

    if not acquired:
        log.warning("job lock %r is held by another run; skipping this tick", job)
    return bool(acquired)


def ping() -> bool:
    """Cheap liveness check for /health/detail."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 — health checks report, they do not raise
        log.exception("database ping failed")
        return False
