"""JSON Schema + LLM tool-definition export for the tierproxy public surface.

Useful when integrating the SDK with AI agents that consume tool definitions
(Claude tool use, OpenAI function-calling, custom MCP-style hosts). The
schemas are derived from the same Pydantic models the SDK uses at runtime,
so they cannot drift.

Example::

    from tierproxy import schemas
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        tools=schemas.anthropic_tools(),
        messages=[{"role": "user", "content": "How much quota is left?"}],
    )
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from tierproxy.resources.health import UpstreamHealth
from tierproxy.resources.me import Me
from tierproxy.resources.ratelimits import RateLimits, RateLimitSuggestion
from tierproxy.resources.usage import Usage, UsageDay, UsageDelta
from tierproxy.resources.usage_recent import Tunnel, UsageRecent

_MODELS: dict[str, type[BaseModel]] = {
    "Me": Me,
    "Usage": Usage,
    "UsageDay": UsageDay,
    "UsageDelta": UsageDelta,
    "UpstreamHealth": UpstreamHealth,
    "RateLimits": RateLimits,
    "RateLimitSuggestion": RateLimitSuggestion,
    "Tunnel": Tunnel,
    "UsageRecent": UsageRecent,
}


def json_schema(model_name: str) -> dict[str, Any]:
    """Return the JSON Schema for one of the SDK's response models.

    Args:
        model_name: One of ``Me``, ``Usage``, ``UsageDay``, ``UsageDelta``,
            ``UpstreamHealth``, ``RateLimits``, ``RateLimitSuggestion``,
            ``Tunnel``, ``UsageRecent``.

    Returns:
        A JSON-Schema (Draft 2020-12) dict.

    Raises:
        KeyError: ``model_name`` is not a known SDK model.
    """
    return _MODELS[model_name].model_json_schema()


_TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "tierproxy_me_get",
        "description": (
            "Fetch the current TierProxy account identity, plan, and"
            " month-to-date usage. Use this before issuing scrapes to"
            " confirm the API key is live and quota has not been"
            " exhausted."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "_output_model": "Me",
    },
    {
        "name": "tierproxy_usage_today",
        "description": ("Get today's bandwidth + cost usage for the authenticated account."),
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "_output_model": "UsageDay",
    },
    {
        "name": "tierproxy_health_list",
        "description": (
            "List recent performance snapshots for every upstream the"
            " account is allowed to route through. Use to choose a stable"
            " provider when smart routing is disabled."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "_output_model": "UpstreamHealth",
    },
    {
        "name": "tierproxy_rate_limits_get",
        "description": (
            "Get current rate-limit suggestions learned by the gateway"
            " for this account's traffic pattern."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "_output_model": "RateLimits",
    },
]


def anthropic_tools() -> list[dict[str, Any]]:
    """Return Anthropic tool-use definitions for the SDK's read endpoints.

    Returns:
        A list of dicts shaped like ``{"name", "description",
        "input_schema"}`` ready to pass as ``tools=`` to
        ``anthropic.Anthropic.messages.create``.
    """
    return [{k: v for k, v in t.items() if not k.startswith("_")} for t in _TOOL_DEFS]


def openai_tools() -> list[dict[str, Any]]:
    """Return OpenAI function-calling tool definitions.

    Returns:
        A list of dicts shaped like
        ``{"type": "function", "function": {"name", "description",
        "parameters"}}`` ready to pass as ``tools=`` to
        ``openai.OpenAI.chat.completions.create``.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in _TOOL_DEFS
    ]


def output_schema_for(tool_name: str) -> dict[str, Any]:
    """Return the JSON Schema describing the response shape of a tool.

    Useful for hosts that want to constrain or validate the SDK call's
    return before sending it back to the model.

    Args:
        tool_name: Name from :func:`anthropic_tools` /
            :func:`openai_tools` (e.g. ``"tierproxy_me_get"``).

    Returns:
        JSON Schema of the corresponding Pydantic model.

    Raises:
        KeyError: ``tool_name`` is unknown.
    """
    spec = next((t for t in _TOOL_DEFS if t["name"] == tool_name), None)
    if spec is None:
        raise KeyError(tool_name)
    return json_schema(spec["_output_model"])


__all__ = [
    "anthropic_tools",
    "json_schema",
    "openai_tools",
    "output_schema_for",
]
