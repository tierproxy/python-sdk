"""tierproxy MCP server.

Exposes ``fetch_url``, ``get_account_info``, ``get_health``, and ``get_usage``
tools to any Model Context Protocol client (Claude Desktop, Cursor, Cline,
Windsurf, Continue.dev).

Run: ``tierproxy-mcp`` (stdio transport — what Claude Desktop expects).
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from tierproxy import TierProxy
from tierproxy._version import __version__


def build_server(api_key: str | None = None) -> Server:
    """Wire a fresh MCP ``Server`` with all four tierproxy tools registered."""
    server: Server = Server("tierproxy")
    client = TierProxy(api_key=api_key)

    @server.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="fetch_url",
                description=(
                    "Fetch a URL through tierproxy. Returns the response body as text. "
                    "Use 'country' for geo-targeting (ISO-2), 'session_id' for sticky "
                    "sessions across multiple fetches."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["url"],
                    "properties": {
                        "url": {"type": "string", "description": "Target URL"},
                        "country": {
                            "type": "string",
                            "description": "ISO-2 country code (e.g. US, GB, JP)",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Sticky session ID — same IP across calls",
                        },
                        "timeout": {"type": "number", "default": 30},
                    },
                },
            ),
            types.Tool(
                name="get_account_info",
                description=(
                    "Return account info: client_id, plan, monthly quota, used bytes, "
                    "allowed upstreams."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="get_health",
                description=(
                    "Return live RED metrics (success_rate, latency_p95_ms, "
                    "cost_per_gb_usd) per upstream. Useful for agents deciding which "
                    "region/provider to use."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="get_usage",
                description=(
                    "Return month-to-date usage + cost in USD. Useful for budget-aware agents."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()  # type: ignore[untyped-decorator]
    async def call_tool(name: str, args: dict[str, Any]) -> list[types.TextContent]:
        if name == "fetch_url":
            url = args["url"]
            kw = {k: v for k, v in args.items() if k != "url"}
            r = client.get(url, **kw)
            return [types.TextContent(type="text", text=r.text)]
        if name == "get_account_info":
            me = client.me.get()
            return [types.TextContent(type="text", text=me.model_dump_json())]
        if name == "get_health":
            ups = client.health.upstreams()
            payload = "[" + ",".join(u.model_dump_json() for u in ups) + "]"
            return [types.TextContent(type="text", text=payload)]
        if name == "get_usage":
            u = client.usage.get()
            return [types.TextContent(type="text", text=u.model_dump_json())]
        raise ValueError(f"unknown tool {name!r}")

    return server


def main() -> int:
    api_key = os.environ.get("TIERPROXY_API_KEY")
    if not api_key:
        sys.stderr.write("TIERPROXY_API_KEY env var required\n")
        return 1

    async def _run() -> None:
        server = build_server(api_key)
        async with mcp.server.stdio.stdio_server() as (read, write):
            await server.run(
                read,
                write,
                InitializationOptions(
                    server_name="tierproxy",
                    server_version=__version__,
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
