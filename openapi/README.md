# tierproxy OpenAPI

`tierproxy.v1.yaml` describes the authenticated REST endpoints exposed by the
gateway on `PUBLIC_API_ADDR` (default `:8444`).

## View locally

```bash
docker run --rm -p 8080:8080 -v $PWD:/spec redocly/redoc \
  --spec /spec/tierproxy.v1.yaml
# open http://localhost:8080
```

## Validate

```bash
pipx run openapi-spec-validator openapi/tierproxy.v1.yaml
```

## Regenerate Python SDK models

```bash
cd sdks/python && bash scripts/generate.sh
```
