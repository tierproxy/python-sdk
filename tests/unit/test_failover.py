"""Tests for auto-failover (Task C3)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
import pytest

from tierproxy import TierProxy
from tierproxy.async_client import AsyncTierProxy
from tierproxy.proxy.selector import pick_next
from tierproxy.resources.health import UpstreamHealth


def _u(uid: str, **kw: Any) -> UpstreamHealth:
    base: dict[str, Any] = {
        "upstream_id": uid,
        "state": "green",
        "cb_state": "closed",
        "success_rate": 0.99,
        "latency_p95_ms": 200,
        "cost_per_gb_usd": 4.0,
    }
    base.update(kw)
    return UpstreamHealth(**base)


def _resp(status: int = 200, body: str = "ok") -> httpx.Response:
    return httpx.Response(
        status,
        content=body.encode(),
        request=httpx.Request("GET", "https://example.com/"),
    )


def test_pick_next_excludes_tried() -> None:
    ups = [_u("a"), _u("b"), _u("c")]
    u = pick_next(ups, exclude={"a"}, strategy="cheapest")
    assert u is not None
    assert u.upstream_id in {"b", "c"}


def test_pick_next_returns_none_if_all_tried() -> None:
    ups = [_u("a"), _u("b")]
    assert pick_next(ups, exclude={"a", "b"}, strategy="cheapest") is None


def test_pick_next_returns_none_for_empty_list() -> None:
    assert pick_next([], exclude=set(), strategy="balanced") is None


def test_pick_next_respects_strategy() -> None:
    ups = [
        _u("a", cost_per_gb_usd=4.0),
        _u("b", cost_per_gb_usd=1.0),
        _u("c", cost_per_gb_usd=2.0),
    ]
    u = pick_next(ups, exclude={"b"}, strategy="cheapest")
    assert u is not None
    assert u.upstream_id == "c"


def _make_failover_client(upstreams: list[UpstreamHealth]) -> TierProxy:
    c = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF",
        base_url="https://gw.local:8444",
        auto_failover=True,
        auto_failover_max_attempts=3,
    )
    assert c._selector is not None
    c._selector._cache = upstreams
    c._selector._fetched_at = 1e18  # never expire
    return c


def test_auto_failover_retries_on_5xx() -> None:
    ups = [_u("a"), _u("b"), _u("c")]
    c = _make_failover_client(ups)

    seen_overrides: list[str] = []

    def stub(self, method, url, _upstream_override=None, **kw):  # noqa: ANN001
        seen_overrides.append(_upstream_override)
        if _upstream_override == seen_overrides[0]:
            return _resp(500)
        return _resp(200, "win")

    with patch.object(TierProxy, "_do_request", new=stub):
        r = c.get("https://example.com")
    assert r.status_code == 200
    assert len(seen_overrides) == 2
    assert seen_overrides[0] != seen_overrides[1]


def test_auto_failover_retries_on_429() -> None:
    ups = [_u("a"), _u("b")]
    c = _make_failover_client(ups)

    calls: list[str] = []

    def stub(self, method, url, _upstream_override=None, **kw):  # noqa: ANN001
        calls.append(_upstream_override)
        return _resp(429) if len(calls) == 1 else _resp(200, "ok")

    with patch.object(TierProxy, "_do_request", new=stub):
        r = c.get("https://example.com")
    assert r.status_code == 200
    assert len(calls) == 2


def test_auto_failover_retries_on_network_error() -> None:
    ups = [_u("a"), _u("b")]
    c = _make_failover_client(ups)

    calls = {"n": 0}

    def stub(self, method, url, _upstream_override=None, **kw):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("dial fail")
        return _resp(200, "win")

    with patch.object(TierProxy, "_do_request", new=stub):
        r = c.get("https://example.com")
    assert r.status_code == 200
    assert calls["n"] == 2


def test_auto_failover_exhausts_attempts_returns_last_failure() -> None:
    ups = [_u("a"), _u("b"), _u("c")]
    c = _make_failover_client(ups)

    def stub(self, method, url, _upstream_override=None, **kw):  # noqa: ANN001
        return _resp(503)

    with patch.object(TierProxy, "_do_request", new=stub):
        r = c.get("https://example.com")
    assert r.status_code == 503


def test_auto_failover_propagates_exhausted_exception() -> None:
    ups = [_u("a"), _u("b")]
    c = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF",
        base_url="https://gw.local:8444",
        auto_failover=True,
        auto_failover_max_attempts=2,
    )
    assert c._selector is not None
    c._selector._cache = ups
    c._selector._fetched_at = 1e18

    def stub(self, method, url, _upstream_override=None, **kw):  # noqa: ANN001
        raise httpx.ConnectError("dial fail")

    with (
        patch.object(TierProxy, "_do_request", new=stub),
        pytest.raises(httpx.ConnectError),
    ):
        c.get("https://example.com")


def test_auto_failover_disabled_skips_retry() -> None:
    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")
    calls = {"n": 0}

    def stub(self, method, url, _upstream_override=None, **kw):  # noqa: ANN001
        calls["n"] += 1
        return _resp(500)

    with patch.object(TierProxy, "_do_request", new=stub):
        r = c.get("https://example.com")
    assert calls["n"] == 1
    assert r.status_code == 500


@pytest.mark.asyncio
async def test_async_auto_failover_retries_on_5xx() -> None:
    ups = [_u("a"), _u("b")]
    c = AsyncTierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF",
        base_url="https://gw.local:8444",
        auto_failover=True,
    )
    assert c._selector is not None
    c._selector._cache = ups
    c._selector._fetched_at = 1e18

    calls: list[str] = []

    async def stub(self, method, url, _upstream_override=None, **kw):  # noqa: ANN001
        calls.append(_upstream_override)
        return _resp(500) if len(calls) == 1 else _resp(200, "win")

    with patch.object(AsyncTierProxy, "_do_request", new=stub):
        r = await c.get("https://example.com")
    assert r.status_code == 200
    assert len(calls) == 2
