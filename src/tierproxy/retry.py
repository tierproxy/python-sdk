from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetryPolicy:
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
        if retry_after is not None:
            return min(retry_after, self.max_delay_seconds)
        base = min(
            self.initial_delay_seconds * (self.multiplier**attempt),
            self.max_delay_seconds,
        )
        jr = base * self.jitter
        return base + random.uniform(-jr, jr)  # noqa: S311
