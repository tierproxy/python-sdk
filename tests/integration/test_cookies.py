from pytest_httpx import HTTPXMock

from tierproxy import TierProxy


def test_cookies_persist_across_requests_with_same_session_id(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://example.com/login",
        headers={"set-cookie": "sid=abc123; Path=/"},
        json={"ok": True},
    )
    httpx_mock.add_response(url="https://example.com/me", json={"user": "alice"})

    client = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    client.get("https://example.com/login", session_id="s1")
    client.get("https://example.com/me", session_id="s1")

    second = [r for r in httpx_mock.get_requests() if str(r.url).endswith("/me")][0]
    assert "sid=abc123" in second.headers.get("cookie", "")


def test_cookies_isolated_per_session_id(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://example.com/login",
        headers={"set-cookie": "sid=alpha; Path=/"},
        json={"ok": True},
    )
    httpx_mock.add_response(url="https://example.com/check", json={"k": "v"})

    client = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    client.get("https://example.com/login", session_id="user_a")
    client.get("https://example.com/check", session_id="user_b")

    second = [r for r in httpx_mock.get_requests() if str(r.url).endswith("/check")][0]
    assert "sid=alpha" not in second.headers.get("cookie", "")
    assert "user_a" in client.cookies
    assert "user_b" in client.cookies
