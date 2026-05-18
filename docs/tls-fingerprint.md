# JA3/JA4 TLS fingerprint rotation

The gateway randomizes its outbound TLS ClientHello per request to defeat
JA3/JA4-based anti-bot systems (Akamai, Cloudflare). The SDK exposes the
profile selector as a request kwarg or module default.

## Motivation

JA3 fingerprints the TLS ClientHello bytes; JA4 (introduced by Akamai
in Feb 2026) extends that to include ALPN, extensions, and cipher ordering.
A vanilla Go `crypto/tls` ClientHello is a single, well-known fingerprint
that targets can block in one rule. Mimicking the ClientHello of Chrome,
Firefox, or Safari makes the gateway indistinguishable from a real browser
at the TLS layer.

## Usage

```python
import tierproxy

# Per-request profile
r = tierproxy.get("https://example.com", tls_fingerprint="chrome")

# Default for the whole client
from tierproxy import TierProxy
g = TierProxy(tls_fingerprint="random")
g.get("https://target.com")  # rotates ClientHello on every outbound dial
```

Profiles: `chrome` (default), `firefox`, `safari`, `random` (rotates each
request).

## How it works

The gateway uses [`refraction-networking/utls`](https://github.com/refraction-networking/utls)
to construct ClientHello bytes matching the chosen browser preset. The SDK
sends the `X-TierProxy-TLS-Profile: <name>` header on each CONNECT; the
gateway picks the matching uTLS preset before dialing the upstream.

## Caveats

- **HTTPS only.** Plain-HTTP forward proxying does not negotiate TLS, so
  there is no ClientHello to spoof.
- **`random` rotates per outbound dial, not per pool slot.** A socket
  already pre-dialed in the pool keeps its original ClientHello until it is
  reaped. With the default pool `idleTimeout=90s`, rotation is bounded.
- **HTTP/2 ALPN.** uTLS handles ALPN advertisement for each preset, but not
  every combination is exercised in CI. Open an issue if you hit a target
  that detects an HTTP/2 mismatch.
- **The target still sees the upstream's IP and User-Agent.** TLS
  fingerprint rotation is necessary but not sufficient. Pair it with
  `country=` rotation, sticky `session_id` lifecycle management, and a
  realistic `User-Agent` header.
- **Browser presets drift.** Real Chrome updates its ClientHello every few
  releases; the uTLS preset lags. The gateway pins to a specific preset
  version per release — check `gateway/internal/pool/tls_profile.go` for
  the current pin.

## Source

- Gateway: `gateway/internal/pool/tls_profile.go`
- SDK: `tls_fingerprint=` kwarg on `client.get()` and the module-level
  convenience functions.
