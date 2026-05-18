from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, cast

import httpx
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from tierproxy.async_client import AsyncTierProxy
    from tierproxy.client import TierProxy


class UsageDay(BaseModel):
    date: str
    bytes_up: int
    bytes_down: int
    cost_usd: float


class Usage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    client_id: str
    from_: str = Field(default="", alias="from")
    to: str
    days: list[UsageDay]
    total_bytes: int
    total_cost_usd: float


class UsageDelta(BaseModel):
    ts: str
    total_bytes: int
    delta_bytes: int


class UsageResource:
    def __init__(self, client: TierProxy) -> None:
        self._client = client

    def get(self, *, from_: str | None = None, to: str | None = None) -> Usage:
        params = {k: v for k, v in {"from": from_, "to": to}.items() if v}
        data = self._client._transport.request("GET", "/v1/usage/me", params=params)
        return Usage.model_validate(data)

    def stream(self) -> Iterator[UsageDelta]:
        """Iterate live usage_delta events from the SSE stream until the gateway closes."""
        from tierproxy._internal.sse import iter_sse

        client = cast(httpx.Client, self._client._transport._client)
        with client.stream(
            "GET",
            self._client._transport.base_url + "/v1/usage/me/stream",
            headers=self._client._transport._headers(),
        ) as resp:
            resp.raise_for_status()
            for event in iter_sse(resp):
                if event.event == "usage_delta":
                    yield UsageDelta.model_validate_json(event.data)


class AsyncUsageResource:
    def __init__(self, client: AsyncTierProxy) -> None:
        self._client = client

    async def get(self, *, from_: str | None = None, to: str | None = None) -> Usage:
        params = {k: v for k, v in {"from": from_, "to": to}.items() if v}
        data = await self._client._transport.arequest("GET", "/v1/usage/me", params=params)
        return Usage.model_validate(data)

    async def stream(self) -> AsyncIterator[UsageDelta]:
        from tierproxy._internal.sse import aiter_sse

        client = cast(httpx.AsyncClient, self._client._transport._client)
        async with client.stream(
            "GET",
            self._client._transport.base_url + "/v1/usage/me/stream",
            headers=self._client._transport._headers(),
        ) as resp:
            resp.raise_for_status()
            async for event in aiter_sse(resp):
                if event.event == "usage_delta":
                    yield UsageDelta.model_validate_json(event.data)
