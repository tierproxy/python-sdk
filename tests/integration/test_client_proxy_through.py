from pytest_httpx import HTTPXMock

from tierproxy import TierProxy


def test_client_get_routes_through_proxy(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/data", json={"k": "v"})
    client = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    r = client.get("https://example.com/data", country="US", session_id="s1")
    assert r.status_code == 200
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["X-Proxy-Geo"] == "US"
    assert req.headers["X-Proxy-Session"] == "s1"


def test_client_post_with_json_body(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/api", method="POST", json={"ok": True})
    client = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    r = client.post("https://example.com/api", json={"k": "v"}, country="GB")
    assert r.status_code == 200
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["X-Proxy-Geo"] == "GB"


def test_target_builder(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/a", json={})
    httpx_mock.add_response(url="https://example.com/b", json={})
    client = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    t = client.target(country="GB", session_id="xx")
    t.get("https://example.com/a")
    t.get("https://example.com/b")
    reqs = httpx_mock.get_requests()
    assert all(r.headers["X-Proxy-Geo"] == "GB" for r in reqs)
    assert all(r.headers["X-Proxy-Session"] == "xx" for r in reqs)


def test_session_reuses_targeting(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com", json={})
    client = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    s = client.session(country="JP")
    s.get("https://example.com")
    s.close()
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["X-Proxy-Geo"] == "JP"


def test_target_per_call_override(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/a", json={})
    client = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    t = client.target(country="GB", session_id="xx")
    t.get("https://example.com/a", country="US")
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["X-Proxy-Geo"] == "US"


def test_request_passthrough_headers_merge(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/a", json={})
    client = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    client.get(
        "https://example.com/a",
        country="US",
        headers={"X-Custom": "hello"},
    )
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["X-Custom"] == "hello"
    assert req.headers["X-Proxy-Geo"] == "US"
