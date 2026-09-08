"""Small bounded retry utility for transient provider calls."""

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry_provider_call(
    operation: Callable[[], T],
    *,
    retryable_errors: tuple[type[BaseException], ...],
    max_attempts: int,
    base_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[T, int]:
    """Retry with bounded exponential backoff and report the actual attempt count."""

    for attempt in range(1, max_attempts + 1):
        try:
            return operation(), attempt
        except retryable_errors:
            if attempt == max_attempts:
                raise
            sleep(base_seconds * (2 ** (attempt - 1)))
    raise RuntimeError("unreachable retry state")
