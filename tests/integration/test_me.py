from pytest_httpx import HTTPXMock

from tierproxy import TierProxy
from tierproxy.errors import AuthenticationError


def test_me_get_returns_typed_object(httpx_mock: HTTPXMock, client: TierProxy) -> None:
    httpx_mock.add_response(
        url="https://test.local/v1/me",
        json={
            "client_id": "c1",
            "plan_id": "p1",
            "status": "active",
            "quota_bytes_month": 100_000_000_000,
            "used_bytes_month": 1_234_567,
            "allowed_upstreams": ["decodo", "iproyal"],
            "rate_per_sec": 100,
            "bytes_per_sec": 10_000_000,
        },
    )
    me = client.me.get()
    assert me.client_id == "c1"
    assert me.plan_id == "p1"
    assert me.remaining_bytes == 100_000_000_000 - 1_234_567


def test_me_sends_bearer_token(httpx_mock: HTTPXMock, client: TierProxy) -> None:
    httpx_mock.add_response(
        json={
            "client_id": "c",
            "plan_id": "p",
            "status": "active",
            "quota_bytes_month": 0,
            "used_bytes_month": 0,
            "allowed_upstreams": [],
        }
    )
    client.me.get()
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["Authorization"] == "Bearer tp_test_DUMMY_1234567890ABCDEF"


def test_me_401_raises_authentication_error(httpx_mock: HTTPXMock, client: TierProxy) -> None:
    httpx_mock.add_response(
        url="https://test.local/v1/me",
        status_code=401,
        json={"type": "auth/x", "title": "no", "request_id": "r1"},
    )
    try:
        client.me.get()
        raise AssertionError("expected AuthenticationError")
    except AuthenticationError as e:
        assert e.request_id == "r1"
