"""
Retry strategy — exponential backoff and circuit breaking for data acquisition.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger("omega.data.orchestration.retry")

T = TypeVar("T")


def with_retry(
    fn: Callable[..., T],
    *args: Any,
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    backoff_max: float = 10.0,
    **kwargs: Any,
) -> Optional[T]:
    """Execute a function with exponential backoff retry.

    Args:
        fn: The function to call.
        *args: Positional arguments to pass to fn.
        max_attempts: Maximum number of attempts.
        backoff_base: Initial backoff delay in seconds.
        backoff_max: Maximum backoff delay in seconds.
        **kwargs: Keyword arguments to pass to fn.

    Returns:
        The function's return value, or None if all attempts failed.
    """
    last_error: Optional[Exception] = None

    for attempt in range(max_attempts):
        try:
            result = fn(*args, **kwargs)
            return result
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts - 1:
                delay = min(backoff_base * (2 ** attempt), backoff_max)
                logger.debug(
                    "Attempt %d/%d failed for %s: %s (retrying in %.1fs)",
                    attempt + 1, max_attempts, fn.__name__, exc, delay,
                )
                time.sleep(delay)
            else:
                logger.debug(
                    "All %d attempts failed for %s: %s",
                    max_attempts, fn.__name__, last_error,
                )

    return None
