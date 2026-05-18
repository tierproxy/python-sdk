import pytest

from tierproxy.retry import RetryPolicy


@pytest.fixture
def policy() -> RetryPolicy:
    return RetryPolicy(max_retries=3)


def test_retries_on_500(policy: RetryPolicy) -> None:
    assert policy.should_retry(0, "GET", 500, False, True) is True


def test_does_not_retry_400(policy: RetryPolicy) -> None:
    assert policy.should_retry(0, "GET", 400, False, True) is False


def test_no_retry_post_without_idempotency(policy: RetryPolicy) -> None:
    assert policy.should_retry(0, "POST", None, True, False) is False


def test_retries_post_with_idempotency(policy: RetryPolicy) -> None:
    assert policy.should_retry(0, "POST", None, True, True) is True


def test_stops_after_max_retries(policy: RetryPolicy) -> None:
    assert policy.should_retry(3, "GET", 500, False, True) is False


def test_429_always_retries(policy: RetryPolicy) -> None:
    assert policy.should_retry(0, "POST", 429, False, False) is True


def test_delay_respects_retry_after(policy: RetryPolicy) -> None:
    assert policy.delay(0, retry_after=10) == 10.0


def test_delay_grows_exponentially(policy: RetryPolicy) -> None:
    d0 = policy.delay(0)
    d2 = policy.delay(2)
    assert d2 > d0
