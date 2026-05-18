import pytest

from tierproxy import TierProxy


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "tp",  # too short
        "tp_live_with space x" + "A" * 8,  # whitespace
        "tp_live_with:colon" + "A" * 8,  # `:` collides with proxy URL grammar
        "tp_live_with@at" + "A" * 8,  # `@` collides with userinfo separator
        "tp_live_with\rNL" + "A" * 8,  # CR injection
        "tp_live_with\nNL" + "A" * 8,  # LF injection
        "tp_live_with\x00null" + "A" * 8,  # null byte
        "tp_live_too_long" + "A" * 200,  # > 128 chars
    ],
)
def test_api_key_rejected(bad):
    with pytest.raises(ValueError, match="api_key"):
        TierProxy(api_key=bad)


def test_api_key_accepted():
    TierProxy(api_key="tp_live_DEMOKEY1234567890ABCDEF")
    TierProxy(api_key="a-b_c.d-1234567890ABCDEF")  # all allowed chars
