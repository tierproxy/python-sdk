# Security hardening guide

This guide covers the security-relevant behaviour of `tierproxy` (Python SDK). For the gateway-side threat model see `docs/spec/security-threat-model.md` in the main repo.

## API key storage

- **Recommended:** read from a secrets manager into the `TIERPROXY_API_KEY` environment variable at process start.
- **Acceptable:** pass via kwarg `TierProxy(api_key=...)`. Never commit the literal value.
- **Validation:** the SDK rejects keys not matching `^[A-Za-z0-9_.\-]{16,128}$`. See `tierproxy/_internal/validators.py` and the `tests/security/test_api_key_validator.py` suite.
- **Logging:** the SDK never logs the raw key. The `redact` module (`tierproxy/observability/redact.py`) scrubs `Authorization`, `Proxy-Authorization`, `Cookie`, and any userinfo embedded in URLs before structured log output.

## TLS

- `base_url` must be `https://`. The SDK refuses non-https URLs unless you explicitly pass `allow_insecure=True`, which is intended for `http://localhost` against a local dev gateway and nothing else.
- Inner CONNECT preserves TLS end-to-end between SDK and target — the gateway sees only encrypted bytes.
- The gateway listener is pinned to **TLS 1.3 minimum** (see `gateway/internal/server/tls.go`). The SDK uses your system's `ssl` defaults, which on supported Python versions negotiate 1.3 against the gateway.

## Multi-tenant safety

The SDK is single-tenant per `TierProxy` instance. **Don't share one client across users**: every request through the same client is billed and quota-counted to the same API key.

```python
# BAD — all traffic billed to the admin key, all users share quota
client = TierProxy(api_key=admin_key)
for user in users:
    client.get(user.url)

# GOOD — each user is isolated, billed to their own key
for user in users:
    with TierProxy(api_key=user.api_key) as c:
        c.get(user.url)
```

The gateway's cross-tenant guarantees (see `TestCrossTenant_*` in `gateway/test/integration/cross_tenant_test.go`) only hold when the SDK is used this way. If you share a client, you've collapsed all those tenants into one from the gateway's perspective — there's no key to scope against.

## Logging

- The SDK's built-in redaction handles its own request/response logs.
- **If you add custom `httpx` event hooks or your own logging middleware, redact too.** A leaked `Authorization` header in your app's debug log is just as bad as one in ours.
- Useful defaults: never log full request bodies for unknown endpoints; never `pprint` an `httpx.Request` object without first stripping sensitive headers.

## Incident response

If you suspect a key leak (committed publicly, shared accidentally, exposed in logs):

1. Rotate the key immediately from the dashboard, or follow `docs/runbook/key-revocation.md` for the manual path.
2. Audit anything downstream that may have been logged or persisted while the key was live.
3. Confirm rotation took effect: the old key returns **407 Proxy Authentication Required** within 60 s of the revoke (auth cache TTL).
