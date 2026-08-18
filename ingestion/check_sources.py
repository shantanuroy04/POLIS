"""Prove every registered source actually yields items. ⟵ GOV-10, DOC-014 §2.0.4

    python -m ingestion.check_sources

Not a unit test: it needs the network, so it must never gate CI. It exists
because four feeds sat in the register returning HTTP 200 with an empty body,
and only a live fetch exposed them. Run it before the demo, and whenever a
source is added.
"""

from __future__ import annotations

import sys

from ingestion.registry import SOURCES
from ingestion.sources.base import SourceError
from ingestion.sources.rss import RssAdapter


def main() -> int:
    adapter = RssAdapter()
    failures = 0

    for source in SOURCES:
        try:
            items = list(adapter.fetch(source))
        except SourceError as exc:
            print(f"FAIL  {source.key:<16} {type(exc).__name__}: {exc}")
            failures += 1
            continue

        newest = max((i.published_at for i in items if i.published_at), default=None)
        print(f"ok    {source.key:<16} {len(items):>3} items  newest={newest}")

    healthy = len(SOURCES) - failures
    print("")
    print(f"{healthy}/{len(SOURCES)} sources healthy")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
