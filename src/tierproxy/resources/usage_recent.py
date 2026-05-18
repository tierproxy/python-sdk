from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from tierproxy.async_client import AsyncTierProxy
    from tierproxy.client import TierProxy


class Tunnel(BaseModel):
    client_id: str = ""
    upstream_id: str
    target_host: str
    bytes_up: int
    bytes_down: int
    cost_usd: float
    duration_ms: int
    timestamp: str
    status_code: int


class UsageRecent(BaseModel):
    tunnels: list[Tunnel]
    ts: str


class UsageRecentResource:
    def __init__(self, client: TierProxy) -> None:
        self._client = client

    def get(self) -> UsageRecent:
        data = self._client._transport.request("GET", "/v1/usage/recent")
        return UsageRecent.model_validate(data)


class AsyncUsageRecentResource:
    def __init__(self, client: AsyncTierProxy) -> None:
        self._client = client

    async def get(self) -> UsageRecent:
        data = await self._client._transport.arequest("GET", "/v1/usage/recent")
        return UsageRecent.model_validate(data)
