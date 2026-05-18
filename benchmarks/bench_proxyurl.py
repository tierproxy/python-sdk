import pytest

from tierproxy import ProxyURL


@pytest.mark.benchmark(group="proxyurl")
def test_bench_basic_build(benchmark):
    benchmark(lambda: ProxyURL(api_key="tp_test").http_url())


@pytest.mark.benchmark(group="proxyurl")
def test_bench_full_modifiers_build(benchmark):
    def build():
        return ProxyURL(
            api_key="tp_test",
            country="US",
            session_id="abc-123",
            session_duration_minutes=30,
            upstream_hint="decodo",
            mode="username_encoding",
        ).http_url()

    benchmark(build)


@pytest.mark.benchmark(group="proxyurl")
def test_bench_headers_dict(benchmark):
    p = ProxyURL(api_key="tp_test", country="US", session_id="x")
    benchmark(p.headers)
