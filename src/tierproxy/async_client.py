from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx

from tierproxy._internal.cache import ResponseCache
from tierproxy._internal.cookies import CookieJar
from tierproxy._internal.http import Transport
from tierproxy._internal.streaming import AsyncStreamCM, is_stream
from tierproxy._internal.validators import validate_api_key, validate_base_url
from tierproxy.errors import AuthenticationError
from tierproxy.resources.health import AsyncHealthResource
from tierproxy.resources.me import AsyncMeResource
from tierproxy.resources.ratelimits import AsyncRateLimitsResource
from tierproxy.resources.usage import AsyncUsageResource
from tierproxy.resources.usage_recent import AsyncUsageRecentResource
from tierproxy.retry import RetryPolicy

if TYPE_CHECKING:
    from tierproxy._internal.cost import AsyncCostAttributor
    from tierproxy.proxy.selector import AsyncSmartSelector


class AsyncTierProxy:
    """Asynchronous client for the tierproxy public REST API.

    Use as an async context manager::

        async with AsyncTierProxy() as client:
            me = await client.me.get()
            resp = await client.get("https://example.com/scrape")

    Prefer this over :class:`TierProxy` for high-throughput workloads where many
    requests can be in-flight concurrently. Args identical to :class:`TierProxy`
    — see that class's docstring for the full kwarg reference.
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
        http_client: httpx.AsyncClient | None = None,
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
        """Construct the async client. See :class:`AsyncTierProxy` for argument documentation."""
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
            is_async=True,
        )
        self._me: AsyncMeResource | None = None
        self._usage: AsyncUsageResource | None = None
        self._health: AsyncHealthResource | None = None
        self._usage_recent: AsyncUsageRecentResource | None = None
        self._cost_attributor: AsyncCostAttributor | None = None
        self._rate_limits: AsyncRateLimitsResource | None = None
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
        self._selector: AsyncSmartSelector | None = None
        self._spent_usd_mtd: float = 0.0
        self._budget_cache_ts: float = 0.0
        self._auto_failover = auto_failover
        self._auto_failover_max_attempts = max(1, auto_failover_max_attempts)
        self._cookie_jar = CookieJar()
        if routing or auto_failover:
            from tierproxy.proxy.selector import AsyncSmartSelector

            self._selector = AsyncSmartSelector(self, strategy=routing or "balanced")  # type: ignore[arg-type]

    @property
    def me(self) -> AsyncMeResource:
        """Lazy accessor for the Me resource."""
        if self._me is None:
            self._me = AsyncMeResource(self)
        return self._me

    @property
    def usage(self) -> AsyncUsageResource:
        """Lazy accessor for the Usage resource."""
        if self._usage is None:
            self._usage = AsyncUsageResource(self)
        return self._usage

    @property
    def health(self) -> AsyncHealthResource:
        """Lazy accessor for the Health resource."""
        if self._health is None:
            self._health = AsyncHealthResource(self)
        return self._health

    @property
    def usage_recent(self) -> AsyncUsageRecentResource:
        """Lazy accessor for the UsageRecent resource."""
        if self._usage_recent is None:
            self._usage_recent = AsyncUsageRecentResource(self)
        return self._usage_recent

    @property
    def rate_limits(self) -> AsyncRateLimitsResource:
        """Lazy accessor for the RateLimits resource."""
        if self._rate_limits is None:
            self._rate_limits = AsyncRateLimitsResource(self)
        return self._rate_limits

    @property
    def cookies(self) -> CookieJar:
        """Lazy accessor for the per-session cookie jar."""
        return self._cookie_jar

    async def cost_for(self, resp: httpx.Response) -> float | None:
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
            from tierproxy._internal.cost import AsyncCostAttributor

            self._cost_attributor = AsyncCostAttributor(self)
        return await self._cost_attributor.cost_for(resp)

    async def upstream_for(self, resp: httpx.Response) -> str | None:
        """Return the upstream ID that served a proxied response.

        Args:
            resp: An ``httpx.Response`` previously returned by
                :meth:`request`, :meth:`get`, or :meth:`post`.

        Returns:
            Upstream identifier string (e.g. ``"decodo"``), or None if the
            upstream cannot be determined from the response.
        """
        if self._cost_attributor is None:
            from tierproxy._internal.cost import AsyncCostAttributor

            self._cost_attributor = AsyncCostAttributor(self)
        return await self._cost_attributor.upstream_for(resp)

    async def close(self) -> None:
        """Close the underlying httpx async client. Called automatically by ``__aexit__``."""
        client = self._transport._client
        if isinstance(client, httpx.AsyncClient):
            await client.aclose()

    async def __aenter__(self) -> AsyncTierProxy:
        """Enter the async context manager, returning this client instance."""
        return self

    async def __aexit__(self, *_: Any) -> None:
        """Exit the async context manager, closing the underlying httpx client."""
        await self.close()

    # -------- Level 1-2: proxy-through helpers --------

    async def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Make an async HTTP request *through* the tierproxy gateway.

        Semantics are identical to :meth:`TierProxy.request` — see that
        method's docstring for the full parameter and behavior reference.

        When ``stream=True`` is passed, returns an async context manager
        yielding an ``httpx.Response`` for streaming.

        Args:
            method: HTTP verb (e.g. ``"GET"``, ``"POST"``).
            url: Full URL of the target resource.
            **kwargs: Targeting kwargs and httpx passthrough kwargs.

        Returns:
            ``httpx.Response`` for normal requests. When ``stream=True``, an
            async context manager that yields ``httpx.Response``.

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

        resp = await self._dispatch(method, url, **kwargs)

        if cache is not None and method.upper() == "GET" and 200 <= resp.status_code < 300:
            cache.set(method, url, params, resp, ttl=self._cache_ttl)
        return resp

    async def _dispatch(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        if not self._auto_failover or self._selector is None:
            return await self._do_request(method, url, **kwargs)

        tried: set[str] = set()
        attempts = 0
        last_resp: httpx.Response | None = None
        last_exc: Exception | None = None
        max_attempts = self._auto_failover_max_attempts

        while attempts < max_attempts:
            if attempts == 0:
                chosen = await self._selector.pick()
            else:
                nxt = await self._selector.pick_next(tried)
                if nxt is None:
                    break
                chosen = nxt
            tried.add(chosen.upstream_id)
            attempts += 1
            try:
                resp = await self._do_request(
                    method, url, _upstream_override=chosen.upstream_id, **kwargs
                )
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

    async def _do_request(
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
            chosen = await self._selector.pick()
            proxy.upstream_hint = chosen.upstream_id

        headers = passthrough.pop("headers", None) or {}
        headers = {**headers, **proxy.headers()}
        if self._pending_429_reports:
            headers["X-TierProxy-Report-429"] = ",".join(sorted(self._pending_429_reports))
            self._pending_429_reports.clear()
        if (tls_fp := passthrough.pop("tls_fingerprint", None)) is not None:
            headers["X-TierProxy-TLS-Profile"] = str(tls_fp)

        if self._monthly_budget_usd is not None:
            await self._guard_budget_async()

        session_id = targeting.get("session_id")
        cookies = self._cookie_jar.get(session_id) if session_id else None

        async with httpx.AsyncClient(
            proxy=proxy.http_url(), timeout=self._http_timeout, cookies=cookies
        ) as h:
            resp = await h.request(method, url, headers=headers, **passthrough)
        if session_id:
            self._cookie_jar.update_from(session_id, resp)
        if resp.status_code == 429:
            target_host = httpx.URL(url).host
            if target_host:
                self._pending_429_reports.add(target_host)
        return resp

    def _stream_request(self, method: str, url: str, **kwargs: Any) -> AsyncStreamCM:
        from tierproxy._targeting import build_proxy, split_kwargs

        targeting, passthrough = split_kwargs(kwargs)
        host = httpx.URL(self._transport.base_url).host
        proxy = build_proxy(self._transport.api_key, host, 443, targeting)

        headers = passthrough.pop("headers", None) or {}
        headers = {**headers, **proxy.headers()}
        if (tls_fp := passthrough.pop("tls_fingerprint", None)) is not None:
            headers["X-TierProxy-TLS-Profile"] = str(tls_fp)

        return AsyncStreamCM(
            method,
            url,
            proxy=proxy.http_url(),
            timeout=self._http_timeout,
            headers=headers,
            **passthrough,
        )

    async def get(self, url: str, **kwargs: Any) -> Any:
        """Make an async GET request through the gateway. Delegates to :meth:`request`."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> Any:
        """Make an async POST request through the gateway. Delegates to :meth:`request`."""
        return await self.request("POST", url, **kwargs)

    def session(self, **targeting_kwargs: Any) -> httpx.AsyncClient:
        """Return an ``httpx.AsyncClient`` preconfigured to route through the gateway.

        Useful when the caller wants to make many requests with the same
        targeting without rebuilding the proxy on every call. The returned
        client is not managed by this ``AsyncTierProxy`` instance — the caller
        is responsible for closing it.

        Args:
            **targeting_kwargs: Targeting parameters baked into the proxy URL
                for every request made with the returned client. Supported
                keys: ``country``, ``state``, ``city``, ``session_id``,
                ``ttl``, ``upstream_hint``, ``pool``.

        Returns:
            A configured ``httpx.AsyncClient`` with the proxy and headers set.
            Use as an async context manager or call ``await .aclose()`` when done.
        """
        from tierproxy._targeting import build_proxy

        host = httpx.URL(self._transport.base_url).host
        proxy = build_proxy(self._transport.api_key, host, 443, targeting_kwargs)
        return httpx.AsyncClient(
            proxy=proxy.http_url(),
            headers=proxy.headers(),
            timeout=self._http_timeout,
        )

    def target(self, **kwargs: Any) -> AsyncTargetedRequest:
        """Builder pattern: capture targeting kwargs and return an async request helper.

        Args:
            **kwargs: Targeting parameters forwarded to every subsequent
                request. Same keys as :meth:`request`.

        Returns:
            An :class:`AsyncTargetedRequest` bound to this client and the
            given targeting kwargs.
        """
        return AsyncTargetedRequest(self, kwargs)

    # -------- Level 3: cost guard --------

    async def _guard_budget_async(self) -> None:
        import time

        from tierproxy._guard import check_budget

        if time.time() - self._budget_cache_ts > 60:
            usage = await self.usage.get()
            self._spent_usd_mtd = usage.total_cost_usd
            self._budget_cache_ts = time.time()
        avg_cost = 4.0
        estimated = avg_cost * (1024 * 1024) / (1024**3)
        assert self._monthly_budget_usd is not None
        check_budget(estimated, self._spent_usd_mtd, self._monthly_budget_usd)


