from pytest_httpx import HTTPXMock

from tierproxy import TierProxy


def test_health_upstreams(httpx_mock: HTTPXMock, client: TierProxy) -> None:
    httpx_mock.add_response(
        json={
            "upstreams": [
                {
                    "upstream_id": "decodo",
                    "state": "green",
                    "cb_state": "closed",
                    "success_rate": 0.99,
                    "latency_p95_ms": 200,
                    "cost_per_gb_usd": 4.5,
                },
                {
                    "upstream_id": "iproyal",
                    "state": "yellow",
                    "cb_state": "closed",
                    "success_rate": 0.88,
                    "latency_p95_ms": 900,
                    "cost_per_gb_usd": 3.2,
                },
            ]
        }
    )
    ups = client.health.upstreams()
    assert len(ups) == 2
    assert ups[0].upstream_id == "decodo"
    assert ups[0].success_rate == 0.99
