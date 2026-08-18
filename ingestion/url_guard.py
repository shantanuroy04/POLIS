"""SSRF defence for every outbound fetch. ⟵ SEC-12, FR-1.13, TRD §14.5

This module is a security control, not a utility. Ingestion fetches
attacker-influenceable URLs by design — a feed entry can link anywhere — so the
only thing standing between POLIS and the cloud metadata endpoint is this file.

Read TRD §14.5 before changing anything here. In particular:

* Every address a hostname resolves to is checked, not just the first. A
  hostname with one public and one loopback A record must be refused.
* IPv4-mapped IPv6 (``::ffff:127.0.0.1``) is unmapped before the check. Without
  that step it reads as an ordinary IPv6 address and sails through.
* Redirects are NOT this module's job to follow, but each hop must be passed
  back through :func:`assert_url_allowed` — see ``http_client``.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# The explicit list from TRD §14.5. The property checks below (is_private and
# friends) already cover most of these; both are kept deliberately, because the
# named ranges document intent and the property checks catch what a hand-written
# list forgets.
BLOCKED_NETS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = tuple(
    ipaddress.ip_network(n)
    for n in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "127.0.0.0/8",
        "169.254.0.0/16",  # link-local, and 169.254.169.254 is cloud metadata
        "172.16.0.0/12",
        "192.168.0.0/16",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
        # These two embed an IPv4 address inside an IPv6 one. Rather than decode
        # and re-check them, refuse outright — no legitimate news source needs
        # 6to4 or NAT64, so the parsing risk buys nothing.
        "2002::/16",
        "64:ff9b::/96",
    )
)

ALLOWED_SCHEMES = frozenset({"http", "https"})

# TRD §14.5 marks the port restriction [PROPOSED]. It is implemented because the
# cost is one comparison and the alternative is letting a source URL reach an
# internal service on a high port that happens to resolve publicly.
ALLOWED_PORTS = frozenset({80, 443})

DEFAULT_PORTS = {"http": 80, "https": 443}


class BlockedURLError(ValueError):
    """Raised before any network call is made.

    Callers must treat this as a configuration error on the source, not a
    transient fetch failure: retrying cannot help, and TRD §11 requires the
    source be marked ``config_error`` rather than retried.
    """


def _unmap(ip: ipaddress.IPv4Address | ipaddress.IPv6Address):
    """Return the IPv4 address hiding inside an IPv6 one, if there is one.

    ``::ffff:127.0.0.1`` is loopback wearing a costume. ``IPv6Address.is_loopback``
    is False for it, so without this step the range checks below never fire.
    """
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def is_blocked_address(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True if this resolved address must not be connected to."""
    ip = _unmap(ip)
    if any(ip in net for net in BLOCKED_NETS):
        return True
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def resolve_all(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Every address the hostname currently maps to, v4 and v6.

    Raises BlockedURLError when the name does not resolve. A source we cannot
    resolve is a source we must not fetch, and failing closed is the whole point.
    """
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise BlockedURLError(f"hostname does not resolve: {hostname}") from exc

    addresses = []
    for *_, sockaddr in infos:
        addresses.append(ipaddress.ip_address(sockaddr[0]))
    if not addresses:
        raise BlockedURLError(f"hostname resolved to nothing: {hostname}")
    return addresses


def assert_url_allowed(url: str) -> None:
    """Refuse the URL unless it is safe to connect to. ⟵ AC-3

    Checks, in order: scheme, embedded credentials, hostname presence, port, and
    every resolved address. Order matters only in that the cheap textual checks
    run before the DNS lookup.

    ponytail: there is a TOCTOU window between this resolution and the one httpx
    performs when it connects — classic DNS rebinding. Closing it properly means
    connecting to a pinned IP and carrying the original Host header, which breaks
    TLS SNI verification unless handled carefully. Not worth it at this scale
    against public news feeds; revisit if POLIS ever fetches user-submitted URLs
    on demand. The window is documented in DOC-009 rather than left implicit.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise BlockedURLError(f"scheme not allowed: {parsed.scheme or '(none)'}")

    # http://attacker@internal/ is a real phishing and parser-confusion vector,
    # and no feed needs credentials in the URL.
    if parsed.username or parsed.password:
        raise BlockedURLError("credentials in URL are not allowed")

    hostname = parsed.hostname
    if not hostname:
        raise BlockedURLError("missing hostname")

    try:
        port = parsed.port
    except ValueError as exc:  # malformed port, e.g. http://host:notaport/
        raise BlockedURLError(f"invalid port in URL: {url}") from exc

    if port is None:
        port = DEFAULT_PORTS[parsed.scheme]
    if port not in ALLOWED_PORTS:
        raise BlockedURLError(f"port not allowed: {port}")

    for ip in resolve_all(hostname):
        if is_blocked_address(ip):
            raise BlockedURLError(f"{hostname} resolves to blocked address: {ip}")
