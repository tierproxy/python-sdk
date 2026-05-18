"""TTL-aware LRU response cache with max_response_size cap.

Responses larger than max_response_size are NOT cached (skipped silently).
Streaming responses (where .content is unavailable) are also skipped.
Prevents in-memory cache from blowing up on crawl workloads with large pages.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx


class ResponseCache:
    def __init__(
        self,
        max_size: int = 256,
        default_ttl: float = 300.0,
        max_response_size: int = 262144,  # 256 KB
    ) -> None:
        self._cache: OrderedDict[str, tuple[float, httpx.Response]] = OrderedDict()
        self._max = max_size
        self._default_ttl = default_ttl
        self._max_response_size = max_response_size

    @staticmethod
    def _key(method: str, url: str, params: dict[str, Any] | None) -> str:
        items = sorted((params or {}).items())
        return f"{method.upper()}|{url}|{items}"

    def get(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response | None:
        key = self._key(method, url, params)
        if key not in self._cache:
            return None
        expires, resp = self._cache[key]
        if time.time() > expires:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return resp

    def set(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None,
        resp: httpx.Response,
        ttl: float | None = None,
    ) -> bool:
        """Store entry; returns True if cached, False if skipped (too large / streaming / ttl<=0)."""
        eff_ttl = self._default_ttl if ttl is None else ttl
        if eff_ttl <= 0:
            return False
        try:
            body_len = len(resp.content)
        except Exception:  # noqa: BLE001 — streaming responses, treat as too large
            return False
        if body_len > self._max_response_size:
            return False

        key = self._key(method, url, params)
        self._cache[key] = (time.time() + eff_ttl, resp)
        self._cache.move_to_end(key)
        while len(self._cache) > self._max:
            self._cache.popitem(last=False)
        return True

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)
