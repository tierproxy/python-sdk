from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tierproxy.proxy.selector import AsyncSmartSelector, SmartSelector, pick
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


def test_cheapest() -> None:
    u = pick(
        [
            _u("a", cost_per_gb_usd=4.0),
            _u("b", cost_per_gb_usd=3.0),
            _u("c", cost_per_gb_usd=5.0),
        ],
        "cheapest",
    )
    assert u.upstream_id == "b"


def test_fastest() -> None:
    u = pick(
        [
            _u("a", latency_p95_ms=300),
            _u("b", latency_p95_ms=100),
            _u("c", latency_p95_ms=200),
        ],
        "fastest",
    )
    assert u.upstream_id == "b"


def test_most_reliable() -> None:
    u = pick(
        [
            _u("a", success_rate=0.90),
            _u("b", success_rate=0.99),
            _u("c", success_rate=0.95),
        ],
        "most_reliable",
    )
    assert u.upstream_id == "b"


def test_excludes_red() -> None:
    u = pick([_u("a", state="red"), _u("b")], "cheapest")
    assert u.upstream_id == "b"


def test_excludes_open_breaker() -> None:
    u = pick([_u("a", cb_state="open"), _u("b")], "cheapest")
    assert u.upstream_id == "b"


def test_balanced_prefers_cheap_and_reliable() -> None:
    cheap_slow = _u("a", cost_per_gb_usd=1.0, latency_p95_ms=5000, success_rate=0.5)
    expensive_fast = _u("b", cost_per_gb_usd=10.0, latency_p95_ms=100, success_rate=0.99)
    medium = _u("c", cost_per_gb_usd=3.0, latency_p95_ms=200, success_rate=0.95)
    u = pick([cheap_slow, expensive_fast, medium], "balanced")
    assert u.upstream_id == "c"


def test_all_red_picks_least_bad() -> None:
    u = pick(
        [
            _u("a", state="red", success_rate=0.5),
            _u("b", state="red", success_rate=0.8),
        ],
        "cheapest",
    )
    assert u.upstream_id == "b"


def test_all_open_breakers_picks_least_bad() -> None:
    u = pick(
        [
            _u("a", cb_state="open", success_rate=0.7),
            _u("b", cb_state="open", success_rate=0.4),
        ],
        "fastest",
    )
    assert u.upstream_id == "a"


def test_empty_list_raises() -> None:
    with pytest.raises(ValueError, match="No upstreams"):
        pick([], "balanced")


def test_default_strategy_is_balanced() -> None:
    cheap_slow = _u("a", cost_per_gb_usd=1.0, latency_p95_ms=5000, success_rate=0.5)
    medium = _u("c", cost_per_gb_usd=3.0, latency_p95_ms=200, success_rate=0.95)
    assert pick([cheap_slow, medium]).upstream_id == "c"


def test_balanced_zero_cost_does_not_div_zero() -> None:
    free_ok = _u("a", cost_per_gb_usd=0.0, latency_p95_ms=200, success_rate=0.95)
    paid_ok = _u("b", cost_per_gb_usd=2.0, latency_p95_ms=200, success_rate=0.95)
    u = pick([free_ok, paid_ok], "balanced")
    assert u.upstream_id == "a"


def test_smart_selector_fetches_and_caches() -> None:
    snapshot = [_u("a", cost_per_gb_usd=4.0), _u("b", cost_per_gb_usd=2.0)]
    client = MagicMock()
    client.health.upstreams = MagicMock(return_value=snapshot)

    sel = SmartSelector(client, strategy="cheapest", cache_ttl=30.0)
    first = sel.pick()
    second = sel.pick()

    assert first.upstream_id == "b"
    assert second.upstream_id == "b"
    assert client.health.upstreams.call_count == 1


def test_smart_selector_refetches_after_ttl() -> None:
    snap_a = [_u("a", cost_per_gb_usd=4.0), _u("b", cost_per_gb_usd=2.0)]
    snap_b = [_u("a", cost_per_gb_usd=1.0), _u("b", cost_per_gb_usd=2.0)]
    client = MagicMock()
    client.health.upstreams = MagicMock(side_effect=[snap_a, snap_b])

    sel = SmartSelector(client, strategy="cheapest", cache_ttl=0.0)
    first = sel.pick()
    second = sel.pick()

    assert first.upstream_id == "b"
    assert second.upstream_id == "a"
    assert client.health.upstreams.call_count == 2


async def test_async_smart_selector_fetches_and_caches() -> None:
    snapshot = [_u("a", cost_per_gb_usd=4.0), _u("b", cost_per_gb_usd=2.0)]
    client = MagicMock()
    client.health.upstreams = AsyncMock(return_value=snapshot)

    sel = AsyncSmartSelector(client, strategy="cheapest", cache_ttl=30.0)
    first = await sel.pick()
    second = await sel.pick()

    assert first.upstream_id == "b"
    assert second.upstream_id == "b"
    assert client.health.upstreams.await_count == 1


async def test_async_smart_selector_refetches_after_ttl() -> None:
    snap_a = [_u("a", cost_per_gb_usd=4.0), _u("b", cost_per_gb_usd=2.0)]
    snap_b = [_u("a", cost_per_gb_usd=1.0), _u("b", cost_per_gb_usd=2.0)]
    client = MagicMock()
    client.health.upstreams = AsyncMock(side_effect=[snap_a, snap_b])

    sel = AsyncSmartSelector(client, strategy="cheapest", cache_ttl=0.0)
    first = await sel.pick()
    second = await sel.pick()

    assert first.upstream_id == "b"
    assert second.upstream_id == "a"
    assert client.health.upstreams.await_count == 2
