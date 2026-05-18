"""Tests for ResponseCache (Task C2)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import httpx
import pytest

from tierproxy import TierProxy
from tierproxy._internal.cache import ResponseCache


def _resp(body: str = "x", status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        content=body.encode(),
        request=httpx.Request("GET", "https://example.com/"),
    )


def test_cache_skips_oversized_response() -> None:
    c = ResponseCache(max_size=10, default_ttl=10.0, max_response_size=100)
    big = _resp("x" * 200)
    assert c.set("GET", "/a", None, big) is False
    assert c.get("GET", "/a") is None


def test_cache_accepts_undersized() -> None:
    c = ResponseCache(max_size=10, default_ttl=10.0, max_response_size=1000)
    assert c.set("GET", "/a", None, _resp("small")) is True
    hit = c.get("GET", "/a")
    assert hit is not None
    assert hit.text == "small"


def test_cache_respects_ttl() -> None:
    c = ResponseCache(max_size=10, default_ttl=0.01)
    c.set("GET", "/a", None, _resp("x"))
    assert c.get("GET", "/a") is not None
    time.sleep(0.02)
    assert c.get("GET", "/a") is None


def test_cache_zero_ttl_skipped() -> None:
    c = ResponseCache(max_size=10, default_ttl=0.0)
    assert c.set("GET", "/a", None, _resp("x")) is False


def test_cache_lru_eviction() -> None:
    c = ResponseCache(max_size=2, default_ttl=10.0)
    c.set("GET", "/a", None, _resp("a"))
    c.set("GET", "/b", None, _resp("b"))
    c.set("GET", "/c", None, _resp("c"))
    assert c.size() == 2
    assert c.get("GET", "/a") is None
    assert c.get("GET", "/b") is not None
    assert c.get("GET", "/c") is not None


def test_cache_params_distinguish_keys() -> None:
    c = ResponseCache(max_size=10, default_ttl=10.0)
    c.set("GET", "/a", {"q": "1"}, _resp("one"))
    c.set("GET", "/a", {"q": "2"}, _resp("two"))
    one = c.get("GET", "/a", {"q": "1"})
    two = c.get("GET", "/a", {"q": "2"})
    assert one is not None and one.text == "one"
    assert two is not None and two.text == "two"


def test_cache_skips_streaming_responses() -> None:
    c = ResponseCache(max_size=10, default_ttl=10.0)
    streaming = MagicMock(spec=httpx.Response)
    streaming.status_code = 200
    type(streaming).content = property(  # type: ignore[misc]
        lambda self: (_ for _ in ()).throw(httpx.StreamConsumed())
    )
    assert c.set("GET", "/a", None, streaming) is False


def test_client_caches_get_2xx() -> None:
    c = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444", cache_ttl=60.0
    )
    fake = _resp("hello")
    with patch.object(TierProxy, "_do_request", return_value=fake) as m:
        a = c.get("https://example.com")
        b = c.get("https://example.com")
    assert m.call_count == 1
    assert a.text == "hello"
    assert b.text == "hello"


def test_client_does_not_cache_post() -> None:
    c = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444", cache_ttl=60.0
    )
    fake = _resp("ok")
    with patch.object(TierProxy, "_do_request", return_value=fake) as m:
        c.post("https://example.com")
        c.post("https://example.com")
    assert m.call_count == 2


def test_client_does_not_cache_non_2xx() -> None:
    c = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444", cache_ttl=60.0
    )
    fake = _resp("oops", status=500)
    with patch.object(TierProxy, "_do_request", return_value=fake) as m:
        c.get("https://example.com")
        c.get("https://example.com")
    assert m.call_count == 2


def test_client_cache_disabled_by_default() -> None:
    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    assert c._response_cache is None


@pytest.mark.asyncio
async def test_async_client_caches_get() -> None:
    from tierproxy.async_client import AsyncTierProxy

    c = AsyncTierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444", cache_ttl=60.0
    )
    fake = _resp("hello")

    async def _stub(*a, **kw):  # noqa: ANN001
        return fake

    with patch.object(AsyncTierProxy, "_do_request", side_effect=_stub) as m:
        a = await c.get("https://example.com")
        b = await c.get("https://example.com")
    assert m.call_count == 1
    assert a.text == "hello"
    assert b.text == "hello"
