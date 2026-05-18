from tierproxy.errors import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    from_problem,
)


def test_401_maps_to_authentication_error() -> None:
    err = from_problem(401, {"type": "auth/x", "title": "no", "request_id": "r1"})
    assert isinstance(err, AuthenticationError)
    assert err.request_id == "r1"


def test_404_maps_to_not_found() -> None:
    err = from_problem(404, {"detail": "gone", "request_id": "r2"})
    assert isinstance(err, NotFoundError)
    assert "gone" in str(err)


def test_500_maps_to_server_error() -> None:
    err = from_problem(503, {"request_id": "r3"})
    assert isinstance(err, ServerError)


def test_429_carries_retry_after_attr() -> None:
    err = RateLimitError("slow", retry_after=10)
    assert err.retry_after == 10
