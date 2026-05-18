# Changelog
## [0.3.0] — Security hardening

### BREAKING CHANGES
- `base_url` must be `https://` unless `allow_insecure=True`.
- `api_key` validated against `^[A-Za-z0-9_.-]{16,128}$` at construction time. Short test keys (e.g. `"tp"`) now raise `ValueError`. Use a 16+ char dummy in tests.
- Proxy URL builder URL-encodes every modifier. `ProxyURL.http_url()` output differs for keys containing reserved chars (now safely percent-encoded).
- Runtime dependencies pinned to exact versions (`httpx==0.28.1`, `pydantic==2.13.4`, `httpx-sse==0.4.3`). Use Dependabot to track security patches.

### Added
- `tierproxy.observability.redact` — header / URL redactor for safe logging.
- `tierproxy._internal.validators` — shared `validate_api_key`, `validate_base_url`.
- `tests/security/` — URL injection, base_url guard, api_key regex, redaction tests.
- `docs/security.md` — SDK hardening guide.
- `uv.lock` + `requirements.lock` shipped with hashes.

### Gateway (co-versioned in `gateway/` of source repo, not on PyPI)
- Inline mid-stream quota enforcement in `CountedReader` (no goroutine watchdog).
- Versioned HMAC pepper with dual-read rotation window (`auth.PepperProvider`, `auth.VersionedHasher`).
- Auth cache TTL 60s; negative lookups never cached. Revocation SLO ≤60s.
- `ConditionExpression` w/ monotonic `seq` on USAGE writes.
- Per-client token bucket on `/v1/*`; per-key dial-rate limit on data plane.
- TLS 1.3 minimum on listener.
- CONNECT target whitelist (no RFC1918 in prod, no metadata IPs, no admin ports).
- Minimal X-* header whitelist.
- 5-min idle deadlines on tunnel conns.
- IAM split: read-only auth path (APIKEY/CLIENT/PLAN) + write-only usage path (CLIENT#USAGE attrs).
- KMS CMK reserved (envelope encryption deferred until first PII lands).
- Cross-tenant integration suite (`gateway/test/integration/cross_tenant_test.go`).

### Deferred (documented in docs/runbook/pepper-rotation.md)
- Pepper rehash CLI (waits for control-plane vault).
- CLIENT attribute envelope decryption (waits for first paying customer).
- DDB Streams revocation Lambda (60s cache TTL covers the same SLO at ~$1/mo vs ~$10/mo).
- Flusher concurrency fix: `ConditionExpression` on byte ADDs can cause lost updates under high concurrency to the same `(client, day)` key. Tracked as follow-up.
- SOCKS5 path not wired into flusher: bytes counted in memory only, not persisted to DDB. Tracked as follow-up.

## [0.2.0] — Feature audit + breaking refactor

### BREAKING CHANGES
- Remove `on_usage_pct` + `on_usage_callback` (external monitoring instead)
- CLI: `tierproxy get` removed (keep `doctor` + `usage`)
- 2 niche AI examples removed (ScrapeGraphAI + GPT-Researcher → community wiki)

### Added
- `client.cost_for(resp)` + `client.upstream_for(resp)` — lazy 30s-cached attribution
- `cache_ttl=`, `cache_max_response_size=` kwargs (LRU response cache; 256KB default size cap)
- `auto_failover=True` retries next-best upstream on 429/5xx/network error
- `client.rate_limits.get()` returns per-domain rate suggestions
- `tls_fingerprint="chrome|firefox|safari|random"` kwarg (JA3/JA4 rotation via uTLS on gateway)
- Cookies persist automatically across requests with same `session_id`
- `stream=True` kwarg returns httpx streaming context manager
- Gateway endpoints: `GET /v1/usage/recent`, `GET /v1/rate-limits/me`
- OpenAPI spec bumped to 1.1.0

### Deprecated
- `playwright_proxy_config(ProxyURL(mode="headers"))` warns DeprecationWarning + auto-clones to username_encoding (silent fix)

### Unchanged
- SmartSelector default `cache_ttl=30.0` (deliberate load-shedding, NOT magic)
- `enable_telemetry()` explicit opt-in (consistency with other auto-magic cuts)

## [0.1.1] — MCP Registry submission
- Add `mcp-name` marker in README for PyPI ownership verification
- Add `server.json` describing MCP server tools + PyPI package
- No code changes

## [0.1.0] — Initial release
- Management client (sync + async): `client.me.get()`, `client.usage.get()`, `client.usage.stream()`, `client.health.upstreams()`
- `ProxyURL` builder (header mode + username-encoding mode)
- Client-side cost-aware smart selector
- LangChain, LlamaIndex, Crawl4AI, Playwright examples
