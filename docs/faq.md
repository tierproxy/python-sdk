# FAQ

## How do I get an API key?

Sign up at https://tierproxy.com/signup. Each account starts with a $5 trial credit.

## Sync vs async — which should I use?

If your app already uses asyncio (FastAPI, aiohttp, asyncio.gather), use `AsyncTierProxy`. Otherwise `TierProxy` is fine — sync wraps the same HTTP transport via httpx.

## Does `routing="cheapest"` always pick the cheapest upstream?

It picks the cheapest upstream that's currently **healthy** (state ≠ red, breaker ≠ open). If all upstreams are unhealthy, it picks the highest success-rate as a fallback.

## How is monthly cost calculated?

Per request: `bytes_in + bytes_out` × `upstream.cost_per_gb_usd / 1024^3`. Aggregated daily in DynamoDB; visible via `client.usage.get()`.

## Why does my `with_browser_use.py` keep getting blocked?

Browser-Use uses Playwright. Browsers ignore HTTP headers on CONNECT, so the SDK forces `mode="username_encoding"` in `playwright_proxy_config(...)`. If you're using your own Playwright wiring without the helper, set the proxy username manually with the encoded form.

## Does the CLI work without an API key?

`tierproxy --help` works. Every other subcommand requires either `--api-key` flag or `TIERPROXY_API_KEY` env var.

## What happens at month-end with usage rollovers?

Usage resets at UTC 00:00 on the 1st. Budgets reset at the same time. Sticky session IDs persist (TTL-based, not month-based).

## Can I use tierproxy with self-hosted gateway?

Yes — pass `base_url="https://my-gw.internal:8444"`. SDK works against any tierproxy-compatible REST endpoint.

## What's the difference between `tierproxy.get()` and `client.get()`?

`tierproxy.get()` is the module-level shortcut — uses a lazy singleton client. `client.get()` is the method on an instance you create explicitly. Use `client.get()` whenever you need to override defaults (routing, budgets, custom http_client).

## How do I trace SDK calls with my existing OpenTelemetry setup?

Install with `pip install tierproxy[otel]`, then call `tierproxy.enable_telemetry(service_name="my-app")` at startup. Spans flow to your existing OTLP endpoint.

## Why does my IDE not autocomplete tierproxy methods?

You may have an old version. v0.1.0+ ships `py.typed` so Pylance/mypy/Pyright see the types. Reinstall: `pip install --upgrade tierproxy`.

## Can I revoke an API key?

Yes — in your account dashboard. Revoked keys return 401 within ~5 min (auth cache TTL).

## What's the rate limit?

Default plans get 100 req/sec + 10 MB/sec. Visible per-client via `client.me.get()` (`rate_per_sec`, `bytes_per_sec`).

## How do I report a bug?

GitHub Issues at https://github.com/tierproxy/python-sdk/issues — include `tierproxy doctor` output if relevant.

## Is the gateway code open-source?

The Python SDK + OpenAPI spec are Apache-2.0 licensed and public. The gateway implementation is closed-source by design — that's how we maintain the multi-provider IP routing layer.
