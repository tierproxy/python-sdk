"""Public exception hierarchy. Every exception carries request_id for support."""

from __future__ import annotations

from typing import Any


class TierProxyError(Exception):
    """Base class for every error raised by the SDK.

    Catch this when you want a single ``except`` to cover any failure. For
    granular handling, catch one of the subclasses below.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status from the gateway (None for client-side
            failures like :exc:`ConnectionError`).
        request_id: Gateway-issued request ID for support escalation. Always
            include this when filing a ticket.
        error_type: RFC 7807 ``type`` URI from the problem+json body.
        problem: Raw RFC 7807 dict (``type``, ``title``, ``detail``,
            ``instance``, plus any extensions).
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
        error_type: str | None = None,
        problem: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        self.error_type = error_type
        self.problem = problem or {}

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(message={self.message!r}, "
            f"status_code={self.status_code}, request_id={self.request_id!r})"
        )


class AuthenticationError(TierProxyError):
    """HTTP 401. API key missing, malformed, or revoked.

    Remedy: confirm ``TIERPROXY_API_KEY`` is set or pass ``api_key=`` to the
    client. Keys revoked by support cannot be reused — issue a new one in
    the dashboard.
    """


class PermissionError(TierProxyError):  # noqa: A001
    """HTTP 403. The account is suspended or the request hit a feature
    not enabled for the current plan.

    Remedy: inspect ``problem['detail']`` for the gating reason
    (suspension vs feature flag) and upgrade the plan or contact billing.
    """


class NotFoundError(TierProxyError):
    """HTTP 404. The requested control-plane resource does not exist.

    Most commonly raised on a typo in an upstream_id passed to
    ``client.health.get(upstream_id=...)``. Not raised on 404s from
    proxied target sites — those return a normal ``httpx.Response`` with
    ``status_code == 404``.
    """


class ValidationError(TierProxyError):
    """HTTP 400. The request body or query parameters failed gateway
    validation.

    Remedy: inspect ``problem['detail']`` for the offending field. The
    SDK already validates locally with Pydantic before sending, so a 400
    typically indicates a server-side rule the SDK does not enforce
    (e.g. country code not in the plan's allowed list).
    """


class ConflictError(TierProxyError):
    """HTTP 409. The request conflicts with current account state.

    Example: deleting an upstream that is still bound to an active rule.
    """


class RateLimitError(TierProxyError):
    """HTTP 429. The plan's rate-per-second or bytes-per-second limit
    was exceeded.

    Attributes:
        retry_after: Seconds the gateway recommends waiting before
            retrying. Sourced from the ``Retry-After`` header. None when
            the header is absent.

    Remedy: respect ``retry_after`` (the SDK's default retry policy does
    this automatically); for sustained traffic, request a plan upgrade
    or enable smart routing across more upstreams.
    """

    def __init__(self, *args: Any, retry_after: int | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


class ServerError(TierProxyError):
    """HTTP 5xx. Gateway internal error.

    The default retry policy retries 500/502/503/504 with backoff. If
    the error survives, the gateway is unhealthy — check
    status.tierproxy.com.
    """


class TimeoutError(TierProxyError):  # noqa: A001
    """The request did not complete within ``timeout`` or ``http_timeout``.

    Distinguishes from ``httpx.TimeoutException`` so generic catches
    against the SDK base class also catch timeouts. Inspect ``problem``
    for which phase timed out (connect, read, pool).
    """


class ConnectionError(TierProxyError):  # noqa: A001
    """The SDK could not establish a TCP connection to the gateway or to
    an upstream-via-gateway.

    Most often a DNS or firewall issue. ``problem['detail']`` carries
    the underlying httpx error string when available.
    """


_STATUS: dict[int, type[TierProxyError]] = {
    400: ValidationError,
    401: AuthenticationError,
    403: PermissionError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
}


def from_problem(status_code: int, problem: dict[str, Any]) -> TierProxyError:
    """Map an RFC 7807 problem+json body to the right exception subclass.

    Used internally by :class:`Transport` to translate a non-2xx response
    into a typed exception. Public so callers building custom transports
    can reuse the mapping.

    Args:
        status_code: HTTP status from the response.
        problem: Parsed JSON body. Expected fields: ``type``, ``title``,
            ``detail``, ``request_id``. Missing fields are tolerated.

    Returns:
        Subclass-specific instance. Status codes not in the mapping
        return :class:`ServerError` (5xx) or the base :class:`TierProxyError`
        (other).
    """
    cls = _STATUS.get(status_code) or (ServerError if status_code >= 500 else TierProxyError)
    return cls(
        problem.get("detail") or problem.get("title") or "tierproxy error",
        status_code=status_code,
        request_id=problem.get("request_id"),
        error_type=problem.get("type"),
        problem=problem,
    )
