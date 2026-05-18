"""Lazy cost attribution. First call to client.cost_for(resp) /
client.upstream_for(resp) triggers ONE batched fetch of /v1/usage/recent,
cached 30s. No per-request poll.

Pattern:
    resp = client.get("https://example.com")
    print(client.cost_for(resp))      # lazy fetch on first access
    print(client.upstream_for(resp))  # uses cache from first call
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx

    from tierproxy.async_client import AsyncTierProxy
    from tierproxy.client import TierProxy


class CostAttributor:
    """One per client instance. Caches recent tunnels for cache_ttl seconds."""

    def __init__(self, client: TierProxy, cache_ttl: float = 30.0) -> None:
        self._client = client
        self._cache: list[dict[str, Any]] | None = None
        self._fetched_at: float = 0.0
        self._ttl = cache_ttl

    def _refresh_if_stale(self) -> None:
        if self._cache is None or time.time() - self._fetched_at > self._ttl:
            try:
                recent = self._client.usage_recent.get()
                self._cache = [t.model_dump() for t in recent.tunnels]
                self._fetched_at = time.time()
            except Exception:  # noqa: BLE001 — telemetry must not break user code
                self._cache = []
                self._fetched_at = time.time()

    def cost_for(self, resp: httpx.Response) -> float | None:
        """Return cost_usd for the given response. Lazy fetch on first call."""
        self._refresh_if_stale()
        for t in reversed(self._cache or []):
            if t["target_host"] == resp.url.host:
                return float(t["cost_usd"])
        return None

    def upstream_for(self, resp: httpx.Response) -> str | None:
        """Return upstream_id for the given response. Lazy fetch on first call."""
        self._refresh_if_stale()
        for t in reversed(self._cache or []):
            if t["target_host"] == resp.url.host:
                return str(t["upstream_id"])
        return None


class AsyncCostAttributor:
    """Async variant. One per AsyncTierProxy."""

    def __init__(self, client: AsyncTierProxy, cache_ttl: float = 30.0) -> None:
        self._client = client
        self._cache: list[dict[str, Any]] | None = None
        self._fetched_at: float = 0.0
        self._ttl = cache_ttl

    async def _refresh_if_stale(self) -> None:
        if self._cache is None or time.time() - self._fetched_at > self._ttl:
            try:
                recent = await self._client.usage_recent.get()
                self._cache = [t.model_dump() for t in recent.tunnels]
                self._fetched_at = time.time()
            except Exception:  # noqa: BLE001 — telemetry must not break user code
                self._cache = []
                self._fetched_at = time.time()

    async def cost_for(self, resp: httpx.Response) -> float | None:
        await self._refresh_if_stale()
        for t in reversed(self._cache or []):
            if t["target_host"] == resp.url.host:
                return float(t["cost_usd"])
        return None

    async def upstream_for(self, resp: httpx.Response) -> str | None:
        await self._refresh_if_stale()
        for t in reversed(self._cache or []):
            if t["target_host"] == resp.url.host:
                return str(t["upstream_id"])
        return None
