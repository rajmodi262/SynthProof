"""Service hardening: who may reach an open service, how fast, how much budget, which headers.

Added 2026-10-16 (W7). Each control is mapped to the threat it answers and the test that pins it
in docs/threat_model.md.

* TRUSTED NETWORK. With no API key configured the service used to answer anyone who could reach
  its port: upload a sensitive table, spend budget, read the ledger. Now an unauthenticated
  service refuses data and budget endpoints from outside its trusted network --
  `SYNTHPROOF_TRUSTED_NETWORK` = `loopback` (default: this machine only), `private` (adds
  RFC 1918 / link-local, what the Docker image sets, since the host reaches a container over a
  bridge), or `any` (explicit opt-out). Configuring a key lifts the restriction: then the key
  is the control.
* PER-PRINCIPAL BUDGETS. `SYNTHPROOF_BUDGETS="alice=10,bob=4,*=20"` caps the epsilon each
  principal may spend through this service (`*` is everyone else). A release whose requested
  epsilon would take the principal past its cap is refused before anything runs; the check uses
  the requested epsilon, which bounds the proved one from above. Spends are summed naively,
  an upper bound on the true composition, so the cap is conservative.
* RATE LIMITING. `SYNTHPROOF_RATE_LIMIT` releases/uploads per principal per minute. Default 30
  on a durable (file-backed) ledger and off on the in-memory demo, where the test suites and the
  live demo run releases back to back.
* SECURITY HEADERS on every response, and a Content-Security-Policy on the console.
"""

import ipaddress
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Mapping, Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

TRUSTED_NETWORKS = ("loopback", "private", "any")

_PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(n)
    for n in (
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",
        "fc00::/7",
        "fe80::/10",
    )
)

# Starlette's TestClient reports its client as the literal host "testclient": it only exists
# in-process, so it is treated as this machine.
_IN_PROCESS_TEST_CLIENT = "testclient"


def parse_budgets(raw: str) -> Dict[str, float]:
    """Parses "name=eps,name=eps,*=eps". A malformed value stops the service."""
    budgets: Dict[str, float] = {}
    for part in (p.strip() for p in raw.split(",")):
        if not part:
            continue
        name, sep, value = part.partition("=")
        name = name.strip()
        try:
            eps = float(value)
        except ValueError:
            eps = -1.0
        if not sep or not name or not eps > 0:
            raise ValueError(
                f"SYNTHPROOF_BUDGETS entry {part!r} is not of the form name=<eps > 0>."
            )
        budgets[name] = eps
    return budgets


def client_is_trusted(host: Optional[str], network: str) -> bool:
    if network == "any":
        return True
    if host is None:
        return False
    if host == _IN_PROCESS_TEST_CLIENT:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    # Listed explicitly: `ipaddress.is_private` also covers the documentation and benchmarking
    # ranges (198.51.100.0/24, 203.0.113.0/24, ...), which are not a local network.
    return network == "private" and any(ip in net for net in _PRIVATE_NETWORKS)


def enforce_trusted_network(request: Request, network: str) -> None:
    host = request.client.host if request.client else None
    if not client_is_trusted(host, network):
        raise HTTPException(
            status_code=403,
            detail=(
                "This service has no API key configured, so it only answers requests from its "
                f"trusted network ({network}). Set SYNTHPROOF_API_KEY or SYNTHPROOF_API_KEYS to "
                "serve other clients."
            ),
        )


def limit_key(request: Request, principal: str) -> str:
    """Rate-limit bucket: the authenticated principal, or the client address when anonymous."""
    if principal != "anonymous":
        return f"principal:{principal}"
    return f"client:{request.client.host if request.client else 'unknown'}"


def budget_for(budgets: Mapping[str, float], principal: str) -> Optional[float]:
    if principal in budgets:
        return budgets[principal]
    return budgets.get("*")


class RateLimiter:
    """A sliding one-minute window per key. Thread-safe; state is per app instance."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, now: Optional[float] = None) -> None:
        if self.per_minute <= 0:
            return
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= 60.0:
                hits.popleft()
            if len(hits) >= self.per_minute:
                retry = int(60.0 - (now - hits[0])) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit: {self.per_minute} per minute. Retry in {retry} s.",
                    headers={"Retry-After": str(retry)},
                )
            hits.append(now)


# The console is a static bundle served from this origin; it loads nothing from anywhere else
# (fonts are bundled, see web/). Inline style attributes are used by React, hence 'unsafe-inline'
# for styles only -- never for scripts.
CONSOLE_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; "
    "worker-src 'self' blob:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)
BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        for k, v in BASE_HEADERS.items():
            response.headers.setdefault(k, v)
        path = request.url.path
        # The console and its assets. Not /docs (Swagger loads from a CDN) and not the capsule
        # export, a self-contained HTML document with its verifier inline by design.
        if path == "/" or path.startswith("/assets/"):
            response.headers.setdefault("Content-Security-Policy", CONSOLE_CSP)
        return response
