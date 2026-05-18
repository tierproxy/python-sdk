import pytest
from pytest_httpx import HTTPXMock

from tierproxy import AsyncTierProxy
from tierproxy._guard import BudgetExceededError


@pytest.mark.asyncio
async def test_async_get(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com", json={"k": "v"})
    async with AsyncTierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444"
    ) as g:
        r = await g.get("https://example.com", country="DE")
    assert r.json() == {"k": "v"}
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["X-Proxy-Geo"] == "DE"


@pytest.mark.asyncio
async def test_async_post(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/api", method="POST", json={"ok": True})
    async with AsyncTierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444"
    ) as g:
        r = await g.post("https://example.com/api", json={"x": 1}, country="US")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_async_target_builder(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com", json={})
    async with AsyncTierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444"
    ) as g:
        await g.target(country="JP").get("https://example.com")
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["X-Proxy-Geo"] == "JP"


@pytest.mark.asyncio
async def test_async_session_reuses_targeting(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com", json={})
    async with AsyncTierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444"
    ) as g:
        s = g.session(country="GB")
        await s.get("https://example.com")
        await s.aclose()
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["X-Proxy-Geo"] == "GB"


@pytest.mark.asyncio
async def test_async_routing_cheapest(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://gw.local:8444/v1/health/upstreams",
        json={
            "upstreams": [
                {
                    "upstream_id": "expensive",
                    "state": "green",
                    "cb_state": "closed",
                    "success_rate": 0.99,
                    "latency_p95_ms": 100,
                    "cost_per_gb_usd": 5.0,
                },
                {
                    "upstream_id": "cheap",
                    "state": "green",
                    "cb_state": "closed",
                    "success_rate": 0.98,
                    "latency_p95_ms": 120,
                    "cost_per_gb_usd": 2.5,
                },
            ]
        },
    )
    httpx_mock.add_response(url="https://example.com", json={})
    async with AsyncTierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF",
        base_url="https://gw.local:8444",
        routing="cheapest",
    ) as g:
        await g.get("https://example.com")
    proxy_req = next(r for r in httpx_mock.get_requests() if "example.com" in str(r.url))
    assert proxy_req.headers["X-Proxy-Upstream-Hint"] == "cheap"


@pytest.mark.asyncio
async def test_async_budget_guard_blocks(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://gw.local:8444/v1/usage/me",
        json={
            "client_id": "c",
            "from": "2026-05-01",
            "to": "2026-05-17",
            "days": [],
            "total_bytes": 0,
            "total_cost_usd": 250.0,
        },
    )
    async with AsyncTierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF",
        base_url="https://gw.local:8444",
        monthly_budget_usd=200.0,
    ) as g:
        with pytest.raises(BudgetExceededError):
            await g.get("https://example.com")
