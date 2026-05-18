from typing import Any

from tierproxy._module_api import get, post, request, reset_default_client, session
from tierproxy._version import __version__
from tierproxy.async_client import AsyncTierProxy
from tierproxy.client import TierProxy
from tierproxy.errors import (
    AuthenticationError,
    ConflictError,
    ConnectionError,  # noqa: A004
    NotFoundError,
    PermissionError,  # noqa: A004
    RateLimitError,
    ServerError,
    TierProxyError,
    TimeoutError,  # noqa: A004
    ValidationError,
)
from tierproxy.proxy.url_builder import ProxyURL
from tierproxy.resources.health import UpstreamHealth
from tierproxy.resources.me import Me
from tierproxy.resources.usage import Usage, UsageDay, UsageDelta
from tierproxy.retry import RetryPolicy


def enable_telemetry(**kwargs: Any) -> None:
    """Lazy proxy to tierproxy._otel.enable_telemetry — keeps OTel import optional."""
    from tierproxy._otel import enable_telemetry as _enable

    _enable(**kwargs)


__all__ = [
    "AsyncTierProxy",
    "AuthenticationError",
    "ConflictError",
    "ConnectionError",
    "TierProxy",
    "TierProxyError",
    "Me",
    "NotFoundError",
    "PermissionError",
    "ProxyURL",
    "RateLimitError",
    "RetryPolicy",
    "ServerError",
    "TimeoutError",
    "Usage",
    "UsageDay",
    "UsageDelta",
    "UpstreamHealth",
    "ValidationError",
    "__version__",
    "enable_telemetry",
    "get",
    "post",
    "request",
    "reset_default_client",
    "session",
]
