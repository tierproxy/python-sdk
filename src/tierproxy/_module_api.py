"""Module-level requests-style helpers backed by a lazy singleton TierProxy.

These functions provide a convenient top-level API — no need to construct a
client object explicitly. The underlying :class:`~tierproxy.TierProxy` instance is
created lazily on the first call, using ``TIERPROXY_API_KEY`` from the
environment. The singleton is shared across all calls in the same process.

.. note::
    Prefer the explicit ``TierProxy()`` context-manager form for production code
    that owns its lifecycle. Module-level helpers are convenient for scripts
    and interactive use but give no control over when the client is closed.

Example::

    import tierproxy

    resp = tierproxy.get("https://httpbin.org/ip", country="US")
    print(resp.json())
"""

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
    """Make a module-level GET request through the gateway.

    Delegates to the lazy singleton :class:`~tierproxy.TierProxy`. Prefer the
    explicit ``TierProxy()`` context-manager form for production code that owns
    its lifecycle.

    Args:
        url: Full URL of the target resource.
        **kwargs: Targeting kwargs (``country``, ``state``, ``city``,
            ``session_id``, ``ttl``, ``upstream_hint``) and httpx passthrough
            kwargs forwarded to :meth:`~tierproxy.TierProxy.request`.

    Returns:
        ``httpx.Response`` by default. When ``stream=True`` is passed,
        a context manager yielding ``httpx.Response``.

    Raises:
        AuthenticationError: ``TIERPROXY_API_KEY`` env var not set.
        RateLimitError: Gateway returned 429.
        ServerError: Gateway or upstream returned 5xx.
        TierProxyError: Any other error originating from the gateway.
    """
    return _client().get(url, **kwargs)


def post(url: str, **kwargs: Any) -> Any:
    """Make a module-level POST request through the gateway.

    Delegates to the lazy singleton :class:`~tierproxy.TierProxy`. Prefer the
    explicit ``TierProxy()`` context-manager form for production code that owns
    its lifecycle.

    Args:
        url: Full URL of the target resource.
        **kwargs: Targeting kwargs and httpx passthrough kwargs forwarded to
            :meth:`~tierproxy.TierProxy.request`.

    Returns:
        ``httpx.Response`` by default. When ``stream=True`` is passed,
        a context manager yielding ``httpx.Response``.

    Raises:
        AuthenticationError: ``TIERPROXY_API_KEY`` env var not set.
        RateLimitError: Gateway returned 429.
        ServerError: Gateway or upstream returned 5xx.
        TierProxyError: Any other error originating from the gateway.
    """
    return _client().post(url, **kwargs)


def request(method: str, url: str, **kwargs: Any) -> Any:
    """Make a module-level HTTP request through the gateway.

    Delegates to the lazy singleton :class:`~tierproxy.TierProxy`. Prefer the
    explicit ``TierProxy()`` context-manager form for production code that owns
    its lifecycle.

    Args:
        method: HTTP verb (e.g. ``"GET"``, ``"POST"``).
        url: Full URL of the target resource.
        **kwargs: Targeting kwargs and httpx passthrough kwargs forwarded to
            :meth:`~tierproxy.TierProxy.request`.

    Returns:
        ``httpx.Response`` by default. When ``stream=True`` is passed,
        a context manager yielding ``httpx.Response``.

    Raises:
        AuthenticationError: ``TIERPROXY_API_KEY`` env var not set.
        RateLimitError: Gateway returned 429.
        ServerError: Gateway or upstream returned 5xx.
        TierProxyError: Any other error originating from the gateway.
    """
    return _client().request(method, url, **kwargs)


def session(**kwargs: Any) -> httpx.Client:
    """Return an ``httpx.Client`` preconfigured to route through the gateway.

    Delegates to the lazy singleton :class:`~tierproxy.TierProxy`. Prefer the
    explicit ``TierProxy()`` context-manager form for production code that owns
    its lifecycle.

    Args:
        **kwargs: Targeting parameters baked into the proxy URL for every
            request made with the returned client. Supported keys:
            ``country``, ``state``, ``city``, ``session_id``, ``ttl``,
            ``upstream_hint``, ``pool``.

    Returns:
        A configured ``httpx.Client``. The caller is responsible for closing
        it (use as a context manager or call ``.close()``).
    """
    return _client().session(**kwargs)


def reset_default_client() -> None:
    """Drop the module-level singleton so the next call rebuilds it from env.

    Intended for use in tests that need a fresh client between test cases.
    Closes the existing client before discarding it.
    """
    global _default_client
    if _default_client is not None:
        _default_client.close()
        _default_client = None
