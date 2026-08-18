"""RSS adapter tests. ⟵ TRD §5.1, Implementation Plan task 2.4

Feeds are fixtures, not live requests. A test that hits news.un.org fails when
the network does, fails differently next week, and tests the publisher rather
than the adapter.
"""

from __future__ import annotations

import contextlib
import time
from datetime import datetime, timezone

import pytest

from ingestion.http_client import BlockedURLError, FetchError
from ingestion.sources import rss
from ingestion.sources.base import SourceConfigError, SourceFetchError
from ingestion.sources.rss import RssAdapter

SOURCE = rss.SourceConfig(
    key="test-en", name="Test feed", url="https://news.example.com/rss", language="en"
)

RSS_2_0 = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
  <title>Test Wire</title>
  <item>
    <title>Ceasefire holds for a third day</title>
    <link>https://news.example.com/a</link>
    <guid isPermaLink="false">urn:test:a</guid>
    <description>Reports from the region indicate the ceasefire is holding.</description>
    <pubDate>Tue, 11 Aug 2026 09:00:00 GMT</pubDate>
    <author>desk@example.com</author>
    <category>Peace and Security</category>
  </item>
  <item>
    <title>Aid convoy reaches the north</title>
    <link>https://news.example.com/b</link>
    <description>Twelve trucks crossed on Monday.</description>
    <pubDate>Mon, 10 Aug 2026 06:30:00 GMT</pubDate>
  </item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Wire</title>
  <entry>
    <title>Talks resume in the capital</title>
    <link href="https://news.example.com/c"/>
    <id>urn:test:c</id>
    <updated>2026-08-11T12:00:00Z</updated>
    <content type="html">&lt;p&gt;Delegations met on Tuesday.&lt;/p&gt;</content>
    <summary>Short summary that must lose to content.</summary>
  </entry>
</feed>"""


@pytest.fixture
def feed(monkeypatch):
    """Swap the guarded fetch for a fixture payload."""

    def _set(payload: bytes | Exception):
        def fake_fetch(url, **kwargs):
            if isinstance(payload, Exception):
                raise payload
            return payload

        monkeypatch.setattr(rss, "http_fetch", fake_fetch)

    return _set


def test_parses_rss_2_0(feed):
    feed(RSS_2_0)
    items = list(RssAdapter().fetch(SOURCE))
    assert [i.title for i in items] == [
        "Ceasefire holds for a third day",
        "Aid convoy reaches the north",
    ]
    first = items[0]
    assert first.external_id == "urn:test:a"
    assert first.url == "https://news.example.com/a"
    assert first.published_at == datetime(2026, 8, 11, 9, 0, tzinfo=timezone.utc)
    assert first.author_handle == "desk@example.com"
    assert first.source_key == "test-en"
    assert first.raw_metadata["feed_title"] == "Test Wire"
    assert first.raw_metadata["language"] == "en"


def test_parses_atom_and_prefers_content_over_summary(feed):
    feed(ATOM)
    item = next(iter(RssAdapter().fetch(SOURCE)))
    assert item.external_id == "urn:test:c"
    assert "Delegations met on Tuesday" in item.body
    assert "must lose to content" not in item.body


def test_does_not_clean_html(feed):
    """The adapter stores what the source published. Stripping here would make
    the stored item impossible to check against the feed ⟵ TRD §5.3 owns cleaning."""
    feed(ATOM)
    item = next(iter(RssAdapter().fetch(SOURCE)))
    assert "&lt;p&gt;" in item.body or "<p>" in item.body


def test_falls_back_to_link_when_guid_missing(feed):
    feed(RSS_2_0)
    items = list(RssAdapter().fetch(SOURCE))
    assert items[1].external_id == "https://news.example.com/b"


def test_since_filters_older_entries(feed):
    feed(RSS_2_0)
    since = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
    items = list(RssAdapter().fetch(SOURCE, since=since))
    assert [i.title for i in items] == ["Ceasefire holds for a third day"]


def test_undated_entries_survive_since(feed):
    """`since` cannot compare what has no date. Dropping such entries would lose
    real articles from feeds that omit pubDate."""
    feed(
        b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
      <item><title>No date here</title><link>https://news.example.com/d</link></item>
    </channel></rss>"""
    )
    items = list(RssAdapter().fetch(SOURCE, since=datetime.now(tz=timezone.utc)))
    assert [i.title for i in items] == ["No date here"]
    assert items[0].published_at is None


# --- failure contract ⟵ TRD §5.1, §5.10 ------------------------------------


def test_blocked_url_is_a_config_error_not_a_fetch_error(feed):
    """The guard refused before connecting and will refuse identically next
    cycle. Retrying it forever would hide a misconfiguration behind a badge."""
    feed(BlockedURLError("resolves to blocked address: 127.0.0.1"))
    with pytest.raises(SourceConfigError):
        list(RssAdapter().fetch(SOURCE))


def test_transport_failure_is_recoverable(feed):
    feed(FetchError("timeout"))
    with pytest.raises(SourceFetchError):
        list(RssAdapter().fetch(SOURCE))


def test_unparseable_feed_raises(feed):
    feed(b"this is not a feed at all")
    with pytest.raises(SourceFetchError):
        list(RssAdapter().fetch(SOURCE))


def test_empty_feed_raises(feed):
    feed(b'<?xml version="1.0"?><rss version="2.0"><channel><title>T</title></channel></rss>')
    with pytest.raises(SourceFetchError, match="no entries"):
        list(RssAdapter().fetch(SOURCE))


def test_malformed_but_recoverable_feed_still_yields(feed, caplog):
    """feedparser is lenient. A feed that trips bozo but still produces entries
    is worth ingesting with a warning — refusing it would drop real articles."""
    feed(
        b"""<rss version="2.0"><channel><title>Broken</title>
      <item><title>Still here</title><link>https://news.example.com/e</link></item>
    </channel>"""
    )  # unclosed <rss>
    items = list(RssAdapter().fetch(SOURCE))
    assert [i.title for i in items] == ["Still here"]


def test_entry_with_neither_title_nor_body_is_skipped(feed):
    feed(
        b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
      <item><link>https://news.example.com/f</link></item>
      <item><title>Real one</title><link>https://news.example.com/g</link></item>
    </channel></rss>"""
    )
    assert [i.title for i in RssAdapter().fetch(SOURCE)] == ["Real one"]


def test_dates_are_utc_regardless_of_machine_timezone(feed, monkeypatch):
    """Regression: the first implementation used time.mktime, which reads a
    struct_time as LOCAL time. On a UTC+5:30 machine every published_at moved
    5.5 hours into the past — plausible-looking timestamps, silently wrong, and
    the 14-day indicator baselines are computed against them."""
    monkeypatch.setenv("TZ", "Asia/Kolkata")
    with contextlib.suppress(AttributeError):
        time.tzset()  # absent on Windows; the assertion below holds either way
    feed(RSS_2_0)
    items = list(RssAdapter().fetch(SOURCE))
    assert items[0].published_at == datetime(2026, 8, 11, 9, 0, tzinfo=timezone.utc)
    assert items[1].published_at == datetime(2026, 8, 10, 6, 30, tzinfo=timezone.utc)
