# Observability with OpenTelemetry

```bash
pip install tierproxy[otel]
```

```python
import tierproxy

tierproxy.enable_telemetry(
    service_name="my-scraper",
    endpoint="http://otel-collector:4317",         # or set OTEL_EXPORTER_OTLP_ENDPOINT env
    resource_attributes={"deployment.env": "prod"},
)

with tierproxy.TierProxy() as t:
    me = t.me.get()
    # Span emitted with attrs: http.method=GET, http.url=..., tierproxy.upstream=...
```

Attributes per span:

| Attribute | Value |
|---|---|
| `service.name` | from `service_name=` arg |
| `http.method` | GET / POST / etc |
| `http.url` | full request URL |
| `tierproxy.country` | from request kwargs |
| `tierproxy.session_id` | sticky session ID if set |
| `tierproxy.upstream` | resolved upstream id |

Compatible with: Datadog APM, Honeycomb, Grafana Tempo, Jaeger, AWS X-Ray, any OTLP receiver.
