from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from tierproxy.async_client import AsyncTierProxy
    from tierproxy.client import TierProxy


class Me(BaseModel):
    client_id: str
    plan_id: str
    status: str
    quota_bytes_month: int
    used_bytes_month: int
    allowed_upstreams: list[str]
    rate_per_sec: float = 0
    bytes_per_sec: float = 0

    @property
    def remaining_bytes(self) -> int:
        return max(0, self.quota_bytes_month - self.used_bytes_month)


class MeResource:
    def __init__(self, client: TierProxy) -> None:
        self._client = client

    def get(self) -> Me:
        data = self._client._transport.request("GET", "/v1/me")
        return Me.model_validate(data)


class AsyncMeResource:
    def __init__(self, client: AsyncTierProxy) -> None:
        self._client = client

    async def get(self) -> Me:
        data = await self._client._transport.arequest("GET", "/v1/me")
        return Me.model_validate(data)
