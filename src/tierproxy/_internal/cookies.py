"""Per-session cookie persistence.

CookieJar stores one ``httpx.Cookies`` instance per ``session_id`` so callers
that pin a sticky session also get cookie continuity across requests. Cookies
are domain-scoped via the response URL host.

Thread-safety: a coarse ``threading.Lock`` guards the underlying dict. The
``httpx.Cookies`` objects themselves are not internally locked; for v0.2.0
concurrent writes to the same session_id from multiple threads are not
recommended. Single-thread / asyncio usage is safe.
"""

from __future__ import annotations

import threading
from collections import defaultdict

import httpx


class CookieJar:
    def __init__(self) -> None:
        self._jars: dict[str, httpx.Cookies] = defaultdict(httpx.Cookies)
        self._lock = threading.Lock()

    def get(self, session_id: str) -> httpx.Cookies:
        with self._lock:
            return self._jars[session_id]

    def update_from(self, session_id: str, resp: httpx.Response) -> None:
        """Merge cookies from ``resp`` into the jar for ``session_id``.

        Uses ``resp.url.host`` as the domain so cookies are scoped correctly
        across hosts sharing the same session pin.
        """
        host = resp.url.host or ""
        with self._lock:
            jar = self._jars[session_id]
            for name, value in resp.cookies.items():
                jar.set(name, value, domain=host)

    def clear(self, session_id: str | None = None) -> None:
        with self._lock:
            if session_id is None:
                self._jars.clear()
            else:
                self._jars.pop(session_id, None)

    def __contains__(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._jars
