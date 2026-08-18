"""The contract every source type implements. ⟵ TRD §5.1, FR-1.1, FR-1.5–1.7

Adding a source type must not require a change to the pipeline. That only holds
if adapters agree on two things: the shape they emit (:class:`RawItem`) and the
way they fail (:class:`SourceFetchError` vs :class:`SourceConfigError`).

The failure split is the load-bearing part. A timeout is worth retrying next
cycle; a feed whose URL now resolves to a private address never will be, and
retrying it forever hides a misconfiguration behind a health badge.
"""

from __future__ import annotations

import abc
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class SourceError(Exception):
    """Base for every adapter failure. Adapters never raise anything else."""


class SourceFetchError(SourceError):
    """Recoverable. Retry next cycle, count against source health.

    Network timeout, 5xx, a feed that is briefly malformed.
    """


class SourceConfigError(SourceError):
    """Unrecoverable without human action. Mark the source unhealthy, stop retrying.

    A blocked URL, a feed that has permanently moved, credentials that no longer
    work. TRD §5.10 requires these be surfaced in the UI rather than absorbed.
    """


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """What an adapter needs to know about a source.

    ponytail: a plain dataclass, not the `sources` ORM row TRD §5.1 names. The
    table does not exist until Week 5 and the adapter does not need it to exist —
    `fetch` only reads these fields, so the ORM row can satisfy the same shape
    later without the adapter changing. Registry today, database then.
    """

    key: str
    name: str
    url: str
    language: str
    kind: str = "rss"
    # Free-form, adapter-specific. Kept out of the typed fields so a new source
    # type cannot force a schema change on every other one.
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RawItem:
    """One item as the source published it. ⟵ TRD §5.1

    Deliberately unclean: HTML is not stripped, text is not normalised, language
    is not detected. Those belong to the cleaner, and an adapter that did them
    would make its own output impossible to audit against the source.
    """

    source_key: str
    external_id: str
    url: str
    title: str
    body: str
    published_at: datetime | None
    author_handle: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(abc.ABC):
    """Uniform fetch contract. ⟵ TRD §5.1"""

    kind: str

    @abc.abstractmethod
    def fetch(self, source: SourceConfig, since: datetime | None = None) -> Iterator[RawItem]:
        """Yield items published after `since`, newest-first order not guaranteed.

        Raises SourceFetchError or SourceConfigError — never a bare exception,
        and never swallows one silently.
        """
        raise NotImplementedError