class AsyncTargetedRequest:
    """One-shot async helper that captures targeting kwargs and forwards to the client.

    Returned by :meth:`AsyncTierProxy.target`. Holds a reference to the parent
    async client and a fixed set of targeting parameters merged into every
    subsequent request.

    Args:
        client: The :class:`AsyncTierProxy` instance that will execute requests.
        targeting: Targeting kwargs captured from :meth:`AsyncTierProxy.target`.
    """

    def __init__(self, client: AsyncTierProxy, targeting: dict[str, Any]) -> None:
        self._client = client
        self._targeting = targeting

    async def get(self, url: str, **kw: Any) -> Any:
        """Make an async GET request with the captured targeting merged in.

        Args:
            url: Target URL.
            **kw: Additional kwargs forwarded to :meth:`AsyncTierProxy.request`;
                override captured targeting on conflict.

        Returns:
            ``httpx.Response`` or an async stream context manager if ``stream=True``.
        """
        return await self._client.get(url, **{**self._targeting, **kw})

    async def post(self, url: str, **kw: Any) -> Any:
        """Make an async POST request with the captured targeting merged in.

        Args:
            url: Target URL.
            **kw: Additional kwargs forwarded to :meth:`AsyncTierProxy.request`;
                override captured targeting on conflict.

        Returns:
            ``httpx.Response`` or an async stream context manager if ``stream=True``.
        """
        return await self._client.post(url, **{**self._targeting, **kw})

    async def request(self, method: str, url: str, **kw: Any) -> Any:
        """Make an async request with the given method and the captured targeting merged in.

        Args:
            method: HTTP verb (e.g. ``"GET"``, ``"POST"``).
            url: Target URL.
            **kw: Additional kwargs forwarded to :meth:`AsyncTierProxy.request`;
                override captured targeting on conflict.

        Returns:
            ``httpx.Response`` or an async stream context manager if ``stream=True``.
        """
        return await self._client.request(method, url, **{**self._targeting, **kw})
