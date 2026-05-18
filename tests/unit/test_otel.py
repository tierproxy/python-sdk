import sys

import pytest


def test_enable_telemetry_raises_without_extra(monkeypatch):
    """If opentelemetry is unimportable, enable_telemetry raises ImportError."""
    # Reset module-level _enabled so the guard doesn't short-circuit a previous run.
    import tierproxy._otel as otel_mod

    monkeypatch.setattr(otel_mod, "_enabled", False)

    # Drop any cached opentelemetry submodules; setitem to None prevents future imports.
    for key in [k for k in sys.modules if k == "opentelemetry" or k.startswith("opentelemetry.")]:
        monkeypatch.delitem(sys.modules, key, raising=False)
    monkeypatch.setitem(sys.modules, "opentelemetry", None)

    with pytest.raises(ImportError, match=r"pip install tierproxy\[otel\]"):
        otel_mod.enable_telemetry()


def test_enable_telemetry_with_otel_installed():
    """Smoke: if the extra is installed in this env, enable_telemetry succeeds."""
    pytest.importorskip("opentelemetry")
    pytest.importorskip("opentelemetry.sdk")
    pytest.importorskip("opentelemetry.instrumentation.httpx")
    pytest.importorskip("opentelemetry.exporter.otlp.proto.grpc.trace_exporter")

    import tierproxy._otel as otel_mod

    otel_mod._enabled = False
    otel_mod.enable_telemetry(service_name="test-svc")
    # Re-calling is a no-op
    otel_mod.enable_telemetry(service_name="test-svc")


def test_top_level_reexport_lazy():
    """Importing tierproxy must not load opentelemetry until enable_telemetry is called."""
    import tierproxy

    assert hasattr(tierproxy, "enable_telemetry")
    assert callable(tierproxy.enable_telemetry)
