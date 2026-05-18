from tierproxy.observability.redact import redact_headers, redact_url


def test_redact_authorization_header():
    h = {"Authorization": "Bearer tp_live_secret", "Accept": "*/*"}
    out = redact_headers(h)
    assert out["Authorization"] == "Bearer ***"
    assert out["Accept"] == "*/*"


def test_redact_proxy_authorization_header():
    h = {"Proxy-Authorization": "Basic dHA6eA=="}
    assert redact_headers(h)["Proxy-Authorization"] == "Basic ***"


def test_redact_x_api_key_header():
    h = {"X-Api-Key": "tp_live_secret"}
    assert redact_headers(h)["X-Api-Key"] == "***"


def test_redact_cookie_header():
    h = {"Cookie": "session=abc; user=def"}
    assert redact_headers(h)["Cookie"] == "***"


def test_redact_url_with_userinfo():
    url = "http://customer-tp_live_secret-cc-US:x@gw.tierproxy.com:443"
    redacted = redact_url(url)
    assert "tp_live_secret" not in redacted
    assert "@gw.tierproxy.com" in redacted


def test_redact_url_without_userinfo_unchanged():
    url = "https://api.tierproxy.com/v1/me"
    assert redact_url(url) == url


def test_redact_url_case_insensitive_header_match():
    h = {"AUTHORIZATION": "Bearer secret"}
    assert redact_headers(h)["AUTHORIZATION"] == "Bearer ***"
