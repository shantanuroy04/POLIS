"""The single guarded egress point. ⟵ FR-1.4, FR-1.12, FR-1.13, SEC-12, TRD §5.2

Nothing in POLIS makes an outbound request except through :func:`fetch`. That is
what makes SEC-12 auditable: there is one place to read, not one per adapter.

Four controls live here, and each exists because of a specific failure:

* **Redirects are followed manually.** ``httpx`` would happily follow a 302 from
  a public host to ``169.254.169.254``, and the guard would never see it. Every
  hop is re-validated, capped at three.
* **The size cap is enforced while streaming.** ``Content-Length`` is a claim by
  the server, and a decompression bomb does not declare itself. The body is read
  in chunks and abandoned the moment it crosses the limit ⟵ SEC-13.
* **Per-domain pacing**, so POLIS stays a polite crawler ⟵ FR-1.4.
* **A truthful User-Agent** identifying the project, per the ethics position in
  PRD §10.
"""

from __future__ import annotations

import threading
import time
from urllib.parse import urlparse

import httpx

from backend.config import get_settings
from ingestion.url_guard import BlockedURLError, assert_url_allowed

MAX_REDIRECTS = 3

# FR-1.4 politeness. One request per domain per second is far below anything a
# news site would notice, and POLIS polls a handful of feeds every 10 minutes.
MIN_SECONDS_BETWEEN_REQUESTS = 1.0

_CHUNK_BYTES = 64 * 1024


class FetchError(RuntimeError):
    """A fetch failed for a reason that is not a security refusal.

    Distinct from BlockedURLError on purpose: a blocked URL is a permanent
    configuration error, while this is transient and may be retried.
    """


class ResponseTooLargeError(FetchError):
    """The body exceeded the configured cap and was abandoned mid-stream."""


class TooManyRedirectsError(FetchError):
    """More than MAX_REDIRECTS hops. Usually a loop, occasionally an attempt to
    tire the guard out across many hops."""


class _DomainPacer:
    """Smallest thing that keeps POLIS polite: last-request time per host.

    ponytail: in-process and in-memory. Correct today because TRD §6.2 runs
    exactly one scheduler in one process; if POLIS ever runs two, this silently
    doubles the request rate. A shared token bucket in PostgreSQL is the upgrade,
    and it is not needed until the deployment topology changes.
    """

    def __init__(self, min_interval: float = MIN_SECONDS_BETWEEN_REQUESTS) -> None:
        self._min_interval = min_interval
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, host: str) -> None:
        with self._lock:
            now = time.monotonic()
            earliest = self._last.get(host, 0.0) + self._min_interval
            delay = earliest - now
            # The slot is claimed inside the lock so two threads targeting the
            # same host queue up instead of both sleeping and then colliding.
            self._last[host] = max(now, earliest)
        if delay > 0:
            time.sleep(delay)


_pacer = _DomainPacer()


def _read_capped(response: httpx.Response, max_bytes: int) -> bytes:
    """Read the body, giving up as soon as it crosses max_bytes.

    iter_bytes yields decompressed data, so this caps the decompressed size —
    which is the size that matters for a gzip bomb.
    """
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes(_CHUNK_BYTES):
        total += len(chunk)
        if total > max_bytes:
            raise ResponseTooLargeError(
                f"response exceeded {max_bytes} bytes; aborted after {total}"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def fetch(url: str, *, timeout: float | None = None) -> bytes:
    """Fetch a URL through every SEC-12 control. Returns the body, ≤ the cap.

    Raises BlockedURLError before any connection is made when the URL, or any
    redirect target, fails the guard ⟵ AC-3.
    """
    settings = get_settings()
    timeout = settings.ingest_timeout_seconds if timeout is None else timeout
    max_bytes = settings.ingest_max_bytes

    headers = {
        "User-Agent": settings.ingest_user_agent,
        # Explicit, so the size cap below is capping something we asked for.
        "Accept-Encoding": "gzip, deflate",
    }

    current = url
    with httpx.Client(
        follow_redirects=False,
        timeout=timeout,
        headers=headers,
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            # Re-validated on every hop, not just the first. A public host that
            # 302s to a private one is the vector this defeats.
            assert_url_allowed(current)

            host = urlparse(current).hostname or ""
            _pacer.wait(host)

            try:
                with client.stream("GET", current) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise FetchError(f"{response.status_code} with no Location header")
                        # Relative redirects are normal; resolve against the URL
                        # we actually requested before re-validating.
                        current = str(response.url.join(location))
                        continue

                    response.raise_for_status()
                    return _read_capped(response, max_bytes)
            except httpx.HTTPStatusError as exc:
                raise FetchError(f"{exc.response.status_code} from {current}") from exc
            except httpx.HTTPError as exc:
                raise FetchError(f"transport error for {current}: {exc}") from exc

    raise TooManyRedirectsError(f"more than {MAX_REDIRECTS} redirects from {url}")


__all__ = [
    "BlockedURLError",
    "FetchError",
    "ResponseTooLargeError",
    "TooManyRedirectsError",
    "fetch",
]
