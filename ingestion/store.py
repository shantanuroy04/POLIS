"""Persist what the adapters read. ⟵ TRD §5.4, §5.10, FR-2.5/2.6/2.7

Plain functions taking a `Session`. There is no repository class, because
SQLAlchemy's Session already is one — a wrapper whose every method forwards a
query is an abstraction over an abstraction, and it makes the SQL harder to find
when a query is slow.

Dedupe finally runs against data that persists. Until now it could only be
exercised on synthetic pairs, because duplicates appear *across* polls and days
rather than within a single fetch.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import ProcessedContent, RawContent, Source
from ingestion.clean import clean_text
from ingestion.dedupe import (
    MAX_HAMMING,
    MIN_JACCARD,
    hamming,
    hash_exact,
    jaccard,
    shingles,
    simhash,
    to_signed64,
)
from ingestion.language import detect
from ingestion.registry import SOURCES
from ingestion.sources.base import (
    RawItem,
    SourceConfig,
    SourceConfigError,
    SourceFetchError,
)
from ingestion.sources.rss import RssAdapter

log = logging.getLogger(__name__)

# ⟵ TRD §5.4. Near-duplicate candidates are drawn from a rolling window; a story
# republished three weeks later is a new story, not an amplification of the old.
DEDUPE_WINDOW_DAYS = 7

# ⟵ TRD §5.10. Three consecutive failures move a source from degraded to
# unhealthy, so one flaky fetch does not red-badge a working feed.
UNHEALTHY_AFTER = 3


@dataclass(frozen=True, slots=True)
class IngestResult:
    source_key: str
    fetched: int = 0
    stored: int = 0
    duplicates: int = 0
    near_duplicates: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def sync_sources(session: Session) -> list[Source]:
    """Reconcile the registry into the `sources` table.

    The registry stays the source of truth for *which* feeds exist and what
    their terms are (DOC-014 §2); the table holds mutable runtime state —
    health, cursors, last success. Splitting them this way means a governance
    decision is a code review, not an UPDATE.
    """
    rows: list[Source] = []
    for config in SOURCES:
        row = session.scalar(select(Source).where(Source.key == config.key))
        if row is None:
            row = Source(
                key=config.key,
                name=config.name,
                source_type=config.kind,
                url=config.url,
                language=config.language,
                config=dict(config.options),
            )
            session.add(row)
        else:
            # Registry wins on identity and terms; runtime state is not touched.
            row.name = config.name
            row.url = config.url
            row.language = config.language
            row.config = dict(config.options)
        rows.append(row)
    session.flush()
    return rows


def _find_cluster(session: Session, normalized: str, fingerprint: int) -> uuid.UUID | None:
    """The cluster this text belongs to, or None if it starts a new one.

    ponytail: scans every fingerprint in the window rather than using the banded
    index TRD §5.4 describes. At roughly 100 items a day the window holds ~700
    rows, and comparing 700 integers in Python is faster than the round trip a
    band lookup would save. The banded index also no longer has its pigeonhole
    guarantee at a Hamming threshold of 12 — see ingestion/dedupe.py.
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=DEDUPE_WINDOW_DAYS)
    candidates = session.execute(
        select(
            ProcessedContent.cluster_id,
            ProcessedContent.simhash,
            ProcessedContent.normalized_text,
        ).where(
            ProcessedContent.processed_at >= cutoff,
            ProcessedContent.simhash.is_not(None),
        )
    ).all()

    mine = shingles(normalized)
    for cluster_id, other_hash, other_text in candidates:
        # Both sides are signed here; hamming masks to 64 bits, so the
        # comparison is on bit patterns rather than on numeric values.
        if hamming(fingerprint, other_hash) > MAX_HAMMING:
            continue
        # Hamming is the filter; Jaccard decides ⟵ ingestion/dedupe.py.
        if jaccard(mine, shingles(other_text)) >= MIN_JACCARD:
            return cluster_id
    return None


