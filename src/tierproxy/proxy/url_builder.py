"""ProxyURL builder. Two modes:
- header_mode (default): caller emits X-Proxy-Geo etc headers; useful in httpx/requests
- username_encoding: encodes modifiers as customer-X-cc-US-...; useful for Playwright
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import quote

Mode = Literal["headers", "username_encoding"]
Pool = Literal["residential", "datacenter", "isp", "mobile"]


def _q(s: str) -> str:
    """URL-encode a single modifier value with no safe chars.

    Every customer-supplied piece of the username string goes through this so
    that contents like `:`, `@`, `%`, ` `, `/` can't break out of the
    username token and corrupt the proxy URL's userinfo / host boundary.
    """
    return quote(s, safe="")


@dataclass
class ProxyURL:
    """Parsed proxy URL with optional authentication and targeting parameters.

    Represents a single gateway connection endpoint together with the
    credentials and targeting modifiers needed to route a request through
    tierproxy.

    Two credential-encoding modes are supported:

    ``"headers"`` (default)
        The ``api_key`` is sent as the proxy username and targeting parameters
        are encoded as ``X-Proxy-*`` headers (e.g. ``X-Proxy-Geo``,
        ``X-Proxy-Session``). Use this for HTTP CONNECT proxies that parse
        ``Proxy-Authorization`` and custom headers — httpx and requests both
        work well in this mode.

    ``"username_encoding"``
        All targeting modifiers are embedded directly in the username field
        using a ``customer-<key>-<modifier>-<value>-...`` convention
        (Smartproxy-compatible style). Use this for tooling such as Playwright
        or Selenium that only accepts a proxy as a plain URL string and has no
        mechanism to inject per-request headers.

    Targeting fields:

    - ``country``: ISO 3166-1 alpha-2 exit-country code (e.g. ``"US"``).
    - ``city``: City name hint for geo-targeting (1–64 chars).
    - ``session_id``: Sticky-session identifier (alphanumeric or ``-_``,
      1–64 chars). Requests sharing the same ``session_id`` are pinned to the
      same residential IP for the duration of the session.
    - ``session_duration_minutes``: How long to hold the sticky session
      (1–1440 minutes).
    - ``upstream_hint``: Preferred upstream provider identifier (e.g.
      ``"decodo"``). The gateway will try this upstream first.
    - ``pool``: Proxy pool type — ``"residential"``, ``"datacenter"``,
      ``"isp"``, or ``"mobile"``. Defaults to residential when None.

    Example::

        from tierproxy.proxy.url_builder import ProxyURL

        p = ProxyURL(api_key="tp_live_abc123", host="gw.example.com", port_https=443)
        print(p.http_url())
        # http://tp_live_abc123:x@gw.example.com:443

        p2 = ProxyURL(
            api_key="tp_live_abc123",
            host="gw.example.com",
            country="DE",
            session_id="job-42",
        )
        print(p2.headers())
        # {'X-Proxy-Geo': 'DE', 'X-Proxy-Session': 'job-42'}
    """

    api_key: str
    password: str = ""
    pool: Pool | None = None
    country: str | None = None
    city: str | None = None
    session_id: str | None = None
    session_duration_minutes: int | None = None
    upstream_hint: str | None = None
    host: str = "gw.tierproxy.com"
    port_https: int = 443
    port_socks5: int = 1080
    mode: Mode = "headers"

    def __post_init__(self) -> None:
        self._validate()

    def encoded_username(self) -> str:
        """Build username with all modifiers inline (Smartproxy-style)."""
        parts: list[str] = ["customer", _q(self.api_key)]
        if self.pool and self.pool != "residential":
            parts += ["pool", _q(self.pool)]
        if self.country:
            parts += ["cc", _q(self.country)]
        if self.city:
            parts += ["city", _q(self.city)]
        if self.session_id:
            parts += ["sessid", _q(self.session_id)]
        if self.session_duration_minutes:
            parts += ["sesstime", str(int(self.session_duration_minutes))]
        if self.upstream_hint:
            parts += ["upstream", _q(self.upstream_hint)]
        return "-".join(parts)

    def headers(self) -> dict[str, str]:
        """Headers form. Set on every request. Gateway parses these."""
        h: dict[str, str] = {}
        if self.country:
            h["X-Proxy-Geo"] = self.country
        if self.session_id:
            h["X-Proxy-Session"] = self.session_id
        if self.session_duration_minutes:
            h["X-Proxy-Session-TTL"] = str(self.session_duration_minutes)
        if self.upstream_hint:
            h["X-Proxy-Upstream-Hint"] = self.upstream_hint
        return h

    def http_url(self) -> str:
        """`http://user:pass@host:port` for HTTP proxy clients."""
        user = self.encoded_username() if self.mode == "username_encoding" else self.api_key
        return f"http://{user}:{self.password or 'x'}@{self.host}:{self.port_https}"

    def socks5_url(self) -> str:
        """``socks5://user:pass@host:port`` for SOCKS5 proxy clients."""
        user = self.encoded_username() if self.mode == "username_encoding" else self.api_key
        return f"socks5://{user}:{self.password or 'x'}@{self.host}:{self.port_socks5}"

    def _validate(self) -> None:
        """Raise ValueError if any field fails its invariant check."""
        if not self.api_key:
            raise ValueError("api_key required")
        if self.country is not None and not (
            len(self.country) == 2 and self.country.isalpha() and self.country.isupper()
        ):
            raise ValueError(f"country must be ISO 3166-1 alpha-2 uppercase, got {self.country!r}")
        if self.city is not None and (not self.city or len(self.city) > 64):
            raise ValueError(f"city invalid: {self.city!r}")
        if self.session_id is not None:
            if not all(c.isalnum() or c in "-_" for c in self.session_id):
                raise ValueError(f"session_id must be alphanumeric or - _: {self.session_id!r}")
            if not (1 <= len(self.session_id) <= 64):
                raise ValueError("session_id length 1-64")
        if self.session_duration_minutes is not None and not (
            1 <= self.session_duration_minutes <= 1440
        ):
            raise ValueError("session_duration_minutes 1-1440")
