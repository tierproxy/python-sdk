"""Use the tierproxy SDK as tools inside a Claude conversation.

Requires: pip install tierproxy anthropic
Env: TIERPROXY_API_KEY, ANTHROPIC_API_KEY
"""

from __future__ import annotations

import json
from typing import Any

import anthropic
from tierproxy import TierProxy, schemas


def dispatch(tool_name: str, _tool_input: dict[str, Any], gw: TierProxy) -> str:
    if tool_name == "tierproxy_me_get":
        return gw.me.get().model_dump_json()
    if tool_name == "tierproxy_usage_today":
        return gw.usage.get_today().model_dump_json()
    if tool_name == "tierproxy_health_list":
        return json.dumps([h.model_dump() for h in gw.health.list()])
    if tool_name == "tierproxy_rate_limits_get":
        return gw.rate_limits.get().model_dump_json()
    raise ValueError(f"unknown tool: {tool_name}")


def main() -> None:
    anthropic_client = anthropic.Anthropic()
    tools = schemas.anthropic_tools()

    with TierProxy() as gw:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": "How much TierProxy quota do I have left this month?"},
        ]
        while True:
            resp = anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                tools=tools,
                messages=messages,
            )
            if resp.stop_reason != "tool_use":
                # Final answer
                final = next(b for b in resp.content if b.type == "text")
                print(final.text)
                return
            tool_use = next(b for b in resp.content if b.type == "tool_use")
            result = dispatch(tool_use.name, tool_use.input, gw)
            messages.append({"role": "assistant", "content": resp.content})
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": result,
                        }
                    ],
                }
            )


if __name__ == "__main__":
    main()
