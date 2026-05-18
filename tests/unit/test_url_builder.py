import pytest

from tierproxy import ProxyURL


def test_basic_http_url_uses_api_key_in_header_mode() -> None:
    p = ProxyURL(api_key="k")
    assert p.http_url() == "http://k:x@gw.tierproxy.com:443"


def test_username_encoding_mode_includes_modifiers() -> None:
    p = ProxyURL(api_key="k", country="US", session_id="abc", mode="username_encoding")
    assert "customer-k-cc-US-sessid-abc" in p.http_url()


def test_headers_only_set_when_attrs_present() -> None:
    p = ProxyURL(api_key="k")
    assert p.headers() == {}
    p2 = ProxyURL(api_key="k", country="US", session_id="abc")
    assert p2.headers() == {"X-Proxy-Geo": "US", "X-Proxy-Session": "abc"}


def test_headers_includes_session_ttl_and_upstream_hint() -> None:
    p = ProxyURL(
        api_key="k",
        country="US",
        session_id="abc",
        session_duration_minutes=30,
        upstream_hint="decodo",
    )
    h = p.headers()
    assert h["X-Proxy-Geo"] == "US"
    assert h["X-Proxy-Session"] == "abc"
    assert h["X-Proxy-Session-TTL"] == "30"
    assert h["X-Proxy-Upstream-Hint"] == "decodo"


def test_invalid_country_raises() -> None:
    with pytest.raises(ValueError, match="ISO 3166"):
        ProxyURL(api_key="k", country="usa")


def test_lowercase_country_raises() -> None:
    with pytest.raises(ValueError, match="ISO 3166"):
        ProxyURL(api_key="k", country="us")


def test_numeric_country_raises() -> None:
    with pytest.raises(ValueError, match="ISO 3166"):
        ProxyURL(api_key="k", country="12")


def test_invalid_session_id_chars_raise() -> None:
    with pytest.raises(ValueError, match="alphanumeric"):
        ProxyURL(api_key="k", session_id="bad@id")


def test_session_id_too_long_raises() -> None:
    with pytest.raises(ValueError, match="1-64"):
        ProxyURL(api_key="k", session_id="x" * 65)


def test_session_id_empty_raises() -> None:
    with pytest.raises(ValueError, match="1-64"):
        ProxyURL(api_key="k", session_id="")


def test_session_id_underscores_and_dashes_ok() -> None:
    p = ProxyURL(api_key="k", session_id="my_session-01")
    assert p.headers()["X-Proxy-Session"] == "my_session-01"


def test_session_duration_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="1-1440"):
        ProxyURL(api_key="k", session_duration_minutes=99999)


def test_session_duration_zero_raises() -> None:
    with pytest.raises(ValueError, match="1-1440"):
        ProxyURL(api_key="k", session_duration_minutes=0)


def test_session_duration_negative_raises() -> None:
    with pytest.raises(ValueError, match="1-1440"):
        ProxyURL(api_key="k", session_duration_minutes=-1)


def test_session_duration_boundary_min() -> None:
    p = ProxyURL(api_key="k", session_duration_minutes=1)
    assert p.headers()["X-Proxy-Session-TTL"] == "1"


def test_session_duration_boundary_max() -> None:
    p = ProxyURL(api_key="k", session_duration_minutes=1440)
    assert p.headers()["X-Proxy-Session-TTL"] == "1440"


def test_city_empty_raises() -> None:
    with pytest.raises(ValueError, match="city invalid"):
        ProxyURL(api_key="k", city="")


def test_city_too_long_raises() -> None:
    with pytest.raises(ValueError, match="city invalid"):
        ProxyURL(api_key="k", city="x" * 65)


def test_city_in_username_encoding() -> None:
    p = ProxyURL(api_key="k", city="miami", mode="username_encoding")
    assert "city-miami" in p.encoded_username()


def test_empty_api_key_raises() -> None:
    with pytest.raises(ValueError, match="api_key required"):
        ProxyURL(api_key="")


def test_pool_residential_not_emitted() -> None:
    p = ProxyURL(api_key="k", pool="residential", mode="username_encoding")
    assert "pool-" not in p.encoded_username()


def test_pool_datacenter_emitted() -> None:
    p = ProxyURL(api_key="k", pool="datacenter", mode="username_encoding")
    assert "pool-datacenter" in p.encoded_username()


def test_pool_isp_emitted() -> None:
    p = ProxyURL(api_key="k", pool="isp", mode="username_encoding")
    assert "pool-isp" in p.encoded_username()


