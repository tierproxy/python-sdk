import os

import pytest

from tierproxy import TierProxy


@pytest.fixture
def client() -> TierProxy:
    return TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://test.local")


def pytest_collection_modifyitems(config, items):  # type: ignore[no-untyped-def]
    has_real_key = bool(os.environ.get("TIERPROXY_API_KEY"))
    for item in items:
        if "requires_real_gateway" in item.keywords and not has_real_key:
            item.add_marker(pytest.mark.skip(reason="TIERPROXY_API_KEY not set"))


def pytest_configure(config):  # type: ignore[no-untyped-def]
    config.addinivalue_line(
        "markers",
        "requires_real_gateway: e2e against a live gateway; needs TIERPROXY_API_KEY",
    )
    config.addinivalue_line(
        "markers",
        "mocked_e2e: e2e against the mock gateway fixture (always runnable)",
    )
