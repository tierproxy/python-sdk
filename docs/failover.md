# Multi-provider auto-failover

`auto_failover=True` retries the next-best upstream when the current one
returns 429, 5xx, or fails with a network error. Useful for high-availability
scrapes where ablation across providers is a feature, not a bug.

## Usage

```python
from tierproxy import TierProxy

g = TierProxy(
    auto_failover=True,
    auto_failover_max_attempts=3,   # default
    routing="balanced",             # picks initial upstream
)

r = g.get("https://hot-target.com")  # retries on 429/5xx with next upstream
```

On a retryable error, the SDK calls `selector.pick_next(exclude=tried)` to
choose a different upstream and resends the request transparently. The
response object exposes `r.headers["x-tierproxy-failover-attempts"]` so you
can spot which requests needed retry.

## When to use

- Targets that aggressively rate-limit per IP block — Walmart, Amazon,
  Cloudflare-protected sites.
- Mission-critical scrapes where one upstream provider being degraded should
  not stall the pipeline.
- Workloads with bursty load where a single provider hits its concurrency
  cap before the others.

## When NOT to use

- **Idempotency-sensitive POSTs.** `auto_failover` retries identical
  requests; if your POST is not idempotent (creates a row each call), use
  `auto_failover=False` and handle retries yourself.
- **Tight per-request latency budgets.** Failover doubles or triples the
  worst-case latency. If you have a 5-second SLO, a 3-attempt failover with
  10-second timeouts can blow past it.
- **Single-upstream plans.** If your plan only has one upstream assigned, no
  failover candidate exists; the kwarg silently no-ops.

## Caveats

- Failover does not change the gateway's circuit-breaker state. If all
  upstreams are open-breaker, you still get an error.
- The retry pool is the set of upstreams *currently healthy* per the
  selector cache (default 30s TTL). A provider that went unhealthy 25
  seconds ago is still in the candidate set until the cache refreshes.
- `auto_failover_max_attempts=N` counts the initial request as attempt 1, so
  the maximum upstream changes per request is `N-1`.

## Source

- Selector: `sdks/python/src/tierproxy/proxy/selector.py` (`pick_next()` method)
- Wired in `sdks/python/src/tierproxy/client.py` and `async_client.py`.
