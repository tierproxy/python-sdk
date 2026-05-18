"""Adapters for popular HTTP clients. Hide ProxyURL composition behind one call."""

from __future__ import annotations

import warnings
from dataclasses import replace
from typing import Any

from tierproxy.proxy.url_builder import ProxyURL


def requests_kwargs(proxy: ProxyURL) -> dict[str, Any]:
    """Returns kwargs to splat into requests.request(): proxies + headers."""
    url = proxy.http_url()
    return {"proxies": {"http": url, "https": url}, "headers": proxy.headers()}


def httpx_kwargs(proxy: ProxyURL) -> dict[str, Any]:
    """Returns kwargs for httpx.Client/AsyncClient or httpx.get."""
    return {"proxy": proxy.http_url(), "headers": proxy.headers()}


def aiohttp_kwargs(proxy: ProxyURL) -> dict[str, Any]:
    """For aiohttp.ClientSession.request(..., proxy=..., proxy_headers=...)."""
    return {"proxy": proxy.http_url(), "proxy_headers": proxy.headers()}


def playwright_proxy_config(proxy: ProxyURL) -> dict[str, str]:
    """Returns {server, username, password} for browser.launch(proxy=...).

    Browsers ignore headers on CONNECT, so this adapter requires
    ``ProxyURL(mode="username_encoding")``. If you pass a ProxyURL with
    ``mode="headers"``, the adapter silently clones it with
    ``mode="username_encoding"`` and emits a DeprecationWarning. Pass
    explicit ``mode="username_encoding"`` to silence the warning.
    """
    if proxy.mode != "username_encoding":
        warnings.warn(
            "playwright_proxy_config received ProxyURL(mode='headers'); "
            "silently cloning to mode='username_encoding'. Set mode explicitly "
            "to silence this warning.",
            DeprecationWarning,
            stacklevel=2,
        )
        proxy = replace(proxy, mode="username_encoding")
    return {
        "server": f"http://{proxy.host}:{proxy.port_https}",
        "username": proxy.encoded_username(),
        "password": proxy.password or "x",
    }
