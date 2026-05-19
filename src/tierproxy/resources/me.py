from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from tierproxy.async_client import AsyncTierProxy
    from tierproxy.client import TierProxy


class Me(BaseModel):
    """Identity and quota snapshot for the authenticated API key.

    Returned by ``client.me.get()``. Reflects the state of the client account
    at the time of the call — not cached unless the SDK was constructed with
    ``cache_ttl > 0``.
    """

    client_id: str = Field(
        description=(
            "Stable account identifier (e.g. 'client_a3f8...'). Use as your join key"
            " when correlating SDK calls with gateway logs."
        )
    )
    plan_id: str = Field(
        description=(
            "Current plan slug (e.g. 'starter', 'pro'). Determines quota, rate, and"
            " allowed upstreams."
        )
    )
    status: str = Field(
        description=(
            "Account status: 'active' | 'suspended' | 'past_due'. Suspended keys"
            " return 403 on proxy requests."
        )
    )
    quota_bytes_month: int = Field(
        description=(
            "Monthly egress quota in bytes. Resets on the first UTC day of each calendar month."
        )
    )
    used_bytes_month: int = Field(
        description=(
            "Bytes consumed month-to-date (request + response, both directions)."
            " Updated server-side; SDK does not buffer."
        )
    )
    allowed_upstreams: list[str] = Field(
        description=(
            "Upstream provider IDs the plan can route through (e.g. ['decodo',"
            " 'iproyal']). Subset of all known upstreams."
        )
    )
    rate_per_sec: float = Field(
        default=0,
        description=("Soft request-rate limit per second. 0 means unmetered (enterprise plans)."),
    )
    bytes_per_sec: float = Field(
        default=0,
        description="Soft bandwidth limit in bytes/second. 0 means unmetered.",
    )

    @property
    def remaining_bytes(self) -> int:
        """Bytes still available this month. Never negative."""
        return max(0, self.quota_bytes_month - self.used_bytes_month)


class MeResource:
    """Account-identity endpoint. Access via ``client.me``.

    Cheap (server-side cached ~5 s), safe to call before every job to confirm
    the key is still active and quota has not been exhausted.
    """

    def __init__(self, client: TierProxy) -> None:
        self._client = client

    def get(self) -> Me:
        """Fetch the current account snapshot.

        Returns:
            A :class:`Me` instance with quota and identity fields populated.

        Raises:
            AuthenticationError: API key invalid or revoked (HTTP 401).
            PermissionError: Account suspended (HTTP 403).
            ServerError: Gateway internal error (HTTP 5xx).

        Example:
            >>> with TierProxy() as g:  # doctest: +SKIP
            ...     me = g.me.get()
            ...     assert me.remaining_bytes > 0, "quota exhausted"
        """
        data = self._client._transport.request("GET", "/v1/me")
        return Me.model_validate(data)


class AsyncMeResource:
    """Async variant of :class:`MeResource`. Access via ``async_client.me``."""

    def __init__(self, client: AsyncTierProxy) -> None:
        self._client = client

    async def get(self) -> Me:
        """Fetch the current account snapshot. See :meth:`MeResource.get`."""
        data = await self._client._transport.arequest("GET", "/v1/me")
        return Me.model_validate(data)
