# Use tierproxy from Claude Desktop / Cursor / Cline / Windsurf

tierproxy ships an MCP server. Any MCP-aware AI agent can fetch URLs through
your proxy, geo-target by country, and inspect cost in real time — without
writing any glue code.

## Install

```bash
pip install tierproxy[mcp]
```

## Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) / `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "tierproxy": {
      "command": "tierproxy-mcp",
      "env": { "TIERPROXY_API_KEY": "tp_live_..." }
    }
  }
}
```

Restart Claude Desktop. The plug icon should show 4 tools:
`fetch_url`, `get_account_info`, `get_health`, `get_usage`.

## Example prompt

> "Fetch https://example.com from a US IP using tierproxy, then summarize it
> in 3 bullets."

Claude will call `fetch_url(url="https://example.com", country="US")`,
get the response, and produce the summary. Cost: ~1 MB ~= $0.005.

## Cursor / Cline / Windsurf

Same JSON in their respective `mcp.json` config files. See:

- Cursor: Settings -> MCP -> Add server
- Cline: `.clinerules/mcp.json` in workspace
- Windsurf: `~/.windsurf/mcp.json`
