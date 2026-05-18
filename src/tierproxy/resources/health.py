from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from tierproxy.async_client import AsyncTierProxy
    from tierproxy.client import TierProxy


class UpstreamHealth(BaseModel):
    upstream_id: str
    state: str
    cb_state: str
    success_rate: float
    latency_p95_ms: int
    cost_per_gb_usd: float


class HealthResource:
    def __init__(self, client: TierProxy) -> None:
        self._client = client

    def upstreams(self) -> list[UpstreamHealth]:
        data = self._client._transport.request("GET", "/v1/health/upstreams")
        return [UpstreamHealth.model_validate(u) for u in data.get("upstreams", [])]


class AsyncHealthResource:
    def __init__(self, client: AsyncTierProxy) -> None:
        self._client = client

    async def upstreams(self) -> list[UpstreamHealth]:
        data = await self._client._transport.arequest("GET", "/v1/health/upstreams")
        return [UpstreamHealth.model_validate(u) for u in data.get("upstreams", [])]
