# AI agent integration

TierProxy's primary persona is engineers building AI/ML data-collection
pipelines. Letting an LLM call the SDK directly — instead of wrapping
every call in glue code — is the fastest path to a working agent.

The SDK exposes three integration surfaces:

1. **Anthropic Claude tool use** — `schemas.anthropic_tools()`
2. **OpenAI function calling** — `schemas.openai_tools()`
3. **MCP server for Claude Desktop** — see
   [`examples/mcp_claude_desktop.md`](https://github.com/tierproxy/python-sdk/blob/main/examples/mcp_claude_desktop.md)

All three share the same JSON Schema definitions, derived directly from
the SDK's Pydantic models. They cannot drift from runtime behavior.

## JSON Schema export

Every response model has a JSON Schema (Draft 2020-12) available:

```python
from tierproxy import schemas

schema = schemas.json_schema("Me")
# {
#   "title": "Me",
#   "type": "object",
#   "properties": {
#     "client_id": {"type": "string", "description": "Stable account identifier..."},
#     "plan_id": {"type": "string", "description": "Current plan slug..."},
#     ...
#   },
#   "required": ["client_id", "plan_id", "status", "quota_bytes_month", ...]
# }
```

Use this when feeding the SDK's response shapes to a validating LLM gateway
(LiteLLM, LangChain structured output) or to constrain a model's generated
JSON.

## Anthropic Claude tool use

```python
import anthropic
from tierproxy import TierProxy, schemas

client = anthropic.Anthropic()

with TierProxy() as gw:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=schemas.anthropic_tools(),
        messages=[
            {"role": "user", "content": "How much quota is left this month?"}
        ],
    )
```

When Claude decides to call a tool, dispatch the call into the SDK and
return the JSON result. Full working example:
[`examples/ai_tool_use_claude.py`](https://github.com/tierproxy/python-sdk/blob/main/examples/ai_tool_use_claude.py).

## OpenAI function calling

```python
from openai import OpenAI
from tierproxy import TierProxy, schemas

openai = OpenAI()

with TierProxy() as gw:
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Check my quota"}],
        tools=schemas.openai_tools(),
    )
```

Full working example:
[`examples/ai_tool_use_openai.py`](https://github.com/tierproxy/python-sdk/blob/main/examples/ai_tool_use_openai.py).

## Tool catalog

`schemas.anthropic_tools()` and `schemas.openai_tools()` currently
expose these read-only tools (the proxy-through surface is too
free-form to expose as a fixed schema):

| Tool name | Description | Output model |
|-----------|-------------|--------------|
| `tierproxy_me_get` | Current account identity + month-to-date usage | `Me` |
| `tierproxy_usage_today` | Today's bandwidth + cost | `UsageDay` |
| `tierproxy_health_list` | Per-upstream performance snapshot | `UpstreamHealth` (list) |
| `tierproxy_rate_limits_get` | Learned rate-limit suggestions | `RateLimits` |

## Round-trip safety

If your agent host validates tool outputs before relaying them to the
model, use `output_schema_for` to fetch the JSON Schema of the expected
response:

```python
from tierproxy import schemas
import jsonschema

schema = schemas.output_schema_for("tierproxy_me_get")
jsonschema.validate(instance=tool_result_payload, schema=schema)
```

## Limitations

- **Read-only surface today.** The proxy-through endpoint (`client.get(url, ...)`)
  is intentionally not exposed as a tool — its input shape is too open to
  capture safely in a fixed JSON Schema. Future versions may expose
  targeted variants (e.g. `tierproxy_scrape_url` with country/session_id).
- **Draft 2020-12** is the dialect used by Pydantic v2's
  `model_json_schema()`. Most LLM hosts accept any Draft 2020/2019/Draft-07
  schema; if yours rejects, post-process with `jsonschema_to_openapi` or
  similar.
- **Tool names are stable across minor versions.** Field-level changes
  inside `input_schema` may evolve — pin the SDK version if your
  agent prompt depends on specific field metadata.

## MCP server

For Claude Desktop, the SDK ships an MCP server entrypoint that exposes
the same tool surface. See
[`examples/mcp_claude_desktop.md`](https://github.com/tierproxy/python-sdk/blob/main/examples/mcp_claude_desktop.md)
for `claude_desktop_config.json` setup.
