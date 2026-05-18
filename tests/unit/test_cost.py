"""Tests for lazy cost attribution (Task C1)."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from tierproxy import TierProxy
from tierproxy._internal.cost import AsyncCostAttributor, CostAttributor
from tierproxy.async_client import AsyncTierProxy
from tierproxy.resources.usage_recent import Tunnel, UsageRecent


def _tunnel(host: str, cost: float = 0.001, upstream: str = "decodo") -> dict[str, Any]:
    return {
        "client_id": "c1",
        "upstream_id": upstream,
        "target_host": host,
        "bytes_up": 100,
        "bytes_down": 200,
        "cost_usd": cost,
        "duration_ms": 50,
        "timestamp": "2026-05-17T10:00:00Z",
        "status_code": 200,
    }


def _resp(host: str) -> httpx.Response:
    return httpx.Response(200, request=httpx.Request("GET", f"https://{host}/x"))


def test_cost_attributor_lazy_fetch_then_cached() -> None:
    client = MagicMock()
    client.usage_recent.get.return_value = UsageRecent(
        tunnels=[Tunnel(**_tunnel("example.com", cost=0.0042))],
        ts="2026-05-17T10:00:05Z",
    )
    attr = CostAttributor(client, cache_ttl=30.0)
    resp = _resp("example.com")

    assert attr.cost_for(resp) == pytest.approx(0.0042)
    assert client.usage_recent.get.call_count == 1
    # Cached within TTL — no extra fetch
    assert attr.cost_for(resp) == pytest.approx(0.0042)
    assert attr.upstream_for(resp) == "decodo"
    assert client.usage_recent.get.call_count == 1


def test_cost_attributor_returns_none_when_host_missing() -> None:
    client = MagicMock()
    client.usage_recent.get.return_value = UsageRecent(
        tunnels=[Tunnel(**_tunnel("a.com"))],
        ts="2026-05-17T10:00:00Z",
    )
    attr = CostAttributor(client)
    assert attr.cost_for(_resp("b.com")) is None
    assert attr.upstream_for(_resp("b.com")) is None


def test_cost_attributor_swallows_fetch_errors() -> None:
    client = MagicMock()
    client.usage_recent.get.side_effect = RuntimeError("backend down")
    attr = CostAttributor(client)
    # Should not raise — telemetry must not break the user's flow.
    assert attr.cost_for(_resp("example.com")) is None
    assert attr.upstream_for(_resp("example.com")) is None


def test_cost_attributor_refreshes_after_ttl() -> None:
    client = MagicMock()
    client.usage_recent.get.return_value = UsageRecent(
        tunnels=[Tunnel(**_tunnel("example.com"))],
        ts="t",
    )
    attr = CostAttributor(client, cache_ttl=0.01)
    attr.cost_for(_resp("example.com"))
    time.sleep(0.02)
    attr.cost_for(_resp("example.com"))
    assert client.usage_recent.get.call_count == 2


def test_client_cost_for_uses_attributor() -> None:
    c = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://test.local")
    fake = MagicMock()
    fake.get.return_value = UsageRecent(
        tunnels=[Tunnel(**_tunnel("example.com", cost=0.05))],
        ts="t",
    )
    c._usage_recent = fake
    resp = _resp("example.com")
    assert c.cost_for(resp) == pytest.approx(0.05)
    assert c.upstream_for(resp) == "decodo"
    assert fake.get.call_count == 1


@pytest.mark.asyncio
async def test_async_cost_attributor_lazy_then_cached() -> None:
    client = MagicMock(spec=AsyncTierProxy)
    client.usage_recent = MagicMock()
    client.usage_recent.get = AsyncMock(
        return_value=UsageRecent(
            tunnels=[Tunnel(**_tunnel("example.com", cost=0.01))],
            ts="t",
        )
    )
    attr = AsyncCostAttributor(client)
    resp = _resp("example.com")
    assert await attr.cost_for(resp) == pytest.approx(0.01)
    assert await attr.upstream_for(resp) == "decodo"
    assert client.usage_recent.get.await_count == 1
