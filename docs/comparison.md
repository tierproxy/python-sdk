# tierproxy vs the field

| Capability | tierproxy | Smartproxy | Bright Data | Oxylabs | DataImpulse |
|---|---|---|---|---|---|
| Multi-provider aggregation | ✅ native | single-provider | single-provider | single-provider | single-provider |
| Client-side smart routing (cheapest/fastest/most_reliable) | ✅ built-in | manual | manual | manual | manual |
| Live SSE usage stream | ✅ | ❌ | ❌ | ❌ | ❌ |
| MCP server (Claude/Cursor/Cline) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Pre-built AI/ML framework examples | 10 | 0 | 1 (LangChain) | 0 | 0 |
| OpenAPI 3.1 spec | ✅ | ❌ | ❌ | ❌ | ❌ |
| OpenTelemetry built-in | ✅ opt-in extra | ❌ | ❌ | ❌ | ❌ |
| Pip-installable CLI | ✅ `tierproxy` | ❌ | ❌ | ❌ | ❌ |
| License | Apache-2.0 (this SDK) | proprietary | proprietary | proprietary | proprietary |
| Sync + async parity | ✅ | partial | partial | partial | partial |
| Built-in budget guardrails | ✅ | ❌ | ❌ | ❌ | ❌ |

## When to pick which

- **You're an AI/ML engineer scraping for RAG** → tierproxy. The cookbook page has 5 ready recipes for the popular frameworks; no other vendor ships these.
- **You're locked into a single provider's contract** → use that vendor's SDK directly; tierproxy is built for multi-provider aggregation.
- **You need browser automation with proxy** → tierproxy + Playwright via `playwright_proxy_config` (see [cookbook recipe 3](cookbook.md#3-playwright-browser-through-tierproxy)).
- **You're cost-sensitive** → tierproxy's `routing="cheapest"` is unique; no competitor selects upstream by price per request.
- **You need observability** → only tierproxy ships OpenTelemetry today.
