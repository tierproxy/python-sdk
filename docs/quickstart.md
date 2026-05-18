# Quickstart

Get from zero to a proxied request in under five minutes.

## 1. Install

```bash
pip install tierproxy
```

## 2. Configure your API key

The SDK reads `TIERPROXY_API_KEY` from the environment by default:

```bash
export TIERPROXY_API_KEY="tp_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

You can also pass it explicitly:

```python
from tierproxy import TierProxy

client = TierProxy(api_key="tp_live_...")
```

## 3. Inspect your account

```python
from tierproxy import TierProxy

with TierProxy() as client:
    me = client.me.get()
    print(f"client_id       : {me.client_id}")
    print(f"plan            : {me.plan_id}")
    print(f"used (MTD)      : {me.used_bytes_month:,} bytes")
    print(f"quota (monthly) : {me.quota_bytes_month:,} bytes")
    print(f"remaining       : {me.remaining_bytes:,} bytes")
```

## 4. Pull month-to-date usage

```python
with TierProxy() as client:
    usage = client.usage.get()
    for day in usage.days:
        print(day.date, day.bytes_up + day.bytes_down, day.cost_usd)
    print("Total spend:", usage.total_cost_usd)
```

## 5. Stream live usage deltas

```python
with TierProxy() as client:
    for delta in client.usage.stream():
        print(delta.ts, "+", delta.delta_bytes, "B")
```

`stream()` returns an iterator over `usage_delta` SSE events and exits
cleanly when the gateway closes the connection.

## 6. Check upstream health

```python
with TierProxy() as client:
    for upstream in client.health.upstreams():
        print(
            upstream.upstream_id,
            upstream.state,
            upstream.cb_state,
            f"{upstream.success_rate:.2%}",
            f"p95={upstream.latency_p95_ms}ms",
        )
```

## 7. Build a proxy URL for your favourite HTTP client

```python
from tierproxy.proxy.url_builder import ProxyURL

url = ProxyURL(
    api_key="tp_live_...",
    country="US",
    session_id="checkout-42",
).http_url()

import requests
requests.get("https://api.ipify.org", proxies={"http": url, "https": url})
```

## Async

Every API has an `async` twin in `AsyncTierProxy`:

```python
import asyncio
from tierproxy import AsyncTierProxy


async def main() -> None:
    async with AsyncTierProxy() as client:
        me = await client.me.get()
        print(me.client_id)


asyncio.run(main())
```

## Next steps

- Read the full [API reference](./reference.md) for every public class and
  function.
- Browse the `examples/` directory in the repository for end-to-end
  recipes (LangChain, LlamaIndex, Crawl4AI, Playwright, cost-aware
  routing, live usage streaming).
- Tune retries, transports, and routing strategies via the
  `TierProxy(retry_policy=..., routing=..., http_client=...)` knobs.
