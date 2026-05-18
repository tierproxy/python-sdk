# Troubleshooting

## `tierproxy doctor` first

Always start with:

```bash
tierproxy doctor
```

Output shows: auth status, upstream health (RED metrics), and current usage.

## 401 Unauthorized

- Verify `TIERPROXY_API_KEY` env var is set + the key starts with `tp_live_` or `tp_test_`.
- Confirm key isn't revoked — log in to dashboard.
- Check your system clock — large clock skew breaks Cognito JWT validation in the public API.

## 403 Forbidden on a specific country

`allowed_upstreams` in your plan may not include any upstream that serves that country. Check `client.me.get().allowed_upstreams` + `client.health.upstreams()` to see which upstreams handle which geos.

## Slow first request

The HTTPS handshake to the gateway warms a TLS session. Subsequent requests reuse it. Persistent client (`with TierProxy() as g: ...`) avoids re-handshake.

## Connection timeouts

Network path between you and `gw.tierproxy.com:443` is blocked. Tools: `curl -v https://gw.tierproxy.com:443/`. Confirm corporate egress, VPN, or local firewall isn't dropping CONNECT.

## `global is not defined` (in browser bundlers)

This is a Vite/Webpack issue unrelated to tierproxy. The Python SDK runs in Python only; if you see this error, you're trying to bundle tierproxy into a browser. Don't — use the gateway's REST endpoint directly.

## MCP server doesn't show in Claude Desktop

After editing `claude_desktop_config.json`, fully quit + restart Claude Desktop (not just close the window). The 🔌 icon at the bottom-left should show `tierproxy`.

## "BudgetExceededError"

You set `monthly_budget_usd=` and the per-request cost estimate would push you over. Raise the budget, or check usage:

```python
print(g.usage.get().total_cost_usd)
```

## OTel spans not showing up

- Verify `pip install tierproxy[otel]`.
- Verify `tierproxy.enable_telemetry(service_name="...")` was called BEFORE any SDK request.
- Verify your OTLP exporter env vars (`OTEL_EXPORTER_OTLP_ENDPOINT`, etc.) are set.
