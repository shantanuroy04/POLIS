"""RSS/Atom adapter. ⟵ TRD §5.1, FR-1.1, FR-1.5

Every byte this parses came from a source POLIS does not control, so two rules
hold throughout:

* The bytes arrive via ``http_client.fetch`` — SSRF-guarded, size-capped, and
  therefore bounded before feedparser ever sees them. The 2 MB cap is what keeps
  a decompression or entity-expansion bomb from being feedparser's problem.
* Nothing here cleans, strips or normalises. An adapter that silently rewrote
  its input would make the stored item impossible to check against the source.
  HTML stripping and NFKC normalisation belong to the cleaner (TRD §5.3).
"""

from __future__ import annotations

import calendar
import hashlib
import logging
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

import feedparser

from ingestion.http_client import BlockedURLError, FetchError
from ingestion.http_client import fetch as http_fetch
from ingestion.sources.base import (
    RawItem,
    SourceAdapter,
    SourceConfig,
    SourceConfigError,
    SourceFetchError,
)

log = logging.getLogger(__name__)


def _to_utc(parsed: time.struct_time | None) -> datetime | None:
    """feedparser's *_parsed fields are UTC struct_time, or absent.

    Absent is normal, not an error: plenty of valid feeds omit a date on some
    entries. The item is still worth ingesting; `published_at=None` lets the
    pipeline fall back to first-seen time rather than inventing one here.
    """
    if not parsed:
        return None
    try:
        # calendar.timegm, NOT time.mktime. mktime interprets a struct_time as
        # LOCAL time, so on a machine at UTC+5:30 every published_at silently
        # moved 5.5 hours into the past. That corrupts the 14-day baselines the
        # indicators are computed against, and nothing downstream would have
        # flagged it — the timestamps stay plausible, just wrong.
        return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
    except (OverflowError, ValueError, TypeError):
        return None


def _first_nonempty(*values: Any) -> str:
    for v in values:
        if isinstance(v, str) and v.strip():
            return v
    return ""


def _body_of(entry: Any) -> str:
    """Prefer full content over the summary, and take the first content block.

    Atom permits several `content` elements; feeds that use more than one in
    practice put the article in the first. Falls back to summary, then to the
    title, so an entry always has something to hash and dedupe on.
    """
    contents = getattr(entry, "content", None)
    if contents:
        first = contents[0]
        value = first.get("value") if isinstance(first, dict) else getattr(first, "value", "")
        if isinstance(value, str) and value.strip():
            return value
    return _first_nonempty(
        getattr(entry, "summary", ""),
        getattr(entry, "description", ""),
        getattr(entry, "title", ""),
    )


def _external_id(entry: Any, source: SourceConfig, url: str, title: str) -> str:
    """A stable per-source identity for the entry.

    Order matters. `id`/`guid` is what the publisher intends as the identity, so
    it wins. A link is the next most stable. Only when both are missing is a
    hash of title+date used — that is a last resort, because an edited title
    then reads as a new item. Dedup (Week 4) is what actually catches those; this
    field only has to be stable enough not to manufacture duplicates on its own.
    """
    for candidate in (getattr(entry, "id", None), getattr(entry, "guid", None), url):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    digest = hashlib.sha256(
        f"{source.key}|{title}|{getattr(entry, 'published', '')}".encode()
    ).hexdigest()
    return f"sha256:{digest}"


class RssAdapter(SourceAdapter):
    """Parses RSS 0.9x–2.0 and Atom, whichever the feed happens to be."""

    kind = "rss"

    def fetch(self, source: SourceConfig, since: datetime | None = None) -> Iterator[RawItem]:
        try:
            payload = http_fetch(source.url)
        except BlockedURLError as exc:
            # Permanent by definition: the guard refused before connecting, and
            # it will refuse identically next cycle ⟵ TRD §5.10.
            raise SourceConfigError(f"{source.key}: URL refused by guard: {exc}") from exc
        except FetchError as exc:
            raise SourceFetchError(f"{source.key}: fetch failed: {exc}") from exc

        parsed = feedparser.parse(payload)
        entries = getattr(parsed, "entries", []) or []

        # bozo means "this did not parse cleanly". feedparser is lenient and
        # often recovers entries anyway, so a bozo feed with entries is worth
        # ingesting with a warning; a bozo feed with none is a real failure.
        if getattr(parsed, "bozo", 0) and not entries:
            raise SourceFetchError(
                f"{source.key}: unparseable feed: {getattr(parsed, 'bozo_exception', 'unknown')}"
            )
        if getattr(parsed, "bozo", 0):
            log.warning(
                "%s: feed parsed with errors, %d entries recovered: %s",
                source.key,
                len(entries),
                getattr(parsed, "bozo_exception", "unknown"),
            )
        if not entries:
            raise SourceFetchError(f"{source.key}: feed contained no entries")

        feed_title = getattr(getattr(parsed, "feed", None), "title", "") or ""

        for entry in entries:
            published_at = _to_utc(
                getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
            )
            # An entry with no date is kept, not dropped: `since` cannot exclude
            # what it cannot compare, and dropping it would lose real articles
            # from feeds that simply omit the field.
            if since is not None and published_at is not None and published_at <= since:
                continue

            url = _first_nonempty(getattr(entry, "link", ""))
            title = _first_nonempty(getattr(entry, "title", ""))
            body = _body_of(entry)
            if not title and not body:
                continue  # nothing to store, nothing to score

            yield RawItem(
                source_key=source.key,
                external_id=_external_id(entry, source, url, title),
                url=url,
                title=title,
                body=body,
                published_at=published_at,
                author_handle=_first_nonempty(getattr(entry, "author", "")) or None,
                raw_metadata={
                    "feed_title": feed_title,
                    "language": source.language,
                    "tags": [
                        t.get("term", "")
                        for t in (getattr(entry, "tags", None) or [])
                        if isinstance(t, dict)
                    ][:10],
                },
            )
