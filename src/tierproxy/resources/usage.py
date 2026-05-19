from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, cast

import httpx
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from tierproxy.async_client import AsyncTierProxy
    from tierproxy.client import TierProxy


class UsageDay(BaseModel):
    """Single-day bandwidth and cost breakdown within a ``Usage`` report.

    Each item in ``Usage.days`` represents one UTC calendar day. Days with no
    traffic are omitted from the list rather than returned as zero rows.
    """

    date: str = Field(
        description=(
            "UTC calendar date in ISO-8601 format (e.g. '2026-05-18'). Matches the"
            " date field used in gateway DynamoDB USAGE# sort-key prefixes."
        )
    )
    bytes_up: int = Field(
        description=(
            "Bytes sent from the client to the upstream (request bodies, headers,"
            " CONNECT overhead) on this day."
        )
    )
    bytes_down: int = Field(
        description=(
            "Bytes received by the client from the upstream (response bodies, headers) on this day."
        )
    )
    cost_usd: float = Field(
        description=(
            "Estimated cost in USD for this day's traffic, based on the plan's"
            " per-GB rate. Informational; billing is reconciled server-side."
        )
    )


class Usage(BaseModel):
    """Month-to-date (or range-scoped) usage aggregate from ``/v1/usage/me``.

    Returned by :meth:`UsageResource.get`. The ``days`` list gives per-day
    breakdowns; ``total_bytes`` and ``total_cost_usd`` are the sum across the
    requested window. The server computes these from DynamoDB USAGE# rows; the
    window defaults to the current calendar month if ``from``/``to`` are omitted.
    """

    model_config = ConfigDict(populate_by_name=True)

    client_id: str = Field(
        description=("Account identifier the usage belongs to. Matches :attr:`Me.client_id`.")
    )
    from_: str = Field(
        default="",
        alias="from",
        description=(
            "Start of the reporting window, ISO-8601 date (e.g. '2026-05-01')."
            " Empty string when the gateway defaults to the start of the current month."
        ),
    )
    to: str = Field(
        description=(
            "End of the reporting window, ISO-8601 date (inclusive). Typically today's"
            " UTC date when the window is the current month."
        )
    )
    days: list[UsageDay] = Field(
        description=(
            "Per-day breakdown within the window. Days with zero traffic are omitted."
            " Ordered chronologically."
        )
    )
    total_bytes: int = Field(
        description=(
            "Sum of ``bytes_up + bytes_down`` across all days in the window. Use this"
            " to gauge remaining quota against :attr:`Me.quota_bytes_month`."
        )
    )
    total_cost_usd: float = Field(
        description=(
            "Estimated total cost in USD for the window. Informational; billing is"
            " reconciled server-side."
        )
    )


class UsageDelta(BaseModel):
    """Single event emitted by the ``/v1/usage/me/stream`` SSE feed.

    Each event represents an incremental bandwidth chunk flushed by the gateway
    flusher (every ~10 s). Consume via :meth:`UsageResource.stream`.
    """

    ts: str = Field(
        description=(
            "ISO-8601 UTC timestamp of the flush event (e.g. '2026-05-18T12:00:10Z')."
            " Use to order or deduplicate events when reconnecting the stream."
        )
    )
    total_bytes: int = Field(
        description=(
            "Cumulative bytes consumed month-to-date at the time of this flush."
            " Monotonically increasing within a calendar month."
        )
    )
    delta_bytes: int = Field(
        description=(
            "Bytes added since the previous flush event. Zero if no traffic occurred"
            " in the interval. Never negative."
        )
    )


class UsageResource:
    """Bandwidth usage endpoint. Access via ``client.usage``.

    Provides both a one-shot snapshot (``get``) and a live SSE stream
    (``stream``) for real-time quota monitoring.
    """

    def __init__(self, client: TierProxy) -> None:
        self._client = client

    def get(self, *, from_: str | None = None, to: str | None = None) -> Usage:
        """Fetch a bandwidth usage aggregate for the authenticated account.

        Args:
            from_: Start date (ISO-8601, e.g. ``'2026-05-01'``). Defaults to
                the first day of the current UTC calendar month.
            to: End date (ISO-8601, inclusive). Defaults to today's UTC date.

        Returns:
            A :class:`Usage` instance with per-day breakdowns and totals.

        Raises:
            AuthenticationError: API key invalid or revoked (HTTP 401).
            ServerError: Gateway internal error (HTTP 5xx).

        Example:
            >>> with TierProxy() as g:  # doctest: +SKIP
            ...     u = g.usage.get()
            ...     print(f"{u.total_bytes:,} bytes used this month")
        """
        params = {k: v for k, v in {"from": from_, "to": to}.items() if v}
        data = self._client._transport.request("GET", "/v1/usage/me", params=params)
        return Usage.model_validate(data)

    def stream(self) -> Iterator[UsageDelta]:
        """Iterate live usage_delta events from the SSE stream until the gateway closes.

        Yields one :class:`UsageDelta` per flush event (approximately every 10 s
        when traffic is flowing). The stream runs indefinitely; break or close
        when quota monitoring is no longer needed.

        Only ``usage_delta`` SSE events are yielded; other event types (e.g.
        keepalive pings) are silently skipped.

        Yields:
            :class:`UsageDelta` instances in chronological order.

        Raises:
            AuthenticationError: API key invalid or revoked (HTTP 401).
            ServerError: Gateway internal error (HTTP 5xx).

        Example:
            >>> with TierProxy() as g:  # doctest: +SKIP
            ...     for delta in g.usage.stream():
            ...         print(f"+{delta.delta_bytes} bytes at {delta.ts}")
            ...         if delta.total_bytes > 10_000_000:
            ...             break
        """
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
    """Async variant of :class:`UsageResource`. Access via ``async_client.usage``."""

    def __init__(self, client: AsyncTierProxy) -> None:
        self._client = client

    async def get(self, *, from_: str | None = None, to: str | None = None) -> Usage:
        """Fetch a bandwidth usage aggregate. See :meth:`UsageResource.get`."""
        params = {k: v for k, v in {"from": from_, "to": to}.items() if v}
        data = await self._client._transport.arequest("GET", "/v1/usage/me", params=params)
        return Usage.model_validate(data)

    async def stream(self) -> AsyncIterator[UsageDelta]:
        """Async SSE stream of usage_delta events. See :meth:`UsageResource.stream`."""
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
