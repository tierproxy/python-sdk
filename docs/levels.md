# The integration ladder

tierproxy exposes a deliberately layered API. Pick the level you need; you can
always graduate later without rewriting.

## Level 0 — One-liner

```python
import tierproxy
r = tierproxy.get("https://example.com", country="US")
```

When to use: throwaway scripts, notebooks, CLI tools.
Behind the scenes: lazy singleton `TierProxy` reads `TIERPROXY_API_KEY`.

## Level 1 — Persistent client

```python
from tierproxy import TierProxy
with TierProxy() as g:
    r = g.get("https://example.com", country="US", session_id="s1")
```

When to use: any script that makes more than ~5 requests.
Benefit: connection pooling, fewer TLS handshakes.

## Level 2 — Smart routing

```python
g = TierProxy(routing="cheapest")
```

When to use: cost-sensitive workloads (LLM RAG scrapes, large datasets).
Strategies: `cheapest`, `fastest`, `most_reliable`, `balanced`.
Behind the scenes: each request calls `SmartSelector.pick()` which caches
`/v1/health/upstreams` for 30s.

## Level 3 — Guardrails

```python
g = TierProxy(
    monthly_budget_usd=200.0,
)
```

When to use: production. Prevents runaway scrape jobs.

## Level 4 — Transport / retry overrides

```python
g = TierProxy(
    retry_policy=RetryPolicy(...),
    http_client=httpx.Client(...),
    user_agent_suffix="my-app/2.3",
)
```

When to use: corporate egress, custom cert pinning, custom instrumentation.

## Level 5 — Raw modes

```python
url = ProxyURL(api_key=..., mode="username_encoding").http_url()
for delta in g.usage.stream(): ...
```

When to use: Playwright (`username_encoding`), live cost dashboards (`stream`).
