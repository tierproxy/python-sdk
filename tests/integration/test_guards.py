import pytest
from pytest_httpx import HTTPXMock

from tierproxy import TierProxy
from tierproxy._guard import BudgetExceededError


def test_budget_guard_blocks_when_over(httpx_mock: HTTPXMock) -> None:
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
    client = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF",
        base_url="https://gw.local:8444",
        monthly_budget_usd=200.0,
    )
    with pytest.raises(BudgetExceededError):
        client.get("https://example.com")


def test_budget_guard_allows_when_under(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://gw.local:8444/v1/usage/me",
        json={
            "client_id": "c",
            "from": "2026-05-01",
            "to": "2026-05-17",
            "days": [],
            "total_bytes": 0,
            "total_cost_usd": 10.0,
        },
    )
    httpx_mock.add_response(url="https://example.com", json={})
    client = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF",
        base_url="https://gw.local:8444",
        monthly_budget_usd=200.0,
    )
    r = client.get("https://example.com")
    assert r.status_code == 200


def test_budget_guard_caches_usage_for_60s(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://gw.local:8444/v1/usage/me",
        json={
            "client_id": "c",
            "from": "2026-05-01",
            "to": "2026-05-17",
            "days": [],
            "total_bytes": 0,
            "total_cost_usd": 5.0,
        },
    )
    httpx_mock.add_response(url="https://example.com/a", json={})
    httpx_mock.add_response(url="https://example.com/b", json={})
    client = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF",
        base_url="https://gw.local:8444",
        monthly_budget_usd=200.0,
    )
    client.get("https://example.com/a")
    client.get("https://example.com/b")
    # Usage endpoint only hit once thanks to 60s cache
    usage_hits = [r for r in httpx_mock.get_requests() if "/v1/usage/me" in str(r.url)]
    assert len(usage_hits) == 1
