"""The chained pipeline. ⟵ TRD §6.2, PRD §11.1, ADR-001

**One job, not four.** The original design ran ingest, scoring, indicators and
alerts on four independent timers, and ADR-001 claimed the result was "well
within" the 20-minute latency requirement. It was not: independent timers give a
worst case equal to the *sum* of their intervals, which was up to 80 minutes. The
arithmetic had never been done.

Chaining the stages into a single 10-minute tick makes the worst case the sum of
one poll wait and the stage durations:

    poll 10.0 + ingest 2.0 + score 2.5 + indicators 1.0 + alerts 0.5 = 16.0 min

against a 20-minute requirement ⟵ PRD §11.1. `backend/config.py` refuses to
start if the poll interval is raised above 10 minutes, because that number is
derived from this budget rather than chosen.

No broker, no queue, no worker. Plain sequential calls inside one process, with a
PostgreSQL advisory lock so an overrunning cycle is skipped rather than run
twice ⟵ ADR-011.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from backend.config import Settings, get_settings
from backend.db import session_scope, with_job_lock
from backend.services.scoring import score_pending
from ingestion.store import ingest_all, sync_sources

log = logging.getLogger(__name__)


def pipeline_cycle() -> None:
    """Stages B and C, chained. ⟵ TRD §6.2

    Stages D (indicators) and E (alerts) join here in Week 17; the budget in
    PRD §11.1 already reserves 1.5 minutes for them. Deliberately absent rather
    than stubbed — an empty function that logs "computing indicators" reads like
    a working stage in the log of a demo where nothing is computed.
    """
    with session_scope() as session:
        # max_instances=1 stops overlap inside one process. The advisory lock
        # stops it across processes, which is what a second instance during a
        # deploy would otherwise cause ⟵ TRD §6.2.
        if not with_job_lock(session, "pipeline"):
            return

        sync_sources(session)

        results = ingest_all(session)
        stored = sum(r.stored for r in results)
        failed_sources = [r.source_key for r in results if not r.ok]

        scoring = score_pending(session)

        log.info(
            "pipeline_cycle: %d sources, %d new items, %d scored, %d scoring failures%s",
            len(results),
            stored,
            scoring.scored,
            scoring.failed,
            f", unhealthy: {', '.join(failed_sources)}" if failed_sources else "",
        )


def create_scheduler(settings: Settings | None = None) -> BackgroundScheduler:
    """One scheduler, in the API process. ⟵ ADR-011

    A separate worker service would need a second always-on process, which the
    free tier does not provide and the workload does not justify: the pipeline is
    I/O-bound and idle for most of every ten minutes.
    """
    settings = settings or get_settings()
    scheduler = BackgroundScheduler(timezone="UTC")

    scheduler.add_job(
        pipeline_cycle,
        trigger="interval",
        minutes=settings.ingest_interval_minutes,
        id="pipeline_cycle",
        # A cycle that overruns must be skipped, not queued behind itself. The
        # next tick is ten minutes away and the work is idempotent.
        max_instances=1,
        coalesce=True,
        # Tolerate a late start — a cold container or a paused free-tier dyno
        # should still run the cycle rather than drop it silently.
        misfire_grace_time=120,
    )
    return scheduler
