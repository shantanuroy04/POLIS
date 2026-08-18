"""The eight sources POLIS ingests. ⟵ DOC-014 §2

Every entry here has had its terms of use **read**, not merely its robots.txt.
France 24 was removed from this list after its licence turned out to forbid
exactly what POLIS does, and BBC Arabic is absent because bbc.co.uk refuses
automated fetches so its terms could not be read at all (DOC-014 §2.0.0, §2.0.3).

**Do not add a source here without recording its terms in DOC-014 first.** That
ordering is the whole control: a source reaches code only after the register.

**And do not add one on the strength of an HTTP 200.** Four UN News topic and
region feeds were listed here until a live run showed they return 200 with an
empty body — a status code is not evidence of content, the same way robots.txt
is not evidence of a licence. `python -m ingestion.check_sources` is what proves
a feed actually yields items (DOC-014 §2.0.4).

ponytail: a module-level tuple, not a table. The `sources` table lands in Week 5
and will supersede this — `SourceConfig` is already the shape a row maps onto,
so the adapter does not change when it does.
"""

from __future__ import annotations

from ingestion.sources.base import SourceConfig

UN_NEWS_TERMS = "UN: reuse of news material permitted with credit given and the UN advised"
RELIEFWEB_TERMS = "ReliefWeb: RSS used, not the API; API appname requirement does not apply"

SOURCES: tuple[SourceConfig, ...] = (
    SourceConfig(
        key="unnews-en",
        name="UN News — all news (English)",
        url="https://news.un.org/feed/subscribe/en/news/all/rss.xml",
        language="en",
        options={"terms": UN_NEWS_TERMS},
    ),
    SourceConfig(
        key="unnews-ar",
        name="UN News — all news (Arabic)",
        url="https://news.un.org/feed/subscribe/ar/news/all/rss.xml",
        language="ar",
        options={"terms": UN_NEWS_TERMS},
    ),
    SourceConfig(
        key="unnews-fr",
        name="UN News — all news (French)",
        url="https://news.un.org/feed/subscribe/fr/news/all/rss.xml",
        language="fr",
        options={"terms": UN_NEWS_TERMS},
    ),
    SourceConfig(
        key="reliefweb-en",
        name="ReliefWeb — updates (English)",
        url="https://reliefweb.int/updates/rss.xml",
        language="en",
        options={"terms": RELIEFWEB_TERMS},
    ),
)

BY_KEY: dict[str, SourceConfig] = {s.key: s for s in SOURCES}
