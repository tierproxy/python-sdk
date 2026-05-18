import os

import httpx
import pytest
from pytest_httpx import HTTPXMock

import tierproxy


@pytest.fixture(autouse=True)
def _reset() -> "object":
    os.environ["TIERPROXY_API_KEY"] = "tp_test_DUMMY_1234567890ABCDEF"
    tierproxy.reset_default_client()
    yield
    tierproxy.reset_default_client()
    del os.environ["TIERPROXY_API_KEY"]


@pytest.fixture
def httpx_mock_non_strict(httpx_mock: HTTPXMock) -> HTTPXMock:
    return httpx_mock


def test_module_get_routes_through_gateway(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com", text="ok", method="GET")
    r = tierproxy.get("https://example.com", country="US")
    assert r.status_code == 200
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers.get("X-Proxy-Geo") == "US"


def test_module_post_forwards_to_default_client(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/api", method="POST", json={"ok": True})
    r = tierproxy.post("https://example.com/api", json={"k": "v"}, country="GB")
    assert r.status_code == 200
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["X-Proxy-Geo"] == "GB"


def test_module_request_method(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/x", method="PUT", json={})
    r = tierproxy.request("PUT", "https://example.com/x", country="DE")
    assert r.status_code == 200


def test_module_session_returns_httpx_client(httpx_mock: HTTPXMock) -> None:
    s = tierproxy.session(country="GB")
    assert isinstance(s, httpx.Client)
    httpx_mock.add_response(url="https://example.com", json={"ok": True})
    r = s.get("https://example.com")
    assert r.status_code == 200
    s.close()


def test_reset_default_client_drops_singleton() -> None:
    s = tierproxy.session(country="US")
    s.close()
    # Force the singleton path
    tierproxy.reset_default_client()
    s2 = tierproxy.session(country="JP")
    s2.close()
