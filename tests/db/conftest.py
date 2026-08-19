"""Database fixtures. ⟵ DOC-005, DOC-016 §5

These tests need a real PostgreSQL. SQLite would be quicker and would test
nothing that matters here: the schema leans on JSONB, partial unique indexes,
regex CHECK constraints and advisory locks, none of which SQLite has. A green
suite against a database POLIS never runs on is worse than no suite.

Locally:

    docker run -d --name polis-db -e POSTGRES_PASSWORD=devonly \\
      -e POSTGRES_USER=polis -e POSTGRES_DB=polis -p 5432:5432 postgres:16

With no database reachable the tests **skip**, so `pytest` still runs on a
laptop with Docker off. CI runs a Postgres service container, so nothing is
skipped where it counts.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.models import Base

# A database of its own, never the development one. Sharing them meant a real
# ingest run left 115 rows behind and two tests started failing on assertions
# that had been true only while the table happened to be empty. Tests that pass
# because of what is NOT in the database are not testing anything.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://polis:devonly@localhost:5432/polis_test"
)


def _reachable(url: str) -> bool:
    # Checks the server via the maintenance database, because the test database
    # may not exist yet — that is what `_ensure_database` is for.
    url = url.rsplit("/", 1)[0] + "/postgres"
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:  # noqa: BLE001 — any failure means "not reachable"
        return False


requires_db = pytest.mark.skipif(
    not _reachable(TEST_DATABASE_URL),
    reason=f"no PostgreSQL at {TEST_DATABASE_URL} — start the polis-db container",
)


def _ensure_database(url: str) -> None:
    """Create the test database if it does not exist.

    Connects to the `postgres` maintenance database to do it, so a fresh
    checkout needs only a running PostgreSQL rather than a manual CREATE.
    """
    target = url.rsplit("/", 1)[-1]
    admin_url = url.rsplit("/", 1)[0] + "/postgres"
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": target}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{target}"'))
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    _ensure_database(TEST_DATABASE_URL)
    eng = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    # create_all, not `alembic upgrade`: the migration is verified separately by
    # its own test. Here the point is to exercise the *models*, and coupling
    # every schema test to migration replay would make both harder to read.
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A session inside a transaction that is always rolled back.

    Nothing a test writes survives it, so tests cannot order-depend on each
    other and the database never needs recreating between them.
    """
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False, future=True)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        # A test that provoked an IntegrityError has already rolled the
        # transaction back; rolling back again warns rather than failing, and a
        # warning nobody can act on is how real ones get ignored.
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def _redirect_backend_db(engine: Engine, monkeypatch):
    """Point `backend.db` at the test database for every db test.

    Without this, anything reached through `session_scope` — the scheduler, a
    service, a future CLI — would quietly talk to the *development* database
    while the test asserts against the test one. The lock test found it: it held
    an advisory lock in one database and `pipeline_cycle` took the same lock in
    another, so nothing was contended and the test passed for the wrong reason.
    """
    from sqlalchemy.orm import sessionmaker

    from backend import db as backend_db

    monkeypatch.setattr(backend_db, "get_engine", lambda: engine)
    monkeypatch.setattr(
        backend_db,
        "get_sessionmaker",
        lambda: sessionmaker(bind=engine, expire_on_commit=False, future=True),
    )


@pytest.fixture
def source(session: Session):
    """A saved enabled source, since almost every row hangs off one."""
    from backend.models import Source

    src = Source(
        key=f"test-{uuid.uuid4().hex[:8]}",
        name=f"Test source {uuid.uuid4().hex[:8]}",
        source_type="rss",
        url="https://news.example.com/rss",
        language="en",
    )
    session.add(src)
    session.flush()
    return src
