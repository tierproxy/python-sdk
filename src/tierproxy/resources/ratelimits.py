from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from tierproxy.async_client import AsyncTierProxy
    from tierproxy.client import TierProxy


class RateLimitSuggestion(BaseModel):
    domain: str
    suggest_per_sec: float


class RateLimits(BaseModel):
    suggestions: list[RateLimitSuggestion]
    window_secs: int


class RateLimitsResource:
    def __init__(self, client: TierProxy) -> None:
        self._client = client

    def get(self) -> RateLimits:
        data = self._client._transport.request("GET", "/v1/rate-limits/me")
        return RateLimits.model_validate(data)


class AsyncRateLimitsResource:
    def __init__(self, client: AsyncTierProxy) -> None:
        self._client = client

    async def get(self) -> RateLimits:
        data = await self._client._transport.arequest("GET", "/v1/rate-limits/me")
        return RateLimits.model_validate(data)
