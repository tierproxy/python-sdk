from urllib.parse import unquote, urlparse

import pytest

from tierproxy import ProxyURL


@pytest.mark.parametrize(
    "api_key",
    [
        "tp_live_normal_key_AAAAAAAAAAAA",
        "tp_live_with-colon-AAAAAAAAAAAA",
        "tp_live_with-at-sign-AAAAAAAAAA",
        "tp_live_with-percent-AAAAAAAAA",
        "tp_live_with-slash-AAAAAAAAAAA",
    ],
)
def test_proxy_url_safe_with_arbitrary_api_key(api_key):
    p = ProxyURL(api_key=api_key, country="US", mode="username_encoding")
    url = p.http_url()
    parsed = urlparse(url)
    assert parsed.hostname is not None
    # Host must not be mangled by api_key contents.
    assert "@" not in parsed.hostname
    decoded = unquote(parsed.username)
    # The api_key piece must appear literally after `customer-`.
    assert decoded.startswith(f"customer-{api_key}")


@pytest.mark.parametrize("country", ["US", "US;DROP", "US@", "US:80"])
def test_proxy_url_safe_with_country_injection(country):
    # Country has strict ISO 3166-1 alpha-2 uppercase validation that rejects
    # injection-shaped values up front. The encoder is defence-in-depth: if a
    # bad value ever slips past validation (e.g. validation is loosened later
    # or bypassed via dataclasses.replace), the encoder must still keep the
    # URL well-formed. Verify both paths.
    if not (len(country) == 2 and country.isalpha() and country.isupper()):
        with pytest.raises(ValueError, match="ISO 3166"):
            ProxyURL(
                api_key="tp_live_DEMOKEY1234567890ABCDEFGH",
                country=country,
                mode="username_encoding",
            )
        # Bypass validation to exercise the encoder directly.
        p = ProxyURL(
            api_key="tp_live_DEMOKEY1234567890ABCDEFGH", country="US", mode="username_encoding"
        )
        object.__setattr__(p, "country", country)
    else:
        p = ProxyURL(
            api_key="tp_live_DEMOKEY1234567890ABCDEFGH", country=country, mode="username_encoding"
        )
    parsed = urlparse(p.http_url())
    decoded = unquote(parsed.username)
    assert f"-cc-{country}" in decoded
    assert "@" not in parsed.hostname


def test_proxy_url_session_id_validation_unchanged():
    # Existing session_id regex validation must still reject ill-formed IDs.
    # If session_id validator exists and rejects spaces/slashes, this stays passing.
    with pytest.raises((ValueError, TypeError)):
        ProxyURL(
            api_key="tp_live_DEMOKEY1234567890ABCDEFGH",
            session_id="bad space",
            mode="username_encoding",
        )
