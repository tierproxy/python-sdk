"""E2E: spins through the local-dev docker compose stack.

Requires: make dev-up && make dev-seed
Run: pytest -m e2e
"""

import os

import httpx
import pytest

from tierproxy import ProxyURL, TierProxy

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.requires_real_gateway,
    pytest.mark.skipif(
        not os.environ.get("TIERPROXY_API_KEY"),
        reason="TIERPROXY_API_KEY not set; local-dev stack required",
    ),
]


@pytest.fixture
def client() -> TierProxy:
    return TierProxy(
        api_key=os.environ.get("TIERPROXY_API_KEY", "tp_local_DEMOKEY1234567890ABCDEFGHIJKL"),
        base_url=os.environ.get("GWPROXY_PUBLIC_URL", "https://localhost:8444"),
        http_client=httpx.Client(verify=False, timeout=30),  # self-signed local cert
    )


def test_me_returns_local_client(client: TierProxy) -> None:
    me = client.me.get()
    assert me.client_id == "client_local"
    assert me.quota_bytes_month > 0


def test_health_lists_upstreams(client: TierProxy) -> None:
    ups = client.health.upstreams()
    assert len(ups) >= 1
    assert all(u.state in {"green", "yellow", "red"} for u in ups)


def test_usage_returns_zero_or_more_days(client: TierProxy) -> None:
    u = client.usage.get()
    assert u.total_bytes >= 0
    assert u.client_id == "client_local"


def test_can_proxy_via_gateway() -> None:
    """Use ProxyURL to actually hit the gateway listener and through to mock-upstream then ipinfo."""
    proxy = ProxyURL(
        api_key=os.environ.get("TIERPROXY_API_KEY", "tp_local_DEMOKEY1234567890ABCDEFGHIJKL"),
        host="localhost",
        port_https=443,
    )
    with httpx.Client(
        proxy=proxy.http_url(),
        headers=proxy.headers(),
        verify=False,
        timeout=30,
    ) as h:
        r = h.get("https://ipinfo.io/json")
        assert r.status_code == 200
        assert "ip" in r.json()
