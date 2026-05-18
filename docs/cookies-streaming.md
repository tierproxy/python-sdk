# Cookies + streaming responses

Two related capabilities that ship together in v0.2.0: per-session cookie
persistence and `stream=True` for large or open-ended responses.

## Cookies persistence

When you set `session_id`, the SDK persists cookies received in each
response and replays them on subsequent requests with the same `session_id`:

```python
from tierproxy import TierProxy

with TierProxy() as g:
    # Step 1: login — sets cookies on the gateway side and in the SDK jar
    g.post("https://shop.example.com/login",
           json={"u": "...", "p": "..."},
           session_id="login-1")

    # Step 2: cart — SDK replays cookies received in step 1
    r = g.get("https://shop.example.com/cart", session_id="login-1")
```

Cookie jars are keyed by `session_id`. Different IDs are fully isolated, so
a parallel scraping crew with one `session_id` per worker has no
cross-contamination.

To clear:

```python
g.cookies.clear("login-1")    # forget one session
g.cookies.clear_all()         # forget everything
```

### Caveats

- Cookies set without `session_id` are not persisted (each request is
  independent).
- The jar respects `Domain`, `Path`, `Expires`, `Max-Age`, `Secure`, and
  `HttpOnly` attributes. It does not implement the full RFC 6265 public
  suffix list — set-cookie from a public suffix domain (e.g. `.co.uk`) is
  treated as belonging to the exact domain.
- Jar is in-memory only. Pickle the session yourself if you need to
  persist across process restart.

## Streaming responses

For large file downloads, multi-MB HTML pages, or SSE pass-through, use
`stream=True`:

```python
with g.get("https://example.com/big.iso", stream=True) as r:
    for chunk in r.iter_bytes(chunk_size=8192):
        process(chunk)
```

`stream=True` returns the response *without* buffering the body. Caller must
iterate via `iter_bytes()` or `iter_text()` and either use the response as a
context manager or call `.close()` manually.

### Async

```python
async with g.stream("GET", "https://example.com/big.iso") as r:
    async for chunk in r.aiter_bytes(chunk_size=8192):
        await process(chunk)
```

### Caveats

- **`cost_for(resp)` works on streamed responses too.** The cost is
  bytes-based on the gateway side, so iterating a stream still updates the
  ring buffer (see [cost-tracking](./cost-tracking.md)).
- **`cache_ttl` does NOT cache streaming responses.** There is no body to
  cache. Re-fetching a streamed URL re-streams from upstream.
- **Always iterate or close.** A leaked streaming response holds an open
  socket from the gateway pool until the OS reclaims it. The pool
  `idleTimeout` (default 90s) bounds the leak, but tight pools can starve.
- **`auto_failover` is best-effort for streams.** If the underlying
  connection drops mid-body, the SDK cannot transparently restart the
  stream from where it left off (HTTP `Range` is not auto-added). The
  caller sees a `httpx.ReadError` and is responsible for resume logic.

## Source

- Cookies: `sdks/python/src/tierproxy/_internal/cookies.py`
- Streaming: `sdks/python/src/tierproxy/_internal/streaming.py`
- Wired into both sync and async clients.
