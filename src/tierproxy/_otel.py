"""OpenTelemetry integration — opt-in via `tierproxy.enable_telemetry()`."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_enabled = False


def enable_telemetry(
    *,
    service_name: str = "tierproxy-client",
    endpoint: str | None = None,
    resource_attributes: dict[str, str] | None = None,
) -> None:
    """Enable distributed tracing for tierproxy SDK calls.

    Wires opentelemetry-instrumentation-httpx so every SDK HTTP request
    becomes a span. Customers' own OTel-instrumented frameworks (FastAPI,
    Django, etc.) automatically parent these spans correctly.

    Args:
        service_name: span service.name attribute. Defaults to "tierproxy-client".
        endpoint: OTLP endpoint URL. If None, reads OTEL_EXPORTER_OTLP_ENDPOINT env var.
        resource_attributes: extra resource attrs to set on every span.

    Raises:
        ImportError: if `tierproxy[otel]` extra wasn't installed.
    """
    global _enabled
    if _enabled:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as e:
        raise ImportError(
            "OpenTelemetry not installed. Install with: pip install tierproxy[otel]"
        ) from e

    resource_attrs: dict[str, str] = {SERVICE_NAME: service_name}
    if resource_attributes:
        resource_attrs.update(resource_attributes)

    provider = TracerProvider(resource=Resource.create(resource_attrs))
    if endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        exporter = OTLPSpanExporter(endpoint=endpoint) if endpoint else OTLPSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    HTTPXClientInstrumentor().instrument()
    _enabled = True
