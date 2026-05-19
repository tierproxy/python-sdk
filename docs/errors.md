# Errors reference

Every SDK error inherits from `tierproxy.TierProxyError` and carries a
`request_id` plus the original RFC 7807 problem+json body for forensic
inspection.

## HTTP status → exception mapping

| HTTP | Exception | Typical cause | Remedy |
|------|-----------|---------------|--------|
| 400 | `ValidationError` | Country / session combination not allowed by plan | Inspect `error.problem['detail']`; remove the offending kwarg |
| 401 | `AuthenticationError` | API key missing, wrong, or revoked | Check `TIERPROXY_API_KEY` or `api_key=` |
| 403 | `PermissionError` | Account suspended or feature gated | Check billing / plan |
| 404 | `NotFoundError` | Upstream / account-resource path wrong | Verify ID — 404s from *target* sites are NOT this exception |
| 409 | `ConflictError` | Resource-state collision | Check `problem['detail']` |
| 429 | `RateLimitError` | Rate or bandwidth ceiling hit | Respect `error.retry_after`; consider plan upgrade |
| 5xx | `ServerError` | Gateway internal | Retried automatically; check status.tierproxy.com |
| — | `TimeoutError` | Local timeout exceeded | Raise `http_timeout` or `timeout` |
| — | `ConnectionError` | DNS / firewall / TLS handshake failed | Check network; `allow_insecure=True` for HTTP base |

## Handling patterns

### Single catch-all for retry-or-log

```python
from tierproxy import TierProxy, TierProxyError

with TierProxy() as g:
    try:
        resp = g.get("https://example.com/page")
    except TierProxyError as e:
        log.error("tierproxy failed", request_id=e.request_id, detail=e.problem)
        raise
```

### Discriminate on rate limits

```python
import time
from tierproxy import TierProxy, RateLimitError

with TierProxy() as g:
    try:
        resp = g.get("https://example.com/page")
    except RateLimitError as e:
        time.sleep(e.retry_after or 5)
        resp = g.get("https://example.com/page")
```

### Use `request_id` when escalating

Every exception exposes `error.request_id`. Always include it in support
tickets — it's the join key between your client logs and the gateway's
request trail.

```python
from tierproxy import TierProxy, TierProxyError

with TierProxy() as g:
    try:
        resp = g.get("https://example.com")
    except TierProxyError as e:
        raise RuntimeError(
            f"tierproxy {e.status_code} (request_id={e.request_id!r}): {e.message}"
        ) from e
```

## Retry behavior

The default `RetryPolicy` retries 429, 500, 502, 503, 504, and the
transient network exceptions (`httpx.ConnectError`, `NetworkError`,
`TimeoutException`). Backoff is exponential with jitter:
`base * (2 ** attempt) * uniform(0.5, 1.5)`, capped at `cap`.

That means `ServerError`, `RateLimitError`, and `ConnectionError` reach
your code only after retries are exhausted. To disable retries entirely:

```python
from tierproxy import TierProxy, RetryPolicy

with TierProxy(retry_policy=RetryPolicy(max_retries=0)) as g:
    ...
```

See [RetryPolicy](./reference.md) in the API reference for the full
field set.
