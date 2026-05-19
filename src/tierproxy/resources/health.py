from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from tierproxy.async_client import AsyncTierProxy
    from tierproxy.client import TierProxy


class UpstreamHealth(BaseModel):
    """Snapshot of one upstream's recent performance.

    Updated every minute server-side by a background health-check loop that
    records success rate and latency into DynamoDB ``HEALTH#<upstream>`` rows.
    Use to inform manual routing decisions or trigger alarms; do not rely on
    this for per-request routing — the gateway selector already uses EWMA
    latency and circuit-breaker state internally.
    """

    upstream_id: str = Field(
        description=(
            "Stable identifier for the upstream provider (e.g. 'decodo', 'iproyal')."
            " Matches the IDs returned in :attr:`Me.allowed_upstreams`."
        )
    )
    state: str = Field(
        description=(
            "Operational state of the upstream: 'active' | 'paused' | 'disabled'."
            " 'paused' means the upstream is temporarily excluded from routing by"
            " the gateway operator; 'disabled' means it has been removed from the"
            " pool entirely."
        )
    )
    cb_state: str = Field(
        description=(
            "Circuit-breaker state: 'closed' (normal), 'open' (upstream skipped after"
            " repeated failures), or 'half_open' (trial request allowed after 30 s)."
            " When 'open', the selector excludes this upstream entirely."
        )
    )
    success_rate: float = Field(
        description=(
            "Fraction of proxy requests that succeeded (HTTP 200 CONNECT) over the"
            " last measurement window, in the range [0.0, 1.0]. Values below ~0.9"
            " typically indicate upstream instability."
        )
    )
    latency_p95_ms: int = Field(
        description=(
            "95th-percentile CONNECT round-trip latency in milliseconds over the last"
            " measurement window. Used by the gateway's Power-of-Two-Choices selector"
            " (via EWMA); exposed here for observability."
        )
    )
    cost_per_gb_usd: float = Field(
        description=(
            "Upstream provider's effective cost per gigabyte in USD, as configured in"
            " the gateway. Used for cost attribution in usage reports."
        )
    )


class HealthResource:
    """Upstream health endpoint. Access via ``client.health``.

    Returns the latest performance snapshot for every upstream the gateway
    knows about (not limited to the caller's plan). Useful for monitoring
    dashboards and automated alerting.
    """

    def __init__(self, client: TierProxy) -> None:
        self._client = client

    def upstreams(self) -> list[UpstreamHealth]:
        """Fetch the latest health snapshot for all known upstreams.

        Returns:
            A list of :class:`UpstreamHealth` instances, one per upstream.
            Order is not guaranteed.

        Raises:
            AuthenticationError: API key invalid or revoked (HTTP 401).
            ServerError: Gateway internal error (HTTP 5xx).

        Example:
            >>> with TierProxy() as g:  # doctest: +SKIP
            ...     for h in g.health.upstreams():
            ...         if h.cb_state == "open":
            ...             print(f"WARNING: {h.upstream_id} circuit breaker open")
        """
        data = self._client._transport.request("GET", "/v1/health/upstreams")
        return [UpstreamHealth.model_validate(u) for u in data.get("upstreams", [])]


class AsyncHealthResource:
    """Async variant of :class:`HealthResource`. Access via ``async_client.health``."""

    def __init__(self, client: AsyncTierProxy) -> None:
        self._client = client

    async def upstreams(self) -> list[UpstreamHealth]:
        """Fetch the latest health snapshot for all known upstreams.

        See :meth:`HealthResource.upstreams`.
        """
        data = await self._client._transport.arequest("GET", "/v1/health/upstreams")
        return [UpstreamHealth.model_validate(u) for u in data.get("upstreams", [])]
