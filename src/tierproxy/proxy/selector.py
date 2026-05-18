"""Client-side smart selector. Reads /v1/health/upstreams + picks one
based on cost / latency / success-rate, then emits an upstream-hint."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from tierproxy.async_client import AsyncTierProxy
    from tierproxy.client import TierProxy
    from tierproxy.resources.health import UpstreamHealth

Strategy = Literal["cheapest", "fastest", "most_reliable", "balanced"]


def pick(upstreams: list[UpstreamHealth], strategy: Strategy = "balanced") -> UpstreamHealth:
    """Pick the best upstream by strategy. Excludes red/open ones.

    'balanced' = weighted score (success_rate / cost / latency).
    """
    candidates = [u for u in upstreams if u.state != "red" and u.cb_state != "open"]
    if not candidates:
        if not upstreams:
            raise ValueError("No upstreams available")
        return max(upstreams, key=lambda u: u.success_rate)

    if strategy == "cheapest":
        return min(candidates, key=lambda u: u.cost_per_gb_usd)
    if strategy == "fastest":
        return min(candidates, key=lambda u: u.latency_p95_ms)
    if strategy == "most_reliable":
        return max(candidates, key=lambda u: u.success_rate)

    def score(u: UpstreamHealth) -> float:
        denom = max(0.01, u.cost_per_gb_usd) * (1 + u.latency_p95_ms / 1000)
        return u.success_rate / denom

    return max(candidates, key=score)


def pick_next(
    upstreams: list[UpstreamHealth],
    exclude: set[str],
    strategy: Strategy = "balanced",
) -> UpstreamHealth | None:
    """Pick the best upstream excluding tried IDs. Returns None if exhausted."""
    remaining = [u for u in upstreams if u.upstream_id not in exclude]
    if not remaining:
        return None
    return pick(remaining, strategy)


class SmartSelector:
    """Convenience: keeps a cached health snapshot, refreshes every N seconds."""

    def __init__(
        self,
        client: TierProxy,
        strategy: Strategy = "balanced",
        cache_ttl: float = 30.0,
    ) -> None:
        self._client = client
        self._strategy: Strategy = strategy
        self._ttl = cache_ttl
        self._cache: list[UpstreamHealth] | None = None
        self._fetched_at: float = 0.0

    def _refresh_if_stale(self) -> list[UpstreamHealth]:
        if not self._cache or time.time() - self._fetched_at > self._ttl:
            self._cache = self._client.health.upstreams()
            self._fetched_at = time.time()
        return self._cache

    def pick(self) -> UpstreamHealth:
        return pick(self._refresh_if_stale(), self._strategy)

    def pick_next(self, exclude: set[str]) -> UpstreamHealth | None:
        return pick_next(self._refresh_if_stale(), exclude, self._strategy)


class AsyncSmartSelector:
    def __init__(
        self,
        client: AsyncTierProxy,
        strategy: Strategy = "balanced",
        cache_ttl: float = 30.0,
    ) -> None:
        self._client = client
        self._strategy: Strategy = strategy
        self._ttl = cache_ttl
        self._cache: list[UpstreamHealth] | None = None
        self._fetched_at: float = 0.0

    async def _refresh_if_stale(self) -> list[UpstreamHealth]:
        if not self._cache or time.time() - self._fetched_at > self._ttl:
            self._cache = await self._client.health.upstreams()
            self._fetched_at = time.time()
        return self._cache

    async def pick(self) -> UpstreamHealth:
        return pick(await self._refresh_if_stale(), self._strategy)

    async def pick_next(self, exclude: set[str]) -> UpstreamHealth | None:
        return pick_next(await self._refresh_if_stale(), exclude, self._strategy)
