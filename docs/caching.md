# Response caching

The SDK can cache `200 OK` GET responses client-side in a TTL-aware LRU. This
saves both bandwidth and gateway cost for workloads that re-fetch the same
URLs (price monitoring, polling APIs, debugging).

## Motivation

Proxy bandwidth is the dominant line item in residential-proxy economics
(see [cost-tracking](./cost-tracking.md)). A 30-second cache on a polling
loop that hits the same URL every second cuts upstream cost by ~97% without
changing application code.

## Usage

```python
from tierproxy import TierProxy

g = TierProxy(
    cache_ttl=300,              # seconds; 0 disables (default)
    cache_max_size=1024,        # max distinct URLs kept in the LRU
    cache_max_response_size=262144,  # 256 KiB per response (default)
)

r1 = g.get("https://api.example.com/prices")   # cache miss → upstream
r2 = g.get("https://api.example.com/prices")   # cache hit → 0 cost
```

The cache key includes the URL plus relevant request kwargs (`country`,
`session_id`, `params`). Headers and bodies are not part of the key — pass
distinct URLs for distinct logical fetches.

## Caveats

- **GET only.** POST/PUT/DELETE are never cached.
- **Status 200 only.** 3xx/4xx/5xx are not cached (no negative caching in v0.2.0).
- **Size cap.** Responses larger than `cache_max_response_size` bypass the
  cache silently. The default 256 KiB cap protects the process from GC
  pressure when an unexpected `.zip` or video URL slips into a polling loop.
  Raise it explicitly if you understand the memory cost.
- **No conditional requests.** The SDK does not send `If-None-Match` /
  `If-Modified-Since` on cache miss; this is a pure local cache, not an
  HTTP-spec cache.
- **No cross-process sharing.** Each `TierProxy` instance has its own LRU.
  Restart loses the cache.
- **Streaming bypasses cache.** `stream=True` always re-fetches; see
  [cookies-streaming](./cookies-streaming.md).

## When NOT to use

- Endpoints that change every request (search results, captcha, login).
- Endpoints where freshness matters more than cost (real-time prices, auction
  data). Use `cache_ttl=0` (default) or skip the cache layer entirely.

## Source

- `sdks/python/src/tierproxy/_internal/cache.py`
- Wired in `sdks/python/src/tierproxy/client.py` and `async_client.py`.
