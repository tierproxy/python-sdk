from pytest_httpx import HTTPXMock

from tierproxy import TierProxy


def test_routing_cheapest_picks_cheapest_upstream(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://gw.local:8444/v1/health/upstreams",
        json={
            "upstreams": [
                {
                    "upstream_id": "a",
                    "state": "green",
                    "cb_state": "closed",
                    "success_rate": 0.99,
                    "latency_p95_ms": 100,
                    "cost_per_gb_usd": 5.0,
                },
                {
                    "upstream_id": "b",
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

    client = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF",
        base_url="https://gw.local:8444",
        routing="cheapest",
    )
    client.get("https://example.com")

    proxy_req = next(r for r in httpx_mock.get_requests() if "example.com" in str(r.url))
    assert proxy_req.headers["X-Proxy-Upstream-Hint"] == "b"


def test_routing_respects_explicit_upstream_hint(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com", json={})

    client = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF",
        base_url="https://gw.local:8444",
        routing="cheapest",
    )
    client.get("https://example.com", upstream_hint="forced")

    proxy_req = next(r for r in httpx_mock.get_requests() if "example.com" in str(r.url))
    assert proxy_req.headers["X-Proxy-Upstream-Hint"] == "forced"


def test_routing_fastest_strategy(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://gw.local:8444/v1/health/upstreams",
        json={
            "upstreams": [
                {
                    "upstream_id": "slow",
                    "state": "green",
                    "cb_state": "closed",
                    "success_rate": 0.99,
                    "latency_p95_ms": 500,
                    "cost_per_gb_usd": 1.0,
                },
                {
                    "upstream_id": "fast",
                    "state": "green",
                    "cb_state": "closed",
                    "success_rate": 0.97,
                    "latency_p95_ms": 50,
                    "cost_per_gb_usd": 9.0,
                },
            ]
        },
    )
    httpx_mock.add_response(url="https://example.com", json={})
    client = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF",
        base_url="https://gw.local:8444",
        routing="fastest",
    )
    client.get("https://example.com")
    proxy_req = next(r for r in httpx_mock.get_requests() if "example.com" in str(r.url))
    assert proxy_req.headers["X-Proxy-Upstream-Hint"] == "fast"
