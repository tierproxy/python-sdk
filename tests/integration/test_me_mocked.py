import pytest

from tierproxy import TierProxy


@pytest.mark.mocked_e2e
@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_me_mocked(mock_gateway):  # type: ignore[no-untyped-def]
    c = TierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF",
        base_url="https://gw.local.tierproxy.com:8444",
    )
    me = c.me.get()
    assert me.client_id == "mock_client"
    assert me.plan_id == "plan_mock"
