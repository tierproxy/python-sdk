"""Mock gateway fixture used by external e2e runs (no TIERPROXY_API_KEY available).

Mirrors enough of the real gateway's /v1/* surface for the SDK contract tests
to exercise routing, parsing, and error handling without a live backend.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def mock_gateway(httpx_mock):  # type: ignore[no-untyped-def]
    base = "https://gw.local.tierproxy.com:8444"
    httpx_mock.add_response(
        method="GET",
        url=f"{base}/v1/me",
        json={
            "client_id": "mock_client",
            "plan_id": "plan_mock",
            "status": "active",
            "quota_bytes_month": 100 * 1024**3,
            "used_bytes_month": 0,
            "allowed_upstreams": ["mock"],
            "rate_per_sec": 100,
            "bytes_per_sec": 10485760,
        },
        is_reusable=True,
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{base}/v1/usage/recent",
        json={"tunnels": [], "window_secs": 3600},
        is_reusable=True,
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{base}/v1/rate-limits/me",
        json={"suggestions": [], "window_secs": 3600},
        is_reusable=True,
    )
    return httpx_mock
