"""Integration tests for JA3/JA4 TLS fingerprint rotation (Task F1)."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from tierproxy import TierProxy
from tierproxy.async_client import AsyncTierProxy


def test_tls_fingerprint_chrome_sets_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/", json={"ok": True})
    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    c.get("https://example.com/", tls_fingerprint="chrome")
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers.get("X-TierProxy-TLS-Profile") == "chrome"


def test_tls_fingerprint_firefox_sets_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/", json={"ok": True})
    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    c.get("https://example.com/", tls_fingerprint="firefox")
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers.get("X-TierProxy-TLS-Profile") == "firefox"


def test_tls_fingerprint_safari_sets_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/", json={"ok": True})
    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    c.get("https://example.com/", tls_fingerprint="safari")
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers.get("X-TierProxy-TLS-Profile") == "safari"


def test_tls_fingerprint_random_sets_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/", json={"ok": True})
    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    c.get("https://example.com/", tls_fingerprint="random")
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers.get("X-TierProxy-TLS-Profile") == "random"


def test_tls_fingerprint_omitted_no_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/", json={"ok": True})
    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    c.get("https://example.com/")
    req = httpx_mock.get_request()
    assert req is not None
    assert "X-TierProxy-TLS-Profile" not in req.headers


def test_tls_fingerprint_kwarg_is_consumed_not_forwarded(httpx_mock: HTTPXMock) -> None:
    """tls_fingerprint must be popped before httpx receives the kwargs."""
    httpx_mock.add_response(url="https://example.com/?a=1", json={"ok": True})
    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    # If tls_fingerprint leaks to httpx as a request kwarg, this raises TypeError.
    c.get("https://example.com/", tls_fingerprint="chrome", params={"a": "1"})
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers.get("X-TierProxy-TLS-Profile") == "chrome"


def test_tls_fingerprint_with_post(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/", json={"ok": True})
    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    c.post("https://example.com/", tls_fingerprint="firefox", json={"k": "v"})
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers.get("X-TierProxy-TLS-Profile") == "firefox"


@pytest.mark.asyncio
async def test_async_tls_fingerprint_sets_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/", json={"ok": True})
    c = AsyncTierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    await c.get("https://example.com/", tls_fingerprint="chrome")
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers.get("X-TierProxy-TLS-Profile") == "chrome"


@pytest.mark.asyncio
async def test_async_tls_fingerprint_omitted_no_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/", json={"ok": True})
    c = AsyncTierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    await c.get("https://example.com/")
    req = httpx_mock.get_request()
    assert req is not None
    assert "X-TierProxy-TLS-Profile" not in req.headers


@pytest.mark.asyncio
async def test_async_tls_fingerprint_random(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/", json={"ok": True})
    c = AsyncTierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    await c.get("https://example.com/", tls_fingerprint="random")
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers.get("X-TierProxy-TLS-Profile") == "random"
