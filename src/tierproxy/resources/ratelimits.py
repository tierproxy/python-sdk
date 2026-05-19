from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from tierproxy.async_client import AsyncTierProxy
    from tierproxy.client import TierProxy


class RateLimitSuggestion(BaseModel):
    """Per-domain rate-limit suggestion derived from the gateway's learning mode.

    The gateway observes success/failure ratios per target domain and emits
    suggestions when it detects that the current request rate is triggering
    upstream defenses. A lower ``suggest_per_sec`` indicates the domain is
    more aggressively rate-protecting.
    """

    domain: str = Field(
        description=(
            "Target domain the suggestion applies to (e.g. 'example.com')."
            " Matched against the ``host`` component of CONNECT requests."
        )
    )
    suggest_per_sec: float = Field(
        description=(
            "Suggested maximum request rate in requests per second for this domain."
            " Derived from observed upstream error signals during the learning window."
            " 0.0 means the gateway has insufficient data to make a recommendation."
        )
    )


class RateLimits(BaseModel):
    """Rate-limit recommendations from ``/v1/rate-limits/me``.

    The gateway runs a learning-mode observer that tracks per-domain success
    rates over a rolling ``window_secs`` window. When error signals indicate
    that upstream providers are throttling requests, the gateway emits
    per-domain suggestions. These are advisory — the SDK does not enforce
    them automatically.
    """

    suggestions: list[RateLimitSuggestion] = Field(
        description=(
            "Per-domain rate-limit suggestions. Empty list means no domains have"
            " triggered learning-mode signals in the current window."
        )
    )
    window_secs: int = Field(
        description=(
            "Duration in seconds of the rolling observation window used to compute"
            " suggestions. Typically 60–300 s. Suggestions are recomputed each time"
            " the window slides."
        )
    )


class RateLimitsResource:
    """Rate-limit recommendations endpoint. Access via ``client.rate_limits``.

    Call this before starting a high-volume scrape job to retrieve any
    domain-level throttling signals the gateway has observed during the
    current observation window.
    """

    def __init__(self, client: TierProxy) -> None:
        self._client = client

    def get(self) -> RateLimits:
        """Fetch current rate-limit suggestions for the authenticated account.

        Returns:
            A :class:`RateLimits` instance with per-domain suggestions and
            the observation window duration.

        Raises:
            AuthenticationError: API key invalid or revoked (HTTP 401).
            ServerError: Gateway internal error (HTTP 5xx).

        Example:
            >>> with TierProxy() as g:  # doctest: +SKIP
            ...     rl = g.rate_limits.get()
            ...     for s in rl.suggestions:
            ...         print(f"{s.domain}: max {s.suggest_per_sec:.1f} rps")
        """
        data = self._client._transport.request("GET", "/v1/rate-limits/me")
        return RateLimits.model_validate(data)


class AsyncRateLimitsResource:
    """Async variant of :class:`RateLimitsResource`. Access via ``async_client.rate_limits``."""

    def __init__(self, client: AsyncTierProxy) -> None:
        self._client = client

    async def get(self) -> RateLimits:
        """Fetch current rate-limit suggestions. See :meth:`RateLimitsResource.get`."""
        data = await self._client._transport.arequest("GET", "/v1/rate-limits/me")
        return RateLimits.model_validate(data)
