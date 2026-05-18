"""Module-level requests-style helpers backed by a lazy singleton TierProxy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from tierproxy.client import TierProxy

_default_client: TierProxy | None = None


def _client() -> TierProxy:
    global _default_client
    if _default_client is None:
        from tierproxy.client import TierProxy

        _default_client = TierProxy()
    return _default_client


def get(url: str, **kwargs: Any) -> Any:
    """Module-level GET through the gateway. Forwards targeting kwargs to ProxyURL.

    Returns ``httpx.Response`` by default; with ``stream=True`` returns a
    context manager.
    """
    return _client().get(url, **kwargs)


def post(url: str, **kwargs: Any) -> Any:
    return _client().post(url, **kwargs)


def request(method: str, url: str, **kwargs: Any) -> Any:
    return _client().request(method, url, **kwargs)


def session(**kwargs: Any) -> httpx.Client:
    """Return an httpx.Client preconfigured to route through the gateway with the given targeting."""
    return _client().session(**kwargs)


def reset_default_client() -> None:
    """For tests: drop the singleton so the next call rebuilds it."""
    global _default_client
    if _default_client is not None:
        _default_client.close()
        _default_client = None
