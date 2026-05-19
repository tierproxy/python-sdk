from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx

from tierproxy._internal.cache import ResponseCache
from tierproxy._internal.cookies import CookieJar
from tierproxy._internal.http import Transport
from tierproxy._internal.streaming import is_stream, sync_stream
from tierproxy._internal.validators import validate_api_key, validate_base_url
from tierproxy.errors import AuthenticationError
from tierproxy.resources.health import HealthResource
from tierproxy.resources.me import MeResource
from tierproxy.resources.ratelimits import RateLimitsResource
from tierproxy.resources.usage import UsageResource
from tierproxy.resources.usage_recent import UsageRecentResource
from tierproxy.retry import RetryPolicy

if TYPE_CHECKING:
    from tierproxy._internal.cost import CostAttributor
    from tierproxy.proxy.selector import SmartSelector


class TierProxy:
    """Synchronous client for the tierproxy public REST API.

    Use as a context manager to guarantee underlying httpx clients are closed::

        with TierProxy() as client:
            me = client.me.get()
            resp = client.get("https://example.com/scrape")

    The same client instance is safe to share across threads — every proxied
    request builds its own httpx.Client. For high-throughput async workloads,
    prefer :class:`AsyncTierProxy`.

    Authentication uses an API key. Either pass ``api_key`` explicitly or set
    the ``TIERPROXY_API_KEY`` environment variable; passing ``api_key=None``
    falls back to the env var.

    Args:
        api_key: Account API key (format ``tp_live_...``). If None, reads
            ``TIERPROXY_API_KEY`` from env. Raises ``AuthenticationError`` if
            both are missing.
        base_url: Gateway base URL. Defaults to production
            (``https://gw.tierproxy.com:8444``). Override for staging or a
            self-hosted gateway.
        timeout: Overall request timeout in seconds for control-plane calls
            (``/v1/me``, ``/v1/usage/...``). Defaults to 30 s.
        http_timeout: Per-request timeout in seconds for proxied traffic
            (``client.get(url)`` etc.). Defaults to 30 s. Increase for slow
            target sites.
        max_retries: Retries on retryable failures (5xx, 429, network) for
            control-plane calls. Ignored when ``retry_policy`` is given.
            Defaults to 3.
        retry_policy: Full :class:`RetryPolicy` for fine control over
            backoff, jitter, and the retryable status set. Overrides
            ``max_retries``.
        http_client: Bring-your-own ``httpx.Client``. Useful for sharing a
            connection pool with the rest of your application. Defaults to
            a client owned by the SDK and closed in ``__exit__``.
        user_agent_suffix: Appended to the ``User-Agent`` header (after the
            SDK identifier). Use for application identification in gateway
            logs (e.g. ``"my-scraper/1.4"``).
        routing: Smart-routing strategy. One of ``"balanced"``, ``"cheap"``,
            ``"fast"``, or None to disable. Activates the in-process
            :class:`SmartSelector` which picks an upstream per request based
            on success-rate and cost.
        monthly_budget_usd: Hard cost ceiling in USD. The client refuses
            requests once month-to-date spend approaches this number. None
            disables the guard.
        cache_ttl: Seconds to cache successful GET responses keyed by
            (method, url, params). 0 disables. Cache is in-memory and
            per-instance.
        cache_max_size: Maximum number of cached responses (LRU eviction).
            Ignored when ``cache_ttl=0``.
        cache_max_response_size: Maximum byte length of a response body
            eligible for caching. Larger responses bypass the cache.
        auto_failover: When True, retries failed requests on a different
            upstream via the SmartSelector. Useful when one provider is
            having a regional outage.
        auto_failover_max_attempts: Upper bound on upstream tries per
            request. Defaults to 3 (initial + 2 fallbacks).
        allow_insecure: Permit an HTTP base_url. Defaults to False —
            HTTPS-only. Set True only for self-hosted gateways without TLS.

    Raises:
        AuthenticationError: No ``api_key`` passed and ``TIERPROXY_API_KEY``
            env var not set.
        ValueError: ``api_key`` or ``base_url`` fails validator checks
            (malformed key, http base_url without ``allow_insecure``).

    Example:
        Basic::

            with TierProxy() as g:
                me = g.me.get()
                resp = g.get("https://httpbin.org/ip", country="US")

        Cost-aware::

            with TierProxy(routing="cheap", monthly_budget_usd=50.0) as g:
                resp = g.get("https://example.com/page")
                print("cost:", g.cost_for(resp))

        Bring your own httpx client::

            shared = httpx.Client(http2=True)
            with TierProxy(http_client=shared) as g:
                g.get("https://example.com")
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://gw.tierproxy.com:8444",
        timeout: float = 30.0,
        http_timeout: float = 30.0,
        max_retries: int = 3,
        retry_policy: RetryPolicy | None = None,
        http_client: httpx.Client | None = None,
        user_agent_suffix: str | None = None,
        routing: str | None = None,
        monthly_budget_usd: float | None = None,
        cache_ttl: float = 0.0,
        cache_max_size: int = 256,
        cache_max_response_size: int = 262144,
        auto_failover: bool = False,
        auto_failover_max_attempts: int = 3,
        allow_insecure: bool = False,
    ) -> None:
        """Construct the client. See :class:`TierProxy` for argument documentation."""
        key = api_key if api_key is not None else os.environ.get("TIERPROXY_API_KEY")
        if key is None:
            raise AuthenticationError("No api_key passed and TIERPROXY_API_KEY env var not set")
        validate_api_key(key)
        validate_base_url(base_url, allow_insecure)
        self.base_url = base_url
        retry = retry_policy or RetryPolicy(max_retries=max_retries)
        self._transport = Transport(
            api_key=key,
            base_url=base_url,
            timeout=timeout,
            retry=retry,
            ua_suffix=user_agent_suffix,
            http_client=http_client,
            is_async=False,
        )
        self._me: MeResource | None = None
        self._usage: UsageResource | None = None
        self._health: HealthResource | None = None
        self._usage_recent: UsageRecentResource | None = None
        self._cost_attributor: CostAttributor | None = None
        self._rate_limits: RateLimitsResource | None = None
        self._pending_429_reports: set[str] = set()

        self._http_timeout = http_timeout
        self._routing = routing
        self._monthly_budget_usd = monthly_budget_usd
        self._cache_ttl = cache_ttl
        self._response_cache: ResponseCache | None = (
            ResponseCache(
                max_size=cache_max_size,
                default_ttl=cache_ttl,
                max_response_size=cache_max_response_size,
            )
            if cache_ttl > 0
            else None
        )
        self._selector: SmartSelector | None = None
        self._spent_usd_mtd: float = 0.0
        self._budget_cache_ts: float = 0.0
        self._auto_failover = auto_failover
        self._auto_failover_max_attempts = max(1, auto_failover_max_attempts)
        self._cookie_jar = CookieJar()
        if routing or auto_failover:
            from tierproxy.proxy.selector import SmartSelector

            self._selector = SmartSelector(self, strategy=routing or "balanced")  # type: ignore[arg-type]

    @property
    def me(self) -> MeResource:
        """Lazy accessor for the Me resource."""
        if self._me is None:
            self._me = MeResource(self)
        return self._me

    @property
    def usage(self) -> UsageResource:
        """Lazy accessor for the Usage resource."""
        if self._usage is None:
            self._usage = UsageResource(self)
        return self._usage

    @property
    def health(self) -> HealthResource:
        """Lazy accessor for the Health resource."""
        if self._health is None:
            self._health = HealthResource(self)
        return self._health

    @property
    def usage_recent(self) -> UsageRecentResource:
        """Lazy accessor for the UsageRecent resource."""
        if self._usage_recent is None:
            self._usage_recent = UsageRecentResource(self)
        return self._usage_recent

    @property
    def rate_limits(self) -> RateLimitsResource:
        """Lazy accessor for the RateLimits resource."""
        if self._rate_limits is None:
            self._rate_limits = RateLimitsResource(self)
        return self._rate_limits

    @property
    def cookies(self) -> CookieJar:
        """Lazy accessor for the per-session cookie jar."""
        return self._cookie_jar

    def cost_for(self, resp: httpx.Response) -> float | None:
        """Return the USD cost attributed to a proxied response.

        Args:
            resp: An ``httpx.Response`` previously returned by
                :meth:`request`, :meth:`get`, or :meth:`post`.

        Returns:
            Estimated cost in USD, or None if cost data is unavailable for
            this response (e.g. the response came from cache or the upstream
            cost table has not loaded yet).
        """
        if self._cost_attributor is None:
            from tierproxy._internal.cost import CostAttributor

            self._cost_attributor = CostAttributor(self)
        return self._cost_attributor.cost_for(resp)

    def upstream_for(self, resp: httpx.Response) -> str | None:
        """Return the upstream ID that served a proxied response.

        Args:
            resp: An ``httpx.Response`` previously returned by
                :meth:`request`, :meth:`get`, or :meth:`post`.

        Returns:
            Upstream identifier string (e.g. ``"decodo"``), or None if the
            upstream cannot be determined from the response.
        """
        if self._cost_attributor is None:
            from tierproxy._internal.cost import CostAttributor

            self._cost_attributor = CostAttributor(self)
        return self._cost_attributor.upstream_for(resp)

    def close(self) -> None:
        """Close the underlying httpx client. Called automatically by ``__exit__``."""
        client = self._transport._client
        if isinstance(client, httpx.Client):
            client.close()

    def __enter__(self) -> TierProxy:
        """Enter the context manager, returning this client instance."""
        return self

    def __exit__(self, *_: Any) -> None:
        """Exit the context manager, closing the underlying httpx client."""
        self.close()

    # -------- Level 1-2: proxy-through helpers --------

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Make an HTTP request *through* the tierproxy gateway.

        Targeting kwargs (``country``, ``state``, ``city``, ``session_id``,
        ``ttl``, ``tls_fingerprint``, ``upstream_hint``) are intercepted and
        encoded into the proxy URL or request headers; all remaining kwargs
        are forwarded to ``httpx`` (``timeout``, ``json``, ``data``,
        ``headers``, ``params``, etc.).

        Successful GET responses are cached when ``cache_ttl > 0`` and the
        response body is within ``cache_max_response_size``. Cache is keyed
        by ``(method, url, params)``.

        When ``auto_failover=True``, transient failures (5xx, 429, network
        errors) transparently retry on a different upstream up to
        ``auto_failover_max_attempts`` times before propagating the error.

        Cookie persistence is automatic when ``session_id`` is present —
        cookies from each response are stored in the per-session
        :attr:`cookies` jar and replayed on the next request with the same
        ``session_id``.

        When ``stream=True`` is passed, returns a context manager yielding an
        ``httpx.Response`` whose body must be iterated (``iter_bytes``/``iter_text``).
        Cache, failover, and cookie persistence are skipped in stream mode.

        Args:
            method: HTTP verb (e.g. ``"GET"``, ``"POST"``).
            url: Full URL of the target resource being fetched through the
                proxy (e.g. ``"https://httpbin.org/ip"``).
            **kwargs: Targeting kwargs and httpx passthrough kwargs.
                Targeting: ``country`` (ISO 3166-1 alpha-2), ``state``,
                ``city``, ``session_id`` (alphanumeric, 1–64 chars),
                ``ttl`` (session duration minutes, 1–1440),
                ``tls_fingerprint``, ``upstream_hint``.
                Everything else is forwarded to ``httpx.Client.request``.

        Returns:
            ``httpx.Response`` for normal requests. When ``stream=True``, a
            context manager that yields ``httpx.Response`` — use
            ``with client.request(..., stream=True) as r: r.iter_bytes()``.

        Raises:
            AuthenticationError: API key rejected by the gateway.
            RateLimitError: Gateway returned 429.
            ServerError: Gateway or upstream returned 5xx.
            TierProxyError: Any other error originating from the gateway.
            httpx.TimeoutException: Request exceeded ``http_timeout``.
            httpx.NetworkError: Transport-level failure contacting the gateway.
        """
        if is_stream(kwargs):
            return self._stream_request(method, url, **kwargs)

        cache = self._response_cache
        params = kwargs.get("params") if isinstance(kwargs.get("params"), dict) else None
        if cache is not None and method.upper() == "GET":
            cached = cache.get(method, url, params)
            if cached is not None:
                return cached

        resp = self._dispatch(method, url, **kwargs)

        if cache is not None and method.upper() == "GET" and 200 <= resp.status_code < 300:
            cache.set(method, url, params, resp, ttl=self._cache_ttl)
        return resp

    def _dispatch(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        if not self._auto_failover or self._selector is None:
            return self._do_request(method, url, **kwargs)

        tried: set[str] = set()
        attempts = 0
        last_resp: httpx.Response | None = None
        last_exc: Exception | None = None
        max_attempts = self._auto_failover_max_attempts

        while attempts < max_attempts:
            override: str | None = None
            if attempts == 0:
                chosen = self._selector.pick()
            else:
                nxt = self._selector.pick_next(tried)
                if nxt is None:
                    break
                chosen = nxt
            override = chosen.upstream_id
            tried.add(override)
            attempts += 1
            try:
                resp = self._do_request(method, url, _upstream_override=override, **kwargs)
            except (httpx.ConnectError, httpx.NetworkError, httpx.TimeoutException) as e:
                last_exc = e
                continue
            last_resp = resp
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                continue
            return resp

        if last_resp is not None:
            return last_resp
        assert last_exc is not None
        raise last_exc

    def _do_request(
        self,
        method: str,
        url: str,
        _upstream_override: str | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        from tierproxy._targeting import build_proxy, split_kwargs

        targeting, passthrough = split_kwargs(kwargs)
        host = httpx.URL(self._transport.base_url).host
        proxy = build_proxy(self._transport.api_key, host, 443, targeting)

        if _upstream_override is not None:
            proxy.upstream_hint = _upstream_override
        elif self._selector is not None and not proxy.upstream_hint:
            chosen = self._selector.pick()
            proxy.upstream_hint = chosen.upstream_id

        headers = passthrough.pop("headers", None) or {}
        headers = {**headers, **proxy.headers()}
        if self._pending_429_reports:
            headers["X-TierProxy-Report-429"] = ",".join(sorted(self._pending_429_reports))
            self._pending_429_reports.clear()
        if (tls_fp := passthrough.pop("tls_fingerprint", None)) is not None:
            headers["X-TierProxy-TLS-Profile"] = str(tls_fp)

        if self._monthly_budget_usd is not None:
            self._guard_budget()

        session_id = targeting.get("session_id")
        cookies = self._cookie_jar.get(session_id) if session_id else None

        with httpx.Client(proxy=proxy.http_url(), timeout=self._http_timeout, cookies=cookies) as h:
            resp = h.request(method, url, headers=headers, **passthrough)
        if session_id:
            self._cookie_jar.update_from(session_id, resp)
        if resp.status_code == 429:
            target_host = httpx.URL(url).host
            if target_host:
                self._pending_429_reports.add(target_host)
        return resp

    def _stream_request(self, method: str, url: str, **kwargs: Any) -> Any:
        from tierproxy._targeting import build_proxy, split_kwargs

        targeting, passthrough = split_kwargs(kwargs)
        host = httpx.URL(self._transport.base_url).host
        proxy = build_proxy(self._transport.api_key, host, 443, targeting)

        if self._selector is not None and not proxy.upstream_hint:
            chosen = self._selector.pick()
            proxy.upstream_hint = chosen.upstream_id

        headers = passthrough.pop("headers", None) or {}
        headers = {**headers, **proxy.headers()}
        if (tls_fp := passthrough.pop("tls_fingerprint", None)) is not None:
            headers["X-TierProxy-TLS-Profile"] = str(tls_fp)

        if self._monthly_budget_usd is not None:
            self._guard_budget()

        return sync_stream(
            method,
            url,
            proxy=proxy.http_url(),
            timeout=self._http_timeout,
            headers=headers,
            **passthrough,
        )

    def get(self, url: str, **kwargs: Any) -> Any:
        """Make a GET request through the gateway. Delegates to :meth:`request`."""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Any:
        """Make a POST request through the gateway. Delegates to :meth:`request`."""
        return self.request("POST", url, **kwargs)

    def session(self, **targeting_kwargs: Any) -> httpx.Client:
        """Return an ``httpx.Client`` preconfigured to route through the gateway.

        Useful when the caller wants to make many requests with the same
        targeting (e.g. one scraper job) without rebuilding the proxy on
        every call. The returned client is not managed by this ``TierProxy``
        instance — the caller is responsible for closing it.

        Args:
            **targeting_kwargs: Targeting parameters baked into the proxy URL
                for every request made with the returned client. Supported
                keys: ``country``, ``state``, ``city``, ``session_id``,
                ``ttl``, ``upstream_hint``, ``pool``.

        Returns:
            A configured ``httpx.Client`` with the proxy and headers set.
            Use as a context manager or call ``.close()`` when done.
        """
        from tierproxy._targeting import build_proxy

        host = httpx.URL(self._transport.base_url).host
        proxy = build_proxy(self._transport.api_key, host, 443, targeting_kwargs)
        return httpx.Client(
            proxy=proxy.http_url(),
            headers=proxy.headers(),
            timeout=self._http_timeout,
        )

    def target(self, **kwargs: Any) -> TargetedRequest:
        """Builder pattern: capture targeting kwargs and return a request helper.

        Lets you set targeting once and issue multiple typed requests without
        repeating the kwargs::

            t = g.target(country="DE", session_id="job-42")
            r1 = t.get("https://example.com/page1")
            r2 = t.post("https://example.com/form", json={"q": "hello"})

        Args:
            **kwargs: Targeting parameters forwarded to every subsequent
                request. Same keys as :meth:`request`.

        Returns:
            A :class:`TargetedRequest` bound to this client and the given
            targeting kwargs.
        """
        return TargetedRequest(self, kwargs)

    # -------- Level 3: cost guard --------

    def _guard_budget(self) -> None:
        """Fetches latest /v1/usage/me cost and refuses request if over budget.

        Cached for 60s. Caller can clear via ``client._budget_cache_ts = 0``.
        """
        import time

        from tierproxy._guard import check_budget

        if time.time() - self._budget_cache_ts > 60:
            usage = self.usage.get()
            self._spent_usd_mtd = usage.total_cost_usd
            self._budget_cache_ts = time.time()
        avg_cost = 4.0
        estimated = avg_cost * (1024 * 1024) / (1024**3)
        assert self._monthly_budget_usd is not None
        check_budget(estimated, self._spent_usd_mtd, self._monthly_budget_usd)


class TargetedRequest:
    """One-shot helper that captures targeting kwargs and forwards to the client.

    Returned by :meth:`TierProxy.target`. Holds a reference to the parent
    client and a fixed set of targeting parameters that are merged into every
    subsequent request. Additional per-request kwargs can still be passed and
    will override the captured targeting where they overlap.

    Args:
        client: The :class:`TierProxy` instance that will execute requests.
        targeting: Targeting kwargs captured from :meth:`TierProxy.target`.
    """

    def __init__(self, client: TierProxy, targeting: dict[str, Any]) -> None:
        self._client = client
        self._targeting = targeting

    def get(self, url: str, **kw: Any) -> Any:
        """Make a GET request with the captured targeting merged in.

        Args:
            url: Target URL.
            **kw: Additional kwargs forwarded to :meth:`TierProxy.request`;
                override captured targeting on conflict.

        Returns:
            ``httpx.Response`` or a stream context manager if ``stream=True``.
        """
        return self._client.get(url, **{**self._targeting, **kw})

    def post(self, url: str, **kw: Any) -> Any:
        """Make a POST request with the captured targeting merged in.

        Args:
            url: Target URL.
            **kw: Additional kwargs forwarded to :meth:`TierProxy.request`;
                override captured targeting on conflict.

        Returns:
            ``httpx.Response`` or a stream context manager if ``stream=True``.
        """
        return self._client.post(url, **{**self._targeting, **kw})

    def request(self, method: str, url: str, **kw: Any) -> Any:
        """Make a request with the given method and the captured targeting merged in.

        Args:
            method: HTTP verb (e.g. ``"GET"``, ``"POST"``).
            url: Target URL.
            **kw: Additional kwargs forwarded to :meth:`TierProxy.request`;
                override captured targeting on conflict.

        Returns:
            ``httpx.Response`` or a stream context manager if ``stream=True``.
        """
        return self._client.request(method, url, **{**self._targeting, **kw})
