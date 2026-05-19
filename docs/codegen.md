# OpenAPI codegen + regeneration

The SDK's hand-coded resource layer (`tierproxy.resources.*`) is the
canonical client surface — chosen for ergonomics over generator output.
However, `openapi/tierproxy.v1.yaml` remains the contractual source of
truth for what the gateway accepts and returns. When the spec changes,
the SDK needs to be re-aligned.

## When to regenerate

- A new endpoint lands in `openapi/tierproxy.v1.yaml`.
- A field is added, removed, or renamed in a response model.
- HTTP status codes for an endpoint change.
- An auth flow changes (e.g. new header).

You do **not** need to regenerate for purely cosmetic spec edits
(description text, `summary`, examples).

## Prerequisites

- Python 3.10+ inside a venv (`.venv` at repo root is recommended).
- `pip install openapi-python-client` — the reference generator.
- The current `openapi/tierproxy.v1.yaml` checked out.

## Regeneration command

```bash
cd sdks/python
openapi-python-client generate \
  --path ../../openapi/tierproxy.v1.yaml \
  --output-path /tmp/regen-tierproxy \
  --overwrite
```

This produces a reference client at `/tmp/regen-tierproxy/` that you can
diff against the hand-coded resources.

## Diff review checklist

Walk through `/tmp/regen-tierproxy/` and confirm:

1. **New methods**: any `*_client/api/*.py` not represented in
   `src/tierproxy/resources/` corresponds to a new endpoint. Add a
   resource class in `src/tierproxy/resources/<endpoint>.py` following
   the existing `MeResource`/`UsageResource` shape.
2. **Field renames / removals**: compare Pydantic model fields in
   `src/tierproxy/resources/*.py` against `/tmp/regen-tierproxy/.../models/`.
   Update SDK field names + add backwards-compatible aliases via
   `Field(alias=...)` when the rename is breaking.
3. **HTTP status changes**: update the `_STATUS` dict in
   `src/tierproxy/errors.py` if a new status code becomes meaningful.

## Mock fixture update

After adding or modifying an endpoint, extend
`tests/integration/mock_gateway.py` with a matching `httpx_mock.add_response`
entry. The integration tests assert against the mock so external CI
(without `TIERPROXY_API_KEY`) keeps running.

## Pitfalls

- The generator outputs Pydantic v1 models by default; the SDK runs on
  Pydantic v2. Use `model_validate` (v2) instead of `parse_obj` (v1) when
  copying logic from the generated client.
- `Field(description=...)` is preserved across regenerations only if the
  spec carries the description. The SDK adds richer descriptions inline,
  so when re-syncing, prefer the SDK's wording over the spec's.
- `openapi-python-client` ships its own `httpx`-based transport. The SDK
  uses a single shared `httpx.Client` instance — do not import the
  generator's transport.

## Don't forget

After a regeneration that touches the public surface:

- Bump `_version.py` per [semver](https://semver.org/) (minor for additive
  changes, major for breaking).
- Add a CHANGELOG entry under "Unreleased".
- Update [reference.md](./reference.md) if new public symbols were added.
