"""Use the tierproxy SDK as tools inside an OpenAI chat completion.

Requires: pip install tierproxy openai
Env: TIERPROXY_API_KEY, OPENAI_API_KEY
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from tierproxy import TierProxy, schemas


def dispatch(name: str, _args: dict[str, Any], gw: TierProxy) -> str:
    if name == "tierproxy_me_get":
        return gw.me.get().model_dump_json()
    if name == "tierproxy_usage_today":
        return gw.usage.get_today().model_dump_json()
    if name == "tierproxy_health_list":
        return json.dumps([h.model_dump() for h in gw.health.list()])
    if name == "tierproxy_rate_limits_get":
        return gw.rate_limits.get().model_dump_json()
    raise ValueError(f"unknown tool: {name}")


def main() -> None:
    openai = OpenAI()
    tools = schemas.openai_tools()
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "How much TierProxy quota is left this month?"}
    ]

    with TierProxy() as gw:
        while True:
            resp = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools,
            )
            msg = resp.choices[0].message
            if not msg.tool_calls:
                print(msg.content)
                return
            messages.append(msg.model_dump())
            for call in msg.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                content = dispatch(call.function.name, args, gw)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": content,
                    }
                )


if __name__ == "__main__":
    main()