def store_item(session: Session, source: Source, item: RawItem) -> ProcessedContent | None:
    """Clean, fingerprint, dedupe and persist one item.

    Returns None when the item is an exact duplicate already stored — the row
    exists, so there is nothing to add. Near-duplicates ARE stored: they join an
    existing cluster as non-canonical, because cluster size is what IND-03
    measures and discarding them would delete the measurement ⟵ FR-2.7.
    """
    result = clean_text(f"{item.title}. {item.body}" if item.title else item.body)
    if not result.cleaned_text:
        return None

    content_hash = hash_exact(result.normalized_text)

    # Exact duplicate ⟵ FR-2.5. Checked before insert rather than relying on the
    # unique index to raise, because the common case is "seen it last poll" and
    # an exception per unchanged item would make the log useless.
    if session.scalar(select(RawContent.id).where(RawContent.content_hash == content_hash)):
        return None

    # Stored signed, because PostgreSQL bigint is signed and SimHash fills all
    # 64 bits ⟵ ingestion/dedupe.to_signed64.
    fingerprint = to_signed64(simhash(result.normalized_text))
    cluster_id = _find_cluster(session, result.normalized_text, fingerprint)
    is_canonical = cluster_id is None
    if cluster_id is None:
        cluster_id = uuid.uuid4()

    language = detect(result.cleaned_text)

    raw = RawContent(
        source_id=source.id,
        external_id=item.external_id,
        url=item.url or None,
        title=item.title or None,
        body=item.body,
        author_handle=item.author_handle,
        published_at=item.published_at,
        content_hash=content_hash,
        source_metadata=item.raw_metadata,
    )
    session.add(raw)
    session.flush()

    processed = ProcessedContent(
        raw_content_id=raw.id,
        cleaned_text=result.cleaned_text,
        normalized_text=result.normalized_text,
        # "other" and "und" are not ISO codes and the column constrains shape;
        # an undetectable language is stored as NULL with the flag set.
        language_code=language.code if language.supported else None,
        language_confidence=language.confidence,
        language_uncertain=language.uncertain or not language.supported,
        simhash=fingerprint,
        cluster_id=cluster_id,
        is_canonical=is_canonical,
        truncated=result.truncated,
        status="clean_degraded" if result.degraded else "pending_analysis",
    )
    session.add(processed)
    session.flush()
    return processed


def ingest_source(session: Session, source: Source, config: SourceConfig) -> IngestResult:
    """Fetch one source and persist what is new, updating its health either way."""
    source.last_run_at = datetime.now(tz=timezone.utc)

    try:
        items = list(RssAdapter().fetch(config))
    except SourceConfigError as exc:
        # Permanent: retrying cannot help, and a retry loop would hide the
        # misconfiguration behind a badge ⟵ TRD §5.10.
        source.health_status = "config_error"
        source.last_error = str(exc)[:500]
        log.error("%s: configuration error, disabling retries: %s", source.key, exc)
        return IngestResult(source_key=source.key, error=str(exc))
    except SourceFetchError as exc:
        source.consecutive_failures += 1
        source.health_status = (
            "unhealthy" if source.consecutive_failures >= UNHEALTHY_AFTER else "degraded"
        )
        source.last_error = str(exc)[:500]
        log.warning(
            "%s: fetch failed (%d consecutive): %s", source.key, source.consecutive_failures, exc
        )
        return IngestResult(source_key=source.key, error=str(exc))

    stored = duplicates = near = 0
    for item in items:
        processed = store_item(session, source, item)
        if processed is None:
            duplicates += 1
            continue
        stored += 1
        if not processed.is_canonical:
            near += 1

    source.consecutive_failures = 0
    source.health_status = "healthy"
    source.last_error = None
    source.last_success_at = datetime.now(tz=timezone.utc)

    return IngestResult(
        source_key=source.key,
        fetched=len(items),
        stored=stored,
        duplicates=duplicates,
        near_duplicates=near,
    )


def ingest_all(session: Session) -> list[IngestResult]:
    """Every enabled source, one pass. Stage B of `pipeline_cycle` ⟵ TRD §6.2.

    One source failing must not stop the others ⟵ AC-2, so each is handled
    independently and the failures are returned rather than raised.
    """
    by_key = {c.key: c for c in SOURCES}
    results: list[IngestResult] = []

    for source in session.scalars(select(Source).where(Source.status == "enabled")):
        config = by_key.get(source.key)
        if config is None:
            # In the table but no longer in the registry: a source was removed
            # on governance grounds (DOC-014 §2.0.0) and must not be fetched.
            log.warning("%s: in database but not in the registry; skipping", source.key)
            continue
        results.append(ingest_source(session, source, config))

    return results
