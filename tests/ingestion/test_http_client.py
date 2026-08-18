"""Guarded fetch tests. ⟵ SEC-12, SEC-13, FR-1.4, Implementation Plan task 2.3

HTTP is mocked with respx and DNS is stubbed, so nothing here touches the
network. The fifth SSRF vector from TRD §14.5 — a public host that redirects to
an internal one — can only be tested here, because it needs a response.
"""

from __future__ import annotations

import socket

import httpx
import pytest
import respx

from ingestion import http_client
from ingestion.http_client import (
    FetchError,
    ResponseTooLargeError,
    TooManyRedirectsError,
    fetch,
)
from ingestion.url_guard import BlockedURLError

PUBLIC = "93.184.216.34"


@pytest.fixture(autouse=True)
def _no_pacing(monkeypatch):
    """The pacer sleeps a real second between requests to a host. Correct in
    production, intolerable in a test suite."""
    monkeypatch.setattr(http_client._pacer, "_min_interval", 0.0)


@pytest.fixture
def dns(monkeypatch):
    table: dict[str, list[str]] = {}

    def fake_getaddrinfo(host, *args, **kwargs):
        if host not in table:
            raise socket.gaierror(f"no stub for {host}")
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (addr, 0))
            for addr in table[host]
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    return table


@respx.mock
def test_fetches_a_public_url(dns):
    dns["news.example.com"] = [PUBLIC]
    respx.get("https://news.example.com/rss").mock(
        return_value=httpx.Response(200, content=b"<rss/>")
    )
    assert fetch("https://news.example.com/rss") == b"<rss/>"


@respx.mock
def test_sends_the_project_user_agent(dns):
    dns["news.example.com"] = [PUBLIC]
    route = respx.get("https://news.example.com/rss").mock(
        return_value=httpx.Response(200, content=b"ok")
    )
    fetch("https://news.example.com/rss")
    ua = route.calls.last.request.headers["user-agent"]
    assert "POLIS" in ua  # PRD §10 — POLIS identifies itself honestly


# --- SSRF vector 5: public host redirecting somewhere internal --------------


@respx.mock
def test_blocks_redirect_to_internal_address(dns):
    """The initial host is genuinely public. Only the hop is hostile, which is
    why follow_redirects=False and per-hop re-validation exist."""
    dns["news.example.com"] = [PUBLIC]
    dns["metadata.internal"] = ["169.254.169.254"]
    respx.get("https://news.example.com/rss").mock(
        return_value=httpx.Response(
            302, headers={"location": "http://metadata.internal/latest/meta-data/"}
        )
    )
    with pytest.raises(BlockedURLError, match="169.254.169.254"):
        fetch("https://news.example.com/rss")


@respx.mock
def test_follows_a_legitimate_redirect(dns):
    dns["news.example.com"] = [PUBLIC]
    dns["www.example.com"] = [PUBLIC]
    respx.get("https://news.example.com/rss").mock(
        return_value=httpx.Response(301, headers={"location": "https://www.example.com/rss"})
    )
    respx.get("https://www.example.com/rss").mock(
        return_value=httpx.Response(200, content=b"moved but fine")
    )
    assert fetch("https://news.example.com/rss") == b"moved but fine"


@respx.mock
def test_resolves_a_relative_redirect(dns):
    dns["news.example.com"] = [PUBLIC]
    respx.get("https://news.example.com/rss").mock(
        return_value=httpx.Response(302, headers={"location": "/feed/atom.xml"})
    )
    respx.get("https://news.example.com/feed/atom.xml").mock(
        return_value=httpx.Response(200, content=b"atom")
    )
    assert fetch("https://news.example.com/rss") == b"atom"


@respx.mock
def test_gives_up_after_three_redirects(dns):
    dns["news.example.com"] = [PUBLIC]
    respx.get(url__regex=r"https://news\.example\.com/hop\d").mock(
        side_effect=lambda request: httpx.Response(
            302, headers={"location": f"/hop{int(request.url.path[-1]) + 1}"}
        )
    )
    with pytest.raises(TooManyRedirectsError):
        fetch("https://news.example.com/hop1")


@respx.mock
def test_redirect_without_location_is_an_error(dns):
    dns["news.example.com"] = [PUBLIC]
    respx.get("https://news.example.com/rss").mock(return_value=httpx.Response(302))
    with pytest.raises(FetchError, match="no Location"):
        fetch("https://news.example.com/rss")


# --- Size cap ⟵ SEC-13 -----------------------------------------------------


@respx.mock
def test_aborts_an_oversized_body(dns, monkeypatch):
    dns["news.example.com"] = [PUBLIC]
    settings = http_client.get_settings()
    monkeypatch.setattr(settings, "ingest_max_bytes", 1024)
    respx.get("https://news.example.com/big").mock(
        return_value=httpx.Response(200, content=b"x" * 4096)
    )
    with pytest.raises(ResponseTooLargeError):
        fetch("https://news.example.com/big")


@respx.mock
def test_a_lying_content_length_does_not_help(dns, monkeypatch):
    """The cap is enforced on bytes actually read, so a small declared
    Content-Length cannot smuggle a large body past it."""
    dns["news.example.com"] = [PUBLIC]
    settings = http_client.get_settings()
    monkeypatch.setattr(settings, "ingest_max_bytes", 1024)
    respx.get("https://news.example.com/liar").mock(
        return_value=httpx.Response(200, content=b"x" * 4096, headers={"content-length": "10"})
    )
    with pytest.raises(ResponseTooLargeError):
        fetch("https://news.example.com/liar")


# --- Errors ----------------------------------------------------------------


@respx.mock
def test_http_error_status_raises_fetch_error(dns):
    dns["news.example.com"] = [PUBLIC]
    respx.get("https://news.example.com/gone").mock(return_value=httpx.Response(404))
    with pytest.raises(FetchError, match="404"):
        fetch("https://news.example.com/gone")


@respx.mock
def test_transport_error_raises_fetch_error(dns):
    dns["news.example.com"] = [PUBLIC]
    respx.get("https://news.example.com/rss").mock(side_effect=httpx.ConnectTimeout("slow"))
    with pytest.raises(FetchError, match="transport error"):
        fetch("https://news.example.com/rss")


def test_blocked_url_never_reaches_the_network(dns):
    """AC-3: blocked before transmission. respx asserts no request was made —
    if the guard ran after connecting, this passes silently and the test fails
    to catch it, so the assertion is on the route, not on the exception alone."""
    dns["evil.test"] = ["127.0.0.1"]
    with respx.mock:
        route = respx.get("http://evil.test/")
        with pytest.raises(BlockedURLError):
            fetch("http://evil.test/")
        assert not route.called
