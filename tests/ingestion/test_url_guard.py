"""SSRF guard tests. ⟵ AC-3, SEC-12, Implementation Plan task 2.2 ("blocks all 5 test vectors")

DNS is stubbed throughout. These tests must not depend on what a real resolver
says today, and a security test that needs the network is a security test that
gets skipped.
"""

from __future__ import annotations

import ipaddress
import socket

import pytest

from ingestion.url_guard import BlockedURLError, assert_url_allowed, is_blocked_address


def _stub_dns(monkeypatch, mapping: dict[str, list[str]]):
    """Point getaddrinfo at a fixed hostname -> addresses table."""

    def fake_getaddrinfo(host, *args, **kwargs):
        if host not in mapping:
            raise socket.gaierror(f"no stub for {host}")
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (addr, 0))
            for addr in mapping[host]
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


# --- The five vectors named in TRD §14.5 -----------------------------------


def test_blocks_loopback_v4(monkeypatch):
    _stub_dns(monkeypatch, {"evil.test": ["127.0.0.1"]})
    with pytest.raises(BlockedURLError, match="blocked address"):
        assert_url_allowed("http://evil.test/feed")


def test_blocks_cloud_metadata_endpoint(monkeypatch):
    _stub_dns(monkeypatch, {"meta.test": ["169.254.169.254"]})
    with pytest.raises(BlockedURLError, match="169.254.169.254"):
        assert_url_allowed("http://meta.test/latest/meta-data/")


def test_blocks_loopback_v6(monkeypatch):
    _stub_dns(monkeypatch, {"v6.test": ["::1"]})
    with pytest.raises(BlockedURLError, match="blocked address"):
        assert_url_allowed("http://v6.test/")


def test_blocks_public_name_that_resolves_internally(monkeypatch):
    """A perfectly ordinary hostname pointing at RFC1918. Nothing in the URL
    text gives this away — only resolution does."""
    _stub_dns(monkeypatch, {"news.example.com": ["10.0.0.5"]})
    with pytest.raises(BlockedURLError, match="10.0.0.5"):
        assert_url_allowed("https://news.example.com/rss")


def test_blocks_when_any_address_is_internal(monkeypatch):
    """One public A record and one loopback. Checking only the first result
    would let this through, which is why resolve_all exists."""
    _stub_dns(monkeypatch, {"split.test": ["93.184.216.34", "127.0.0.1"]})
    with pytest.raises(BlockedURLError, match="127.0.0.1"):
        assert_url_allowed("https://split.test/")


# --- Scheme, credentials, port ---------------------------------------------


@pytest.mark.parametrize("url", ["file:///etc/passwd", "gopher://x/", "ftp://x/", "//x/"])
def test_rejects_non_http_schemes(url):
    with pytest.raises(BlockedURLError, match="scheme"):
        assert_url_allowed(url)


def test_rejects_credentials_in_url(monkeypatch):
    _stub_dns(monkeypatch, {"news.example.com": ["93.184.216.34"]})
    with pytest.raises(BlockedURLError, match="credentials"):
        assert_url_allowed("https://user:pw@news.example.com/")


def test_rejects_non_standard_port(monkeypatch):
    _stub_dns(monkeypatch, {"news.example.com": ["93.184.216.34"]})
    with pytest.raises(BlockedURLError, match="port not allowed"):
        assert_url_allowed("http://news.example.com:8080/")


def test_rejects_unresolvable_host(monkeypatch):
    _stub_dns(monkeypatch, {})
    with pytest.raises(BlockedURLError, match="does not resolve"):
        assert_url_allowed("https://nope.test/")


def test_rejects_missing_hostname():
    with pytest.raises(BlockedURLError, match="hostname"):
        assert_url_allowed("http:///just-a-path")


# --- The unmapping bug this module exists to avoid --------------------------


def test_ipv4_mapped_loopback_is_blocked(monkeypatch):
    """::ffff:127.0.0.1 is loopback wearing a costume. IPv6Address.is_loopback
    is False for it, so without _unmap this passes every range check."""
    assert is_blocked_address(ipaddress.ip_address("::ffff:127.0.0.1"))
    _stub_dns(monkeypatch, {"mapped.test": ["::ffff:169.254.169.254"]})
    with pytest.raises(BlockedURLError, match="blocked address"):
        assert_url_allowed("http://mapped.test/")


@pytest.mark.parametrize(
    "addr",
    # S104 flags the "0.0.0.0" literal as a bind-to-all-interfaces smell. Here it
    # is the opposite: the test asserts that address is REFUSED.
    [
        "0.0.0.0",  # noqa: S104
        "10.1.2.3",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.1.1",
        "224.0.0.1",
        "fe80::1",
    ],
)
def test_blocked_ranges(addr):
    assert is_blocked_address(ipaddress.ip_address(addr))


@pytest.mark.parametrize("addr", ["93.184.216.34", "8.8.8.8", "2606:2800:220:1:248:1893:25c8:1946"])
def test_public_addresses_are_allowed(addr):
    assert not is_blocked_address(ipaddress.ip_address(addr))


def test_allows_a_normal_public_url(monkeypatch):
    _stub_dns(monkeypatch, {"news.example.com": ["93.184.216.34"]})
    assert_url_allowed("https://news.example.com/rss.xml")  # must not raise
