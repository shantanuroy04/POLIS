"""Ingest writer tests. ⟵ TRD §5.4, §5.10, FR-2.5/2.6/2.7

Dedupe is finally exercised against persisted rows. Everything before this could
only test synthetic pairs, because duplicates appear across polls rather than
within one fetch.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import RawContent, Source
from ingestion import store
from ingestion.sources.base import RawItem, SourceConfig, SourceConfigError, SourceFetchError
from tests.db.conftest import requires_db

pytestmark = requires_db

NOW = datetime.now(tz=timezone.utc)

_BODY = (
    "The Security Council adopted a resolution on Mali on Tuesday, extending the mission "
    "mandate by one year and calling on all parties to resume political dialogue"
)


def _item(external_id: str, title: str = "Council extends Mali mandate", body: str = _BODY):
    return RawItem(
        source_key="test",
        external_id=external_id,
        url=f"https://news.example.com/{external_id}",
        title=title,
        body=body,
        published_at=NOW,
        raw_metadata={"feed_title": "Test"},
    )


def test_stores_a_new_item_end_to_end(session: Session, source: Source):
    processed = store.store_item(session, source, _item("a"))
    assert processed is not None
    assert processed.language_code == "en"
    assert processed.is_canonical is True
    assert processed.status == "pending_analysis"
    assert processed.simhash is not None

    raw = session.get(RawContent, processed.raw_content_id)
    assert raw.title == "Council extends Mali mandate"
    # The adapter's raw body is preserved; only processed_content is cleaned.
    assert raw.body == _BODY


def test_exact_duplicate_is_not_stored_twice(session: Session, source: Source):
    """FR-2.5. The same item reappears in the feed every poll until it scrolls
    off; storing it each time would multiply the corpus by the poll rate."""
    assert store.store_item(session, source, _item("a")) is not None
    assert store.store_item(session, source, _item("b")) is None

    # Scoped to this test's source. Counting the whole table passed only while
    # the database happened to be empty, and broke the moment a real ingest run
    # left rows behind — the fixture rolls back its own writes, not everyone's.
    stored = session.scalar(
        select(func.count()).select_from(RawContent).where(RawContent.source_id == source.id)
    )
    assert stored == 1


def test_punctuation_only_change_is_still_an_exact_duplicate(session: Session, source: Source):
    """The hash is taken over normalized_text, so a headline comma does not
    manufacture a new row."""
    store.store_item(session, source, _item("a"))
    assert store.store_item(session, source, _item("b", body=_BODY.replace(",", ";"))) is None


def test_near_duplicate_is_stored_and_joins_the_cluster(session: Session, source: Source):
    """FR-2.7. Near-duplicates are NOT discarded: cluster size is what IND-03
    measures, so throwing the second copy away deletes the measurement."""
    first = store.store_item(session, source, _item("a"))
    second = store.store_item(session, source, _item("b", body=_BODY + " immediately"))

    assert second is not None, "a near-duplicate must be stored, not dropped"
    assert second.cluster_id == first.cluster_id
    assert first.is_canonical is True
    assert second.is_canonical is False


def test_a_different_story_starts_its_own_cluster(session: Session, source: Source):
    first = store.store_item(session, source, _item("a"))
    other = store.store_item(
        session,
        source,
        _item(
            "b",
            title="Aid convoy reaches the north",
            body=(
                "An aid convoy of twelve trucks reached the north on Monday after weeks of "
                "negotiation with local groups over access routes and security guarantees"
            ),
        ),
    )
    assert other.cluster_id != first.cluster_id
    assert other.is_canonical is True


def test_items_outside_the_window_do_not_cluster(session: Session, source: Source):
    """A story republished three weeks later is a new story, not amplification
    of the old one ⟵ TRD §5.4."""
    first = store.store_item(session, source, _item("a"))
    first.processed_at = NOW - timedelta(days=store.DEDUPE_WINDOW_DAYS + 1)
    session.flush()

    later = store.store_item(session, source, _item("b", body=_BODY + " immediately"))
    assert later.cluster_id != first.cluster_id


def test_unsupported_language_is_stored_with_a_null_code(session: Session, source: Source):
    """Spanish is detected as "other" and kept. It is excluded from per-language
    indicators, not from the corpus — and the column only accepts ISO codes."""
    processed = store.store_item(
        session,
        source,
        _item(
            "es",
            title="El Consejo adopta una resolucion",
            body=(
                "El Consejo de Seguridad adopto una resolucion sobre Mali esta semana tras "
                "consultas prolongadas entre los miembros del organismo"
            ),
        ),
    )
    assert processed.language_code is None
    assert processed.language_uncertain is True


def test_empty_body_is_skipped(session: Session, source: Source):
    assert store.store_item(session, source, _item("x", title="", body="")) is None


# --- source health ⟵ TRD §5.10 ----------------------------------------------


def _config(source: Source) -> SourceConfig:
    return SourceConfig(key=source.key, name=source.name, url=source.url, language="en")


def test_successful_run_marks_the_source_healthy(session: Session, source: Source, monkeypatch):
    monkeypatch.setattr(
        store.RssAdapter, "fetch", lambda self, cfg, since=None: iter([_item("a"), _item("b")])
    )
    source.consecutive_failures = 2
    source.health_status = "degraded"

    result = store.ingest_source(session, source, _config(source))

    assert result.ok
    assert result.fetched == 2
    assert result.stored == 1 and result.duplicates == 1
    assert source.health_status == "healthy"
    assert source.consecutive_failures == 0
    assert source.last_success_at is not None


def test_fetch_failure_degrades_then_goes_unhealthy(session: Session, source: Source, monkeypatch):
    """One flaky fetch must not red-badge a working feed; three in a row must."""

    def boom(self, cfg, since=None):
        raise SourceFetchError("timeout")

    monkeypatch.setattr(store.RssAdapter, "fetch", boom)

    for expected in ("degraded", "degraded", "unhealthy"):
        store.ingest_source(session, source, _config(source))
        assert source.health_status == expected

    assert source.consecutive_failures == store.UNHEALTHY_AFTER
    assert source.last_error == "timeout"


def test_config_error_is_terminal_not_retried(session: Session, source: Source, monkeypatch):
    """A blocked URL will be blocked identically next cycle. Retrying forever
    would hide the misconfiguration behind a health badge."""

    def blocked(self, cfg, since=None):
        raise SourceConfigError("URL refused by guard")

    monkeypatch.setattr(store.RssAdapter, "fetch", blocked)
    store.ingest_source(session, source, _config(source))

    assert source.health_status == "config_error"
    assert source.consecutive_failures == 0, "a permanent error is not a failure streak"


def test_one_bad_source_does_not_stop_the_others(session: Session, monkeypatch):
    """AC-2. A single broken feed must not take the pipeline down."""
    store.sync_sources(session)
    calls: list[str] = []

    def half_broken(self, cfg, since=None):
        calls.append(cfg.key)
        if cfg.key.endswith("-ar"):
            raise SourceFetchError("boom")
        return iter([_item(f"{cfg.key}-1")])

    monkeypatch.setattr(store.RssAdapter, "fetch", half_broken)
    results = store.ingest_all(session)

    assert len(calls) == len(results) > 1
    assert any(not r.ok for r in results)
    assert any(r.ok for r in results)


# --- registry reconciliation -------------------------------------------------


def test_sync_sources_is_idempotent(session: Session):
    first = store.sync_sources(session)
    second = store.sync_sources(session)
    assert {s.id for s in first} == {s.id for s in second}
    # By key, not by table count: other rows may legitimately exist.
    keys = {s.key for s in first}
    assert len(keys) == len(first)


def test_sync_preserves_runtime_state(session: Session):
    """The registry owns identity and terms; the table owns health. A governance
    edit must not silently reset a source's failure history."""
    rows = store.sync_sources(session)
    rows[0].consecutive_failures = 2
    rows[0].health_status = "degraded"
    session.flush()

    store.sync_sources(session)
    assert rows[0].consecutive_failures == 2
    assert rows[0].health_status == "degraded"


def test_a_source_removed_from_the_registry_is_not_fetched(
    session: Session, source: Source, monkeypatch
):
    """France 24 was removed on governance grounds (DOC-014 §2.0.0). A row left
    behind in the table must not keep being fetched."""
    fetched: list[str] = []
    monkeypatch.setattr(
        store.RssAdapter,
        "fetch",
        lambda self, cfg, since=None: fetched.append(cfg.key) or iter([]),
    )
    results = store.ingest_all(session)

    assert source.key not in fetched
    assert source.key not in [r.source_key for r in results]
