"""Integration tests for rate-limit learning (Task C4)."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from tierproxy import TierProxy
from tierproxy.async_client import AsyncTierProxy


def test_rate_limits_get(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://gw.local:8444/v1/rate-limits/me",
        json={
            "suggestions": [
                {"domain": "example.com", "suggest_per_sec": 1.5},
                {"domain": "api.x.com", "suggest_per_sec": 0.25},
            ],
            "window_secs": 3600,
        },
    )
    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    rl = c.rate_limits.get()
    assert rl.window_secs == 3600
    assert len(rl.suggestions) == 2
    assert rl.suggestions[0].domain == "example.com"
    assert rl.suggestions[0].suggest_per_sec == pytest.approx(1.5)


def test_429_queues_then_reports_on_next_request(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://api.x.com/v", status_code=429)
    httpx_mock.add_response(url="https://api.y.com/v", json={"ok": True})

    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    c.get("https://api.x.com/v")
    assert c._pending_429_reports == {"api.x.com"}

    c.get("https://api.y.com/v")
    reqs = httpx_mock.get_requests()
    # Second request (to api.y.com) should carry the report header
    second = [r for r in reqs if "api.y.com" in str(r.url)][0]
    assert second.headers.get("X-TierProxy-Report-429") == "api.x.com"
    # Set is cleared after emission
    assert c._pending_429_reports == set()


def test_multiple_429s_joined_in_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://a.com/v", status_code=429)
    httpx_mock.add_response(url="https://b.com/v", status_code=429)
    httpx_mock.add_response(url="https://c.com/v", json={"ok": True})

    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    c.get("https://a.com/v")
    c.get("https://b.com/v")
    # First call sent no header (set empty before), second call sent "a.com",
    # so after second call only b.com is pending.
    assert "b.com" in c._pending_429_reports

    c.get("https://c.com/v")
    reqs = httpx_mock.get_requests()
    third = [r for r in reqs if "c.com" in str(r.url)][0]
    assert "b.com" in third.headers.get("X-TierProxy-Report-429", "")
    assert c._pending_429_reports == set()


def test_first_request_no_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://x.com", json={"ok": True})
    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    c.get("https://x.com")
    req = httpx_mock.get_request()
    assert req is not None
    assert "X-TierProxy-Report-429" not in req.headers


@pytest.mark.asyncio
async def test_async_rate_limits_get(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://gw.local:8444/v1/rate-limits/me",
        json={
            "suggestions": [{"domain": "x.com", "suggest_per_sec": 2.0}],
            "window_secs": 60,
        },
    )
    c = AsyncTierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    rl = await c.rate_limits.get()
    assert rl.window_secs == 60
    assert rl.suggestions[0].domain == "x.com"


@pytest.mark.asyncio
async def test_async_429_reported_on_next_request(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://api.x.com/v", status_code=429)
    httpx_mock.add_response(url="https://api.y.com/v", json={"ok": True})

    c = AsyncTierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    await c.get("https://api.x.com/v")
    assert c._pending_429_reports == {"api.x.com"}

    await c.get("https://api.y.com/v")
    reqs = httpx_mock.get_requests()
    second = [r for r in reqs if "api.y.com" in str(r.url)][0]
    assert second.headers.get("X-TierProxy-Report-429") == "api.x.com"
