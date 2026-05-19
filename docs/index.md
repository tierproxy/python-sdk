# tierproxy Python SDK

Official Python SDK for [tierproxy](https://github.com/tierproxy/python-sdk) — a
premium multi-provider proxy gateway built for AI/ML data-collection
pipelines. The SDK wraps the public REST API (`/v1/me`, `/v1/usage/me`,
`/v1/usage/me/stream`, `/v1/health/upstreams`) and ships ready-to-use
adapters for the most popular Python HTTP clients and scraping frameworks.

```{toctree}
:maxdepth: 2
:caption: Contents

quickstart
levels
cookbook
errors
caching
cost-tracking
failover
rate-limit-learning
tls-fingerprint
cookies-streaming
observability
ai-integration
codegen
security
comparison
faq
migration
troubleshooting
reference
```

## Install

```bash
pip install tierproxy
```

Optional extras:

```bash
pip install "tierproxy[requests]"   # adapter for the `requests` library
pip install "tierproxy[docs]"       # build the documentation locally
```

## At a glance

```python
from tierproxy import TierProxy

with TierProxy() as client:
    me = client.me.get()
    print(me.client_id, me.used_bytes_month, "of", me.quota_bytes_month)
```

The SDK supports both synchronous (`TierProxy`) and asynchronous
(`AsyncTierProxy`) usage, exposes a typed exception hierarchy, includes a
configurable retry policy with exponential backoff + jitter, and streams
live usage deltas via Server-Sent Events.

See the [Quickstart](./quickstart.md) for a 5-minute walkthrough and the
[API reference](./reference.md) for the complete public surface.

## Performance

`ProxyURL` builds in well under 1 µs (basic), ~2 µs with full modifiers.
The smart `pick` selector chooses from 100 upstreams in ~17 µs, 1000 upstreams
in ~60 µs. See [benchmarks](https://github.com/tierproxy/python-sdk/tree/main/sdks/python/benchmarks).

## Indices

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
