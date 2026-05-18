import pytest

from tierproxy import AsyncTierProxy, TierProxy


def test_base_url_must_be_https_by_default():
    with pytest.raises(ValueError, match="https://"):
        TierProxy(
            api_key="tp_live_DEMOKEY1234567890ABCDEF", base_url="http://insecure.example.com:8444"
        )


def test_async_base_url_must_be_https_by_default():
    with pytest.raises(ValueError, match="https://"):
        AsyncTierProxy(
            api_key="tp_live_DEMOKEY1234567890ABCDEF", base_url="http://insecure.example.com:8444"
        )


def test_base_url_http_allowed_with_explicit_opt_in():
    g = TierProxy(
        api_key="tp_live_DEMOKEY1234567890ABCDEF",
        base_url="http://localhost:8444",
        allow_insecure=True,
    )
    assert str(g.base_url).startswith("http://")


def test_async_base_url_http_allowed_with_explicit_opt_in():
    g = AsyncTierProxy(
        api_key="tp_live_DEMOKEY1234567890ABCDEF",
        base_url="http://localhost:8444",
        allow_insecure=True,
    )
    assert str(g.base_url).startswith("http://")


def test_default_base_url_https_works():
    # No assertion explosion; constructor succeeds without specifying base_url.
    TierProxy(api_key="tp_live_DEMOKEY1234567890ABCDEF")
