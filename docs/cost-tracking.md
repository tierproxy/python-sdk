# Per-request cost attribution

`client.cost_for(resp)` returns the dollar cost of a specific response,
attributed to the upstream that served it. Useful for chargeback, per-tenant
billing, A/B comparison of routing strategies, and cost dashboards.

## Motivation

Pricing in residential proxy is per-byte and the price is upstream-dependent.
Without per-request attribution you cannot answer "did the `cheapest`
routing strategy actually save money this week?" The v0.2.0 API exposes the
gateway's own accounting on a per-tunnel basis.

## Usage

```python
from tierproxy import TierProxy

with TierProxy() as g:
    r = g.get("https://example.com", country="US")
    print(g.cost_for(r), "USD")
    print(g.upstream_for(r), "upstream")
```

`cost_for(resp)` and `upstream_for(resp)` are lazy — the first call within a
30-second window fetches `/v1/usage/recent` once and caches the last 100
tunnels for the client. Subsequent calls in the same window are pure
in-memory dict lookups and add no network traffic.

## How it works

1. Gateway pushes a `RecentTunnel{client_id, upstream_id, target_host,
   bytes_up, bytes_down, cost_usd, duration_ms, timestamp}` to a ring buffer
   after each CONNECT tunnel closes.
2. SDK calls `/v1/usage/recent` on first `cost_for()` after the 30s window
   expires.
3. SDK matches `resp` to its tunnel by (request timestamp, target host,
   request id). The match is heuristic — see caveats.

## Caveats

- **30-second eventual consistency.** Calling `cost_for()` immediately after
  a request may return `None` if the gateway has not yet flushed the tunnel
  to the ring. Retry, or batch your reads.
- **Ring buffer holds last 100 tunnels per client.** Older tunnels are
  evicted and `cost_for()` will return `None` for them.
- **Match heuristic.** If you fire 50 requests to the same `target_host` in
  the same 100ms window, the SDK cannot disambiguate which response maps to
  which ring entry. Total cost across the batch is correct; per-response
  attribution may shuffle.
- **No retroactive backfill.** Switching `cost_for()` on mid-session does not
  attribute the requests already fired; the ring only knows tunnels since
  startup.
- **Lazy by design.** There is no per-request callback. If you want a hot
  feedback loop, poll `/v1/usage/recent` yourself on a 30-second timer.

## Cost of the cost feature itself

`/v1/usage/recent` returns ~100 rows × ~120 bytes = ~12 KB JSON per fetch.
With the 30-second cache that is ~24 KB/minute or ~35 MB/month per client
even under continuous polling. Negligible vs. the proxy bandwidth itself.

## Source

- Gateway: `gateway/internal/publicapi/usage_recent.go`
- SDK: `sdks/python/src/tierproxy/_internal/cost.py`,
  `sdks/python/src/tierproxy/resources/usage_recent.py`
