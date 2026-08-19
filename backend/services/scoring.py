"""Stage C of the pipeline: score what ingestion left pending. ⟵ TRD §6.2, PRD §11.1

The only thing in POLIS that calls `score_text`. Everything the model produces
enters the database here and nowhere else, so the frozen contract has exactly one
consumer to keep honest ⟵ ADR-008.

**No FastAPI imports.** This is a service, callable from the scheduler, a test,
or a CLI — TRD §4.1 keeps that boundary so the pipeline never depends on there
being a web request.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import NlpResult, ProcessedContent
from ml.predict import score_text

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ScoringResult:
    scored: int = 0
    failed: int = 0
    elapsed_ms: int = 0

    @property
    def per_item_ms(self) -> float:
        return self.elapsed_ms / self.scored if self.scored else 0.0


def _row_from(content: ProcessedContent, payload: dict) -> NlpResult:
    """Map the frozen `score_text` shape onto columns.

    The one place the contract meets the schema. If PRD §9.1 ever changes, this
    function and `backend/models` both have to change in the same commit — which
    is the point of keeping the mapping in a single readable place rather than
    spread across an ORM event or a pydantic adapter.
    """
    return NlpResult(
        processed_content_id=content.id,
        model_version=payload["model_version"],
        schema_version=payload["schema_version"],
        sentiment_label=payload["sentiment"]["label"],
        sentiment_confidence=payload["sentiment"]["confidence"],
        sentiment_scores=payload["sentiment"]["scores"],
        hostility_label=payload["hostility"]["label"],
        hostility_confidence=payload["hostility"]["confidence"],
        hostility_scores=payload["hostility"]["scores"],
        disinfo_label=payload["disinfo"]["label"],
        disinfo_confidence=payload["disinfo"]["confidence"],
        disinfo_scores=payload["disinfo"]["scores"],
        stance_label=payload["stance"]["label"],
        stance_confidence=payload["stance"]["confidence"],
        stance_scores=payload["stance"]["scores"],
        entities=payload["entities"],
        topics=payload["topics"],
        inference_ms=payload["meta"].get("inference_ms"),
    )


def score_pending(session: Session, limit: int | None = None) -> ScoringResult:
    """Score up to `limit` items awaiting analysis, oldest first.

    The cap is not a performance tweak, it is the latency budget. PRD §11.1
    allots stage C 2.5 minutes, which at NFR-1.3's 1.5 s per item is ~100 items;
    an uncapped batch would blow the 20-minute end-to-end requirement on the
    first busy cycle ⟵ TBD-16.

    Oldest first, so a backlog drains in the order it arrived rather than
    starving the items that have already waited longest.
    """
    from backend.config import get_settings

    limit = limit if limit is not None else get_settings().model_scoring_batch_limit

    pending = list(
        session.scalars(
            select(ProcessedContent)
            .where(ProcessedContent.status == "pending_analysis")
            .order_by(ProcessedContent.processed_at)
            .limit(limit)
        )
    )
    if not pending:
        return ScoringResult()

    started = time.monotonic()
    scored = failed = 0

    for content in pending:
        try:
            payload = score_text(content.cleaned_text, lang=content.language_code)
            session.add(_row_from(content, payload))
            content.status = "analyzed"
            scored += 1
        except Exception:
            # One unscoreable item must not abandon the batch ⟵ TRD §5.10. The
            # row stays visible in the feed marked as unanalysed rather than
            # disappearing, and it is not retried forever.
            log.exception("scoring failed for processed_content %s", content.id)
            content.status = "scoring_failed"
            failed += 1

    session.flush()
    elapsed_ms = int((time.monotonic() - started) * 1000)

    result = ScoringResult(scored=scored, failed=failed, elapsed_ms=elapsed_ms)
    log.info(
        "scored %d, failed %d, %.1f ms/item (budget 1500 ms ⟵ NFR-1.3)",
        scored,
        failed,
        result.per_item_ms,
    )
    return result
