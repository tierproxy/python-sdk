# Rate-limit learning

The gateway aggregates `429 Too Many Requests` reports per (client, target
domain) and exposes them as a suggested safe rate. The SDK reports 429s back
automatically and surfaces the suggestions for client-side throttling.

## Usage

```python
from tierproxy import TierProxy

with TierProxy(auto_report_429=True) as g:   # auto_report_429=True is default
    g.get("https://hot-target.com/api")    # if it returns 429, SDK reports it

    suggestions = g.rate_limits.get()
    # {
    #   "hot-target.com": 0.5,   # suggested req/sec
    #   "another.com":   2.0,
    # }
    if rate := suggestions.get("hot-target.com"):
        sleep(1.0 / rate)
```

## How it works

1. SDK detects `429` on a response and sends `X-TierProxy-Report-429:
   <target-domain>` on the *next* request to the same gateway. (Out-of-band
   reporting would be 2x the network amplification we already paid to learn
   the 429 was coming.)
2. Gateway tracks the timestamps of 429s per (client, domain) in a sliding
   60-second window.
3. `GET /v1/rate-limits/me` returns `{domain: suggested_req_per_sec}` for the
   calling client. The suggestion is `0.5 * (window_429_count /
   window_seconds)` — half the observed rate of breakage, as a starting
   guess.

## Limitations (honest doc)

- **Self-reported only.** The gateway only knows about 429s that go through
  the gateway. If your script bypasses the gateway for some requests, those
  429s never reach the learner.
- **Per-client.** Suggestions are not shared across clients. If you spin up
  10 clients, each has to learn the same lesson independently.
- **Lossy.** The first 429 report only travels back on the *next* gateway
  request. If you fire one request that 429s and then stop, the gateway
  never learns about it. Mitigation: send a follow-up cheap request to flush
  the report.
- **Domain-level, not URL-level.** Two endpoints on the same domain with
  different limits get the same suggestion. Hand-tune if needed.
- **Suggestion is a guess.** `0.5x` of observed breakage is a heuristic, not
  a guarantee. Targets that 429 at 10 req/s might be safe at 5 req/s, or
  might still 429 at 5 req/s. Use the suggestion as a starting throttle and
  back off further on continued 429s.
- **60-second window.** Reports older than 60 seconds are dropped. Long-tail
  rate limits on slow APIs are not captured.

## When to use

- Polling APIs with unknown per-IP limits — let the gateway aggregate
  before you tune.
- Multi-tenant infra where each customer scrapes different targets — every
  client gets its own learned profile.

## When NOT to use

- One-shot scrapes. Nothing to learn from.
- Targets with documented rate limits — read the docs, set the throttle,
  done.

## Source

- Gateway: `gateway/internal/health/ratelimits.go`,
  `gateway/internal/publicapi/ratelimits.go`
- SDK: `sdks/python/src/tierproxy/resources/ratelimits.py`
