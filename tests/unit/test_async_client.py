"""Cover the AsyncTierProxy paths so the coverage gate hits 80%."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from tierproxy import AsyncTierProxy
from tierproxy.errors import AuthenticationError, NotFoundError


@pytest.fixture
def async_client() -> AsyncTierProxy:
    return AsyncTierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://test.local")


async def test_async_me_get(httpx_mock: HTTPXMock, async_client: AsyncTierProxy) -> None:
    httpx_mock.add_response(
        url="https://test.local/v1/me",
        json={
            "client_id": "c1",
            "plan_id": "p1",
            "status": "active",
            "quota_bytes_month": 10,
            "used_bytes_month": 2,
            "allowed_upstreams": ["a"],
        },
    )
    me = await async_client.me.get()
    assert me.client_id == "c1"
    assert me.remaining_bytes == 8
    await async_client.close()


async def test_async_me_401(httpx_mock: HTTPXMock, async_client: AsyncTierProxy) -> None:
    httpx_mock.add_response(
        url="https://test.local/v1/me",
        status_code=401,
        json={"title": "no", "request_id": "rid"},
    )
    with pytest.raises(AuthenticationError):
        await async_client.me.get()
    await async_client.close()


async def test_async_usage_get(httpx_mock: HTTPXMock, async_client: AsyncTierProxy) -> None:
    httpx_mock.add_response(
        json={
            "client_id": "c",
            "from": "2026-05-01",
            "to": "2026-05-16",
            "days": [],
            "total_bytes": 0,
            "total_cost_usd": 0,
        }
    )
    u = await async_client.usage.get(from_="2026-05-01", to="2026-05-16")
    assert u.total_bytes == 0
    await async_client.close()


async def test_async_health(httpx_mock: HTTPXMock, async_client: AsyncTierProxy) -> None:
    httpx_mock.add_response(json={"upstreams": []})
    ups = await async_client.health.upstreams()
    assert ups == []
    await async_client.close()


async def test_async_health_404(httpx_mock: HTTPXMock, async_client: AsyncTierProxy) -> None:
    httpx_mock.add_response(status_code=404, json={"title": "no", "request_id": "rid"})
    with pytest.raises(NotFoundError):
        await async_client.health.upstreams()
    await async_client.close()


async def test_async_context_manager(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"upstreams": []})
    async with AsyncTierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://test.local"
    ) as c:
        ups = await c.health.upstreams()
        assert ups == []


def test_async_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TIERPROXY_API_KEY", raising=False)
    with pytest.raises(AuthenticationError):
        AsyncTierProxy()


def test_async_env_var_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIERPROXY_API_KEY", "envkey_DUMMY_1234567890ABCDEF")
    c = AsyncTierProxy()
    assert c._transport.api_key == "envkey_DUMMY_1234567890ABCDEF"


def test_async_resources_lazy_singleton() -> None:
    c = AsyncTierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://x")
    assert c.me is c.me
    assert c.usage is c.usage
    assert c.health is c.health
