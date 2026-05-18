# Migrating to tierproxy

## Migrating from v0.1.x to v0.2.0

### BREAKING CHANGES

#### 1. `on_usage_pct` callback removed

```diff
- g = TierProxy(monthly_budget_usd=200, on_usage_pct=80, on_usage_callback=alert)
+ g = TierProxy(monthly_budget_usd=200)
+ # Use Datadog/Grafana for threshold alerts.
```

The `monthly_budget_usd` pre-request guard remains. External monitoring
(Datadog/Grafana/CloudWatch) replaces the in-SDK callback state machine.

#### 2. `tierproxy get` CLI subcommand removed

```diff
- tierproxy get https://example.com --country US
+ python -c "import tierproxy; print(tierproxy.get('https://example.com', country='US').text)"
```

`tierproxy doctor` and `tierproxy usage` remain unchanged.

#### 3. 2 niche AI examples removed

`with_scrapegraphai.py` + `with_gpt_researcher.py` have moved to the GitHub
Discussions community wiki. The 8 most-used framework examples
(LangChain, LlamaIndex, Crawl4AI, Playwright, Firecrawl, Browser-Use,
CrewAI, MCP) remain shipped in the package.

### NON-BREAKING ADDITIONS

- `client.cost_for(resp)` + `client.upstream_for(resp)` — lazy cost attribution
  backed by the new `/v1/usage/recent` gateway endpoint (30s batched cache).
- `cache_ttl=`, `cache_max_size=`, `cache_max_response_size=` kwargs — TTL-aware
  LRU response cache with a size cap (default 256 KiB) to avoid GC pressure.
- `auto_failover=True`, `auto_failover_max_attempts=3` kwargs — retries the
  next-best upstream on 429/5xx/network error.
- `client.rate_limits.get()` returns per-domain rate suggestions sourced from
  gateway-aggregated 429 telemetry.
- `auto_report_429=True` (default) — SDK reports 429s back to the gateway via
  the `X-TierProxy-Report-429` header so the learning loop converges.
- `tls_fingerprint="random|chrome|firefox|safari"` kwarg — gateway-side
  JA3/JA4 rotation via the `X-TierProxy-TLS-Profile` header.
- `session_id` now persists cookies across requests automatically; cookie jars
  are isolated per session ID.
- `stream=True` kwarg returns an httpx streaming context manager (large files,
  SSE pass-through).

### DEPRECATIONS

- `playwright_proxy_config(ProxyURL(mode="headers"))` now warns
  `DeprecationWarning` and silently auto-clones to `mode="username_encoding"`.
  Pass `ProxyURL(..., mode="username_encoding")` explicitly to silence.

### UNCHANGED

- Constructor positional/keyword signatures for `TierProxy()`/`AsyncTierProxy()`
  except for the three removed kwargs above. Existing imports, resource
  surfaces (`client.me`, `client.usage`, `client.health`), retry policy, error
  hierarchy, and `ProxyURL` builder are source-compatible.
- The selector cache (`cache_ttl=30.0` default) stays — it is deliberate
  load-shedding for the `/v1/health/upstreams` endpoint, not magic.

## From Smartproxy

```diff
# Before: Smartproxy URL with modifier suffix
- proxy = "http://customer-USER-cc-US:PASS@gate.smartproxy.com:7000"
- requests.get(target, proxies={"http": proxy, "https": proxy})

# After: tierproxy
+ from tierproxy import ProxyURL
+ proxy = ProxyURL(api_key="tp_live_...", country="US", mode="username_encoding")
+ requests.get(target, proxies={"http": proxy.http_url(), "https": proxy.http_url()})
```

The username-encoding mode produces a Smartproxy-compatible URL shape, so most code only needs the host + auth string change.

## From Bright Data

Bright Data uses `username:password@brd.superproxy.io:22225` style. Swap to:

```python
from tierproxy import ProxyURL
proxy = ProxyURL(api_key="tp_live_...", host="gw.tierproxy.com", port_https=443)
```

Bright Data session zones become tierproxy `session_id`:

```python
proxy = ProxyURL(api_key=..., session_id="zone-static-1", session_duration_minutes=30)
```

## From plain httpx / requests

You don't migrate — you wrap. Keep your existing HTTP stack; just point it at tierproxy:

```python
import httpx
from tierproxy import TierProxy, ProxyURL

g = TierProxy()
proxy = ProxyURL(api_key=g._transport.api_key, country="US")
with httpx.Client(proxy=proxy.http_url(), headers=proxy.headers()) as h:
    r = h.get("https://example.com")
```

Or use the layered API:

```python
import tierproxy
r = tierproxy.get("https://example.com", country="US")
```
