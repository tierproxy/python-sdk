from pytest_httpx import HTTPXMock

from tierproxy import TierProxy


def test_usage_get(httpx_mock: HTTPXMock, client: TierProxy) -> None:
    httpx_mock.add_response(
        json={
            "client_id": "c",
            "from": "2026-05-01",
            "to": "2026-05-16",
            "days": [{"date": "2026-05-15", "bytes_up": 100, "bytes_down": 200, "cost_usd": 0.05}],
            "total_bytes": 300,
            "total_cost_usd": 0.05,
        }
    )
    u = client.usage.get(from_="2026-05-01", to="2026-05-16")
    assert u.total_bytes == 300
    assert u.days[0].date == "2026-05-15"


def test_usage_passes_query_params(httpx_mock: HTTPXMock, client: TierProxy) -> None:
    httpx_mock.add_response(
        json={
            "client_id": "c",
            "from": "x",
            "to": "y",
            "days": [],
            "total_bytes": 0,
            "total_cost_usd": 0,
        }
    )
    client.usage.get(from_="2026-05-01", to="2026-05-16")
    req = httpx_mock.get_request()
    assert req is not None
    assert "from=2026-05-01" in str(req.url)
    assert "to=2026-05-16" in str(req.url)
