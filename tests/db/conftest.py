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

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://polis:devonly@localhost:5432/polis"
)


def _reachable(url: str) -> bool:
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


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
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