def test_pool_mobile_emitted() -> None:
    p = ProxyURL(api_key="k", pool="mobile", mode="username_encoding")
    assert "pool-mobile" in p.encoded_username()


def test_socks5_url() -> None:
    p = ProxyURL(api_key="k")
    assert p.socks5_url() == "socks5://k:x@gw.tierproxy.com:1080"


def test_socks5_url_with_username_encoding() -> None:
    p = ProxyURL(api_key="k", country="US", mode="username_encoding")
    assert p.socks5_url().startswith("socks5://customer-k-cc-US:")
    assert p.socks5_url().endswith("@gw.tierproxy.com:1080")


def test_upstream_hint_in_headers() -> None:
    p = ProxyURL(api_key="k", upstream_hint="decodo")
    assert p.headers()["X-Proxy-Upstream-Hint"] == "decodo"


def test_upstream_hint_in_username() -> None:
    p = ProxyURL(api_key="k", upstream_hint="decodo", mode="username_encoding")
    assert "upstream-decodo" in p.encoded_username()


def test_http_url_uses_custom_password_when_set() -> None:
    p = ProxyURL(api_key="k", password="secret")
    assert p.http_url() == "http://k:secret@gw.tierproxy.com:443"


def test_http_url_custom_host_and_port() -> None:
    p = ProxyURL(api_key="k", host="localhost", port_https=8443)
    assert p.http_url() == "http://k:x@localhost:8443"


def test_socks5_url_custom_port() -> None:
    p = ProxyURL(api_key="k", port_socks5=1085)
    assert p.socks5_url().endswith(":1085")


def test_encoded_username_all_modifiers() -> None:
    p = ProxyURL(
        api_key="abc",
        pool="datacenter",
        country="US",
        city="miami",
        session_id="s1",
        session_duration_minutes=10,
        upstream_hint="decodo",
        mode="username_encoding",
    )
    assert p.encoded_username() == (
        "customer-abc-pool-datacenter-cc-US-city-miami-sessid-s1-sesstime-10-upstream-decodo"
    )


def test_headers_mode_url_no_encoded_username() -> None:
    p = ProxyURL(api_key="k", country="US", session_id="abc", mode="headers")
    assert p.http_url() == "http://k:x@gw.tierproxy.com:443"
    assert "cc-US" not in p.http_url()


def test_requests_kwargs() -> None:
    from tierproxy.proxy.adapters import requests_kwargs

    p = ProxyURL(api_key="k", country="US")
    kw = requests_kwargs(p)
    assert kw["proxies"]["http"].startswith("http://k:")
    assert kw["proxies"]["https"].startswith("http://k:")
    assert kw["headers"]["X-Proxy-Geo"] == "US"


def test_httpx_kwargs() -> None:
    from tierproxy.proxy.adapters import httpx_kwargs

    p = ProxyURL(api_key="k")
    kw = httpx_kwargs(p)
    assert "proxy" in kw
    assert "headers" in kw
    assert kw["proxy"] == "http://k:x@gw.tierproxy.com:443"


def test_aiohttp_kwargs() -> None:
    from tierproxy.proxy.adapters import aiohttp_kwargs

    p = ProxyURL(api_key="k", country="US")
    kw = aiohttp_kwargs(p)
    assert kw["proxy"] == "http://k:x@gw.tierproxy.com:443"
    assert kw["proxy_headers"]["X-Proxy-Geo"] == "US"


def test_playwright_config_auto_clones_with_warning() -> None:
    from tierproxy.proxy.adapters import playwright_proxy_config

    p = ProxyURL(api_key="k", country="US", mode="headers")
    with pytest.warns(DeprecationWarning, match="username_encoding"):
        cfg = playwright_proxy_config(p)
    assert "customer-k-cc-US" in cfg["username"]
    assert cfg["server"] == "http://gw.tierproxy.com:443"
    assert cfg["password"] == "x"


def test_playwright_config_no_warning_when_explicit() -> None:
    import warnings

    from tierproxy.proxy.adapters import playwright_proxy_config

    p = ProxyURL(api_key="k", mode="username_encoding")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        playwright_proxy_config(p)


def test_playwright_proxy_config_custom_password() -> None:
    from tierproxy.proxy.adapters import playwright_proxy_config

    p = ProxyURL(api_key="k", password="pw", country="US", mode="username_encoding")
    cfg = playwright_proxy_config(p)
    assert cfg["password"] == "pw"
