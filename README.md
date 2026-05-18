# tierproxy — Python SDK

<!-- mcp-name: io.github.tierproxy/python-sdk -->

> 🚧 **Preview release.** Gateway is not yet generally available. Join the
> waitlist at hello@tierproxy.com. SDK is functional but `tierproxy doctor`
> against a live gateway requires invitation.

[![PyPI version](https://img.shields.io/pypi/v/tierproxy.svg?logo=python&logoColor=white)](https://pypi.org/project/tierproxy/)
[![Python versions](https://img.shields.io/pypi/pyversions/tierproxy.svg)](https://pypi.org/project/tierproxy/)
[![Downloads](https://static.pepy.tech/badge/tierproxy/month)](https://pepy.tech/project/tierproxy)
[![CI](https://github.com/tierproxy/python-sdk/actions/workflows/test.yml/badge.svg)](https://github.com/tierproxy/python-sdk/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/tierproxy/python-sdk/branch/main/graph/badge.svg)](https://codecov.io/gh/tierproxy/python-sdk)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![OpenAPI 3.1](https://img.shields.io/badge/OpenAPI-3.1-6BA539?logo=openapiinitiative)](https://github.com/tierproxy/python-sdk/blob/main/openapi/tierproxy.v1.yaml)
[![MCP compatible](https://img.shields.io/badge/MCP-compatible-blueviolet?logo=anthropic)](#mcp-server-claude-desktop--cursor--cline--windsurf)

Premium multi-provider proxy infrastructure for AI/ML pipelines. Built for engineers who measure cost, latency, and success rate twice — and write Python.

## Install

```bash
pip install tierproxy
```

## Quickstart — five-second flavor

```python
import tierproxy
r = tierproxy.get("https://example.com", country="US")
print(r.text)
```

That's it. (Set `TIERPROXY_API_KEY` env var first.)

## Three lines, persistent session

```python
from tierproxy import TierProxy
with TierProxy() as g:
    print(g.me.get().client_id)
    r = g.get("https://example.com", country="US", session_id="s1")
```

## Auto-pick the cheapest healthy upstream every request

```python
g = TierProxy(routing="cheapest")  # also: "fastest", "most_reliable", "balanced"
g.get("https://example.com")     # picks via /v1/health/upstreams under the hood
```

## Cost guardrails

```python
g = TierProxy(
    monthly_budget_usd=200.0,    # raises BudgetExceededError before going over
)
```

## Power-user knobs

```python
import httpx
from tierproxy import TierProxy
from tierproxy.retry import RetryPolicy

g = TierProxy(
    api_key="tp_live_...",
    base_url="https://my-self-hosted-gw:8444",
    timeout=10.0,
    retry_policy=RetryPolicy(max_retries=5, retry_on_status=frozenset({500, 502})),
    http_client=httpx.Client(verify=False),  # custom transport
    user_agent_suffix="my-app/2.3",          # attribution
)
```

## Raw modes (Playwright, curl, etc.)

```python
from tierproxy import ProxyURL

p = ProxyURL(api_key="tp_live_...", country="US", mode="username_encoding")
print(p.http_url())  # http://customer-tp_live_...-cc-US:x@gw.tierproxy.com:443
```

## How tierproxy compares

| | tierproxy | Smartproxy SDK | Bright Data SDK | Oxylabs SDK | DataImpulse |
|---|---|---|---|---|---|
| Multi-provider routing | ✅ | ❌ | ❌ | ❌ | ❌ |
| Client-side smart selector (cost-aware) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Live usage streaming (SSE) | ✅ | ❌ | ❌ | ❌ | ❌ |
| MCP server (Claude/Cursor/Cline) | ✅ | ❌ | ❌ | ❌ | ❌ |
| OpenTelemetry built-in | ✅ | ❌ | ❌ | ❌ | ❌ |
| Sync + async parity | ✅ | partial | partial | partial | partial |
| AI/ML framework examples shipped | 8 | 0 | 1 | 0 | 0 |
| Type-safe (Pydantic v2 + mypy strict) | ✅ | ❌ | ❌ | partial | ❌ |
| OpenAPI 3.1 spec | ✅ | ❌ | ❌ | ❌ | ❌ |
| Pip-installable CLI (`tierproxy doctor`) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Per-request cost attribution (lazy) | ✅ | ❌ | ❌ | ❌ | ❌ |
| JA3/JA4 TLS fingerprint rotation | ✅ | ❌ | ❌ | ❌ | ❌ |
| Rate-limit learning + auto-failover | ✅ | ❌ | ❌ | ❌ | ❌ |
| License | Apache 2.0 | proprietary | proprietary | proprietary | proprietary |

## Features

- **Five-second quickstart** — `import tierproxy; tierproxy.get(url, country="US")`
- **Layered API** — five integration levels from one-liner to power-user knobs
- **Smart routing** — `routing="cheapest"` auto-picks healthy upstream per request
- **Cost guardrails** — `monthly_budget_usd=` refuses requests that would exceed budget
- **Per-request cost attribution** — `client.cost_for(resp)` returns USD; lazy 30s cache, no per-request overhead
- **Client-side response caching** — `cache_ttl=300, cache_max_response_size=262144` LRU with size cap
- **Multi-provider auto-failover** — `auto_failover=True` retries with next-best upstream on 429/5xx
- **Rate-limit learning** — `client.rate_limits.get()` surfaces gateway-aggregated 429s per target domain
- **JA3/JA4 TLS rotation** — per-upstream fingerprint randomization (gateway side; see [tls-fingerprint guide](docs/tls-fingerprint.md))
- **Cookie persistence** — cookies stick to `session_id` across multi-step crawls
- **Streaming responses** — `client.get(url, stream=True)` returns iterator (large files, SSE)
- **Live SSE stream** — `for delta in g.usage.stream()` tails month-to-date bytes
- **MCP server** — `tierproxy-mcp` exposes proxy as tools to Claude/Cursor/Cline
- **8 framework integrations** — LangChain, LlamaIndex, Crawl4AI, Playwright, Firecrawl, Browser-Use, CrewAI
- **OpenTelemetry opt-in** — `pip install tierproxy[otel]` for distributed tracing
- **Geo + sticky sessions** — countries, cities, 1-1440min session pins
- **Dual URL syntax** — headers (httpx/requests) AND username-encoding (Playwright)
- **Type-safe end-to-end** — Pydantic v2 models, mypy strict, full IDE autocomplete

See [examples/](./examples) for LangChain/LlamaIndex/Crawl4AI/Playwright and
[`examples/levels.py`](./examples/levels.py) for a runnable demo of every level.

## Use with your favorite AI/agent framework

| Framework | Example | Notes |
|---|---|---|
| **LangChain** | [`with_langchain.py`](./examples/with_langchain.py) | RAG document loaders through proxy |
| **LlamaIndex** | [`with_llamaindex.py`](./examples/with_llamaindex.py) | SimpleWebPageReader through proxy |
| **Crawl4AI** | [`with_crawl4ai.py`](./examples/with_crawl4ai.py) | Playwright crawler + tierproxy |
| **Firecrawl** (hot) | [`with_firecrawl.py`](./examples/with_firecrawl.py) | Self-hosted Firecrawl + residential IPs |
| **Browser-Use** (hot) | [`with_browser_use.py`](./examples/with_browser_use.py) | LLM-driven autonomous browser |
| **CrewAI** (hot) | [`with_crewai.py`](./examples/with_crewai.py) | Multi-agent scraper crew + cost-aware routing |
| **Playwright** | [`with_playwright.py`](./examples/with_playwright.py) | Direct Playwright with tierproxy |
| **MCP (Claude/Cursor/Cline/Windsurf)** (unique) | [`mcp_claude_desktop.md`](./examples/mcp_claude_desktop.md) | Native tool integration via `tierproxy-mcp` |

## MCP server (Claude Desktop / Cursor / Cline / Windsurf)

```bash
pip install tierproxy[mcp]
```

Then add to your MCP client config:

```json
{
  "mcpServers": {
    "tierproxy": {
      "command": "tierproxy-mcp",
      "env": { "TIERPROXY_API_KEY": "tp_live_..." }
    }
  }
}
```

Now your AI assistant can call `fetch_url(url, country="US")`, inspect health
and usage, and route through the cheapest healthy upstream — no glue code,
no httpx imports, no boilerplate.
