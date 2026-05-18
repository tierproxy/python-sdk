"""Resolve user-facing targeting kwargs into a ProxyURL.

Recognized kwargs:
- country: ISO-2 (mapped to X-Proxy-Geo)
- city: lowercase city (mapped to ProxyURL.city if username_encoding mode)
- session_id: sticky session pin
- session_duration_minutes: sticky TTL override
- upstream_hint: target a specific upstream
- mode: 'headers' | 'username_encoding'  (default 'headers')
- pool: residential/datacenter/isp/mobile
"""

from __future__ import annotations

from typing import Any

from tierproxy.proxy.url_builder import ProxyURL

_TARGETING_KEYS = {
    "country",
    "city",
    "session_id",
    "session_duration_minutes",
    "upstream_hint",
    "mode",
    "pool",
}


def split_kwargs(kwargs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (targeting, passthrough). Mutates the input dict."""
    targeting = {k: kwargs.pop(k) for k in list(kwargs) if k in _TARGETING_KEYS}
    return targeting, kwargs


def build_proxy(api_key: str, host: str, port: int, targeting: dict[str, Any]) -> ProxyURL:
    return ProxyURL(api_key=api_key, host=host, port_https=port, **targeting)
