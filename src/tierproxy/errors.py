"""Public exception hierarchy. Every exception carries request_id for support."""

from __future__ import annotations

from typing import Any


class TierProxyError(Exception):
    """Base class. Catch this to handle any SDK error."""

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


class AuthenticationError(TierProxyError): ...


class PermissionError(TierProxyError): ...  # noqa: A001


class NotFoundError(TierProxyError): ...


class ValidationError(TierProxyError): ...


class ConflictError(TierProxyError): ...


class RateLimitError(TierProxyError):
    def __init__(self, *args: Any, retry_after: int | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


class ServerError(TierProxyError): ...


class TimeoutError(TierProxyError): ...  # noqa: A001


class ConnectionError(TierProxyError): ...  # noqa: A001


_STATUS: dict[int, type[TierProxyError]] = {
    400: ValidationError,
    401: AuthenticationError,
    403: PermissionError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
}


def from_problem(status_code: int, problem: dict[str, Any]) -> TierProxyError:
    """Map an RFC 7807 problem+json body to the right exception."""
    cls = _STATUS.get(status_code) or (ServerError if status_code >= 500 else TierProxyError)
    return cls(
        problem.get("detail") or problem.get("title") or "tierproxy error",
        status_code=status_code,
        request_id=problem.get("request_id"),
        error_type=problem.get("type"),
        problem=problem,
    )
