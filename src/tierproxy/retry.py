from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetryPolicy:
    """Exponential-backoff retry policy with jitter.

    On each retryable failure the client sleeps
    ``initial_delay_seconds * (multiplier ** attempt) * uniform(1-jitter, 1+jitter)``
    seconds, capped at ``max_delay_seconds``, up to ``max_retries`` times.
    Failures considered retryable:

    - HTTP status codes in :attr:`retry_on_status` (default: 408, 429, 500,
      502, 503, 504)
    - ``httpx.ConnectError``, ``httpx.NetworkError``, ``httpx.TimeoutException``

    Attributes:
        max_retries: Maximum attempts after the first. Default 3 = up to 4
            total requests.
        initial_delay_seconds: Initial backoff in seconds. Default 0.5.
        max_delay_seconds: Upper bound on a single sleep. Default 30.0.
        multiplier: Exponential growth factor applied to each successive
            delay. Default 2.0.
        jitter: Fractional jitter applied symmetrically around the computed
            delay (e.g. 0.25 means ±25%). Default 0.25.
        retry_on_status: HTTP status codes that should trigger a retry.
            Default is the common transient set (408, 429, 500, 502, 503, 504).
        retry_on_methods: HTTP methods eligible for retry. Non-idempotent
            methods (e.g. POST) are excluded by default. Default is
            GET, HEAD, OPTIONS, PUT, DELETE.

    Example:
        Aggressive (8 retries, fast)::

            RetryPolicy(max_retries=8, initial_delay_seconds=0.1, max_delay_seconds=5.0)

        Conservative (1 retry, slow)::

            RetryPolicy(max_retries=1, initial_delay_seconds=2.0, max_delay_seconds=2.0)
    """

    max_retries: int = 3
    initial_delay_seconds: float = 0.5
    max_delay_seconds: float = 30.0
    multiplier: float = 2.0
    jitter: float = 0.25
    retry_on_status: frozenset[int] = field(
        default_factory=lambda: frozenset({408, 429, 500, 502, 503, 504})
    )
    retry_on_methods: frozenset[str] = field(
        default_factory=lambda: frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})
    )

    def should_retry(
        self,
        attempt: int,
        method: str,
        status_code: int | None,
        had_network_error: bool,
        is_idempotent: bool,
    ) -> bool:
        """Return True if the request should be retried given the current attempt state."""
        if attempt >= self.max_retries:
            return False
        if had_network_error:
            return method in self.retry_on_methods or is_idempotent
        if status_code is None:
            return False
        if status_code == 429:
            return True
        if status_code in self.retry_on_status:
            return method in self.retry_on_methods or is_idempotent
        return False

    def delay(self, attempt: int, retry_after: float | None = None) -> float:
        """Compute sleep duration in seconds for the given attempt number.

        Respects the ``Retry-After`` value when provided; otherwise applies
        exponential backoff with jitter capped at ``max_delay_seconds``.
        """
        if retry_after is not None:
            return min(retry_after, self.max_delay_seconds)
        base = min(
            self.initial_delay_seconds * (self.multiplier**attempt),
            self.max_delay_seconds,
        )
        jr = base * self.jitter
        return base + random.uniform(-jr, jr)  # noqa: S311
