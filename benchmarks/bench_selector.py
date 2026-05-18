import pytest

from tierproxy.proxy.selector import pick
from tierproxy.resources.health import UpstreamHealth


def _make(n: int) -> list[UpstreamHealth]:
    return [
        UpstreamHealth(
            upstream_id=f"u{i}",
            state="green" if i % 10 else "yellow",
            cb_state="closed",
            success_rate=0.99 - i * 0.001,
            latency_p95_ms=100 + i,
            cost_per_gb_usd=2.0 + i * 0.01,
        )
        for i in range(n)
    ]


@pytest.mark.benchmark(group="selector")
def test_bench_pick_balanced_100(benchmark):
    ups = _make(100)
    benchmark(pick, ups, "balanced")


@pytest.mark.benchmark(group="selector")
def test_bench_pick_cheapest_1000(benchmark):
    ups = _make(1000)
    benchmark(pick, ups, "cheapest")
