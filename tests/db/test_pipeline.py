"""Scoring stage and chained pipeline. ⟵ TRD §6.2, PRD §11.1, ADR-001"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import NlpResult, ProcessedContent, Source
from backend.services import scoring
from backend.services.scoring import score_pending
from ingestion import store
from ingestion.sources.base import RawItem
from tests.db.conftest import requires_db

pytestmark = requires_db

NOW = datetime.now(tz=timezone.utc)


def _item(n: int) -> RawItem:
    return RawItem(
        source_key="test",
        external_id=f"urn:pipeline:{n}",
        url=f"https://news.example.com/{n}",
        title=f"Council debates item {n}",
        body=(
            f"Delegates met on Tuesday to discuss agenda item {n}, with several members "
            "calling for the mandate to be extended and others urging a review of its scope"
        ),
        published_at=NOW,
    )


def _pending(session: Session, source: Source, count: int) -> list[ProcessedContent]:
    return [store.store_item(session, source, _item(n)) for n in range(count)]


# --- scoring ⟵ TRD §6.2 stage C ---------------------------------------------


def test_scores_pending_items_and_writes_results(session: Session, source: Source):
    rows = _pending(session, source, 3)
    result = score_pending(session, limit=10)

    assert result.scored == 3
    assert result.failed == 0
    for row in rows:
        assert row.status == "analyzed"

    stored = session.scalars(
        select(NlpResult).where(NlpResult.processed_content_id.in_([r.id for r in rows]))
    ).all()
    assert len(stored) == 3
    first = stored[0]
    assert first.model_version == "polis-stub-v0.0.1"
    assert first.schema_version == "1.0"
    assert set(first.sentiment_scores) == {"negative", "neutral", "positive"}


def test_already_scored_items_are_not_rescored(session: Session, source: Source):
    _pending(session, source, 2)
    assert score_pending(session, limit=10).scored == 2
    assert score_pending(session, limit=10).scored == 0


def test_the_batch_limit_is_the_latency_budget(session: Session, source: Source):
    """PRD §11.1 allots stage C 2.5 minutes, which at NFR-1.3's 1.5 s per item is
    ~100 items. An uncapped batch blows the 20-minute end-to-end requirement on
    the first busy cycle ⟵ TBD-16."""
    _pending(session, source, 5)
    assert score_pending(session, limit=2).scored == 2
    assert score_pending(session, limit=2).scored == 2
    assert score_pending(session, limit=2).scored == 1


def test_oldest_items_are_scored_first(session: Session, source: Source):
    """A backlog must drain in arrival order rather than starving whatever has
    already waited longest."""
    rows = _pending(session, source, 3)
    score_pending(session, limit=1)
    assert rows[0].status == "analyzed"
    assert rows[1].status == "pending_analysis"


def test_one_unscoreable_item_does_not_abandon_the_batch(
    session: Session, source: Source, monkeypatch
):
    """TRD §5.10. The failed row stays visible in the feed marked unanalysed
    rather than disappearing, and the rest of the batch still gets scored."""
    rows = _pending(session, source, 3)
    calls = {"n": 0}
    real = scoring.score_text

    def flaky(text, lang=None):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("model exploded")
        return real(text, lang=lang)

    monkeypatch.setattr(scoring, "score_text", flaky)
    result = score_pending(session, limit=10)

    assert result.scored == 2
    assert result.failed == 1
    assert [r.status for r in rows].count("scoring_failed") == 1
    assert [r.status for r in rows].count("analyzed") == 2


def test_a_failed_item_is_not_retried_forever(session: Session, source: Source, monkeypatch):
    _pending(session, source, 1)
    monkeypatch.setattr(
        scoring, "score_text", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    assert score_pending(session, limit=10).failed == 1
    # scoring_failed is not pending_analysis, so the next cycle skips it.
    assert score_pending(session, limit=10).scored == 0


def test_scoring_nothing_is_not_an_error(session: Session):
    result = score_pending(session, limit=10)
    assert result.scored == 0 and result.failed == 0


def test_language_is_passed_through_to_the_model(session: Session, source: Source, monkeypatch):
    rows = _pending(session, source, 1)
    rows[0].language_code = "fr"
    session.flush()

    seen = {}
    real = scoring.score_text
    monkeypatch.setattr(
        scoring,
        "score_text",
        lambda text, lang=None: (seen.update(lang=lang), real(text, lang=lang))[1],
    )
    score_pending(session, limit=1)
    assert seen["lang"] == "fr"


# --- the chained cycle ⟵ ADR-001 --------------------------------------------


def test_pipeline_cycle_is_a_single_job_not_four_timers():
    """ADR-001 originally ran four independent timers and claimed the result was
    within the 20-minute budget. Independent timers give a worst case equal to
    the SUM of their intervals — up to 80 minutes. One chained job is what makes
    PRD §11.1's 16.0-minute worst case true."""
    from backend.scheduler import create_scheduler

    scheduler = create_scheduler()
    jobs = scheduler.get_jobs()

    assert len(jobs) == 1, f"expected one chained job, found {[j.id for j in jobs]}"
    job = jobs[0]
    assert job.id == "pipeline_cycle"
    assert job.max_instances == 1, "an overrunning cycle must be skipped, not run twice"
    assert job.trigger.interval.total_seconds() <= 10 * 60, "stage A of the PRD §11.1 budget"


def test_creating_the_app_does_not_start_polling():
    """Importing or building the app in a test, in Alembic, or in a REPL must
    never start fetching the internet."""
    from backend.main import create_app

    app = create_app()
    assert app.state.scheduler is None

    with_sched = create_app(with_scheduler=True)
    assert with_sched.state.scheduler is not None
    assert not with_sched.state.scheduler.running, "started by lifespan, not by the factory"


def test_pipeline_cycle_skips_when_the_lock_is_held(session: Session, engine, monkeypatch):
    """The advisory lock stops a second process overlapping — a deploy running
    two instances briefly is the real case ⟵ TRD §6.2."""
    from sqlalchemy import text as sql_text

    from backend import scheduler as sched
    from backend.db import ADVISORY_LOCK_NAMESPACE

    held = session.execute(
        sql_text("SELECT pg_try_advisory_xact_lock(:ns, 1)"), {"ns": ADVISORY_LOCK_NAMESPACE}
    ).scalar_one()
    assert held is True

    ingested = []
    monkeypatch.setattr(sched, "ingest_all", lambda s: ingested.append(1) or [])
    monkeypatch.setattr(sched, "sync_sources", lambda s: [])

    sched.pipeline_cycle()
    assert ingested == [], "a cycle ran while another held the lock"
