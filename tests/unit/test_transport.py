"""Cover retry + error paths in the shared Transport."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
import pytest
from pytest_httpx import HTTPXMock

from tierproxy import TierProxy
from tierproxy._internal.http import Transport
from tierproxy.errors import (
    ConnectionError as GwConnectionError,
)
from tierproxy.errors import (
    NotFoundError,
    ServerError,
    TierProxyError,
    ValidationError,
)
from tierproxy.errors import (
    TimeoutError as GwTimeoutError,
)
from tierproxy.retry import RetryPolicy


@pytest.fixture
def fast_client() -> TierProxy:
    # Tiny retry delay so the retry tests don't sit blocking.
    policy = RetryPolicy(max_retries=2, initial_delay_seconds=0.0, jitter=0.0)
    return TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://test.local", retry_policy=policy
    )


def test_retries_500_then_succeeds(httpx_mock: HTTPXMock, fast_client: TierProxy) -> None:
    httpx_mock.add_response(url="https://test.local/v1/me", status_code=500, json={})
    httpx_mock.add_response(
        url="https://test.local/v1/me",
        json={
            "client_id": "c",
            "plan_id": "p",
            "status": "active",
            "quota_bytes_month": 0,
            "used_bytes_month": 0,
            "allowed_upstreams": [],
        },
    )
    me = fast_client.me.get()
    assert me.client_id == "c"


def test_retries_429_with_retry_after(httpx_mock: HTTPXMock, fast_client: TierProxy) -> None:
    httpx_mock.add_response(
        url="https://test.local/v1/me",
        status_code=429,
        headers={"Retry-After": "0"},
        json={"title": "slow down"},
    )
    httpx_mock.add_response(
        url="https://test.local/v1/me",
        json={
            "client_id": "c",
            "plan_id": "p",
            "status": "active",
            "quota_bytes_month": 0,
            "used_bytes_month": 0,
            "allowed_upstreams": [],
        },
    )
    me = fast_client.me.get()
    assert me.client_id == "c"


def test_404_maps_to_not_found(httpx_mock: HTTPXMock, client: TierProxy) -> None:
    httpx_mock.add_response(
        url="https://test.local/v1/me",
        status_code=404,
        json={"detail": "missing", "request_id": "rx"},
    )
    with pytest.raises(NotFoundError) as exc:
        client.me.get()
    assert exc.value.request_id == "rx"


def test_400_maps_to_validation_error(httpx_mock: HTTPXMock, client: TierProxy) -> None:
    httpx_mock.add_response(
        url="https://test.local/v1/me",
        status_code=400,
        json={"title": "bad"},
    )
    with pytest.raises(ValidationError):
        client.me.get()


def test_503_after_retries_raises_server_error(
    httpx_mock: HTTPXMock, fast_client: TierProxy
) -> None:
    # max_retries=2 → 3 total attempts (1 initial + 2 retries).
    for _ in range(3):
        httpx_mock.add_response(
            url="https://test.local/v1/me",
            status_code=503,
            json={"title": "no"},
        )
    with pytest.raises(ServerError):
        fast_client.me.get()


def test_non_json_error_body_still_raises(httpx_mock: HTTPXMock, client: TierProxy) -> None:
    httpx_mock.add_response(
        url="https://test.local/v1/me",
        status_code=418,
        content=b"plain text",
        headers={"Content-Type": "text/plain", "X-Request-Id": "xyz"},
    )
    with pytest.raises(TierProxyError) as exc:
        client.me.get()
    assert exc.value.request_id == "xyz"


def test_network_error_exhausts_then_raises_connection(fast_client: TierProxy) -> None:
    def boom(*_a: Any, **_kw: Any) -> Any:
        raise httpx.ConnectError("nope")

    with patch.object(httpx.Client, "request", side_effect=boom), pytest.raises(GwConnectionError):
        fast_client.me.get()


def test_timeout_exhausts_then_raises_timeout(fast_client: TierProxy) -> None:
    def boom(*_a: Any, **_kw: Any) -> Any:
        raise httpx.ReadTimeout("slow")

    with patch.object(httpx.Client, "request", side_effect=boom), pytest.raises(GwTimeoutError):
        fast_client.me.get()


def test_user_agent_suffix_is_appended() -> None:
    c = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF",
        base_url="https://x",
        user_agent_suffix="myapp/1.0",
    )
    assert "myapp/1.0" in c._transport.ua


def test_close_is_idempotent_with_external_client() -> None:
    external = httpx.Client()
    c = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://x", http_client=external
    )
    c.close()
    # External client is the same object — close() called on it.
    assert external.is_closed


def test_context_manager_closes() -> None:
    with TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://x") as c:
        assert c._transport.ua.startswith("tierproxy-python/")


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TIERPROXY_API_KEY", raising=False)
    from tierproxy.errors import AuthenticationError

    with pytest.raises(AuthenticationError):
        TierProxy()


def test_env_var_supplies_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIERPROXY_API_KEY", "from_env_DUMMY_1234567890ABCDEF")
    c = TierProxy()
    assert c._transport.api_key == "from_env_DUMMY_1234567890ABCDEF"


def test_transport_async_flag_round_trip() -> None:
    t = Transport(
        api_key="k",
        base_url="https://x",
        timeout=1.0,
        retry=RetryPolicy(),
        ua_suffix=None,
        http_client=None,
        is_async=True,
    )
    assert t._is_async is True
    assert isinstance(t._client, httpx.AsyncClient)
