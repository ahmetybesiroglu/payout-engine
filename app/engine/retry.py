"""
Exponential backoff retry logic for payment provider calls.

Implements the same pattern used in production: retry on transient failures
(429 rate limits, 503 service unavailable) with exponential backoff and
configurable max retries. Permanent failures (4xx client errors) are not retried.
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger("payout_engine.retry")

T = TypeVar("T")

RETRIABLE_STATUS_CODES = {429, 502, 503, 504}
MAX_RETRIES = 5
BASE_DELAY = 1.0
MAX_DELAY = 30.0


class ProviderError(Exception):
    """Base exception for payment provider errors."""

    def __init__(self, message: str, status_code: int = 500, retriable: bool = True):
        super().__init__(message)
        self.status_code = status_code
        self.retriable = retriable


class RateLimitError(ProviderError):
    """429 Too Many Requests from the payment provider."""

    def __init__(self, message: str = "Rate limited", retry_after: float | None = None):
        super().__init__(message, status_code=429, retriable=True)
        self.retry_after = retry_after


class PermanentError(ProviderError):
    """Non-retriable error (e.g. invalid account, bad request)."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, status_code=status_code, retriable=False)


async def with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = MAX_RETRIES,
    **kwargs: Any,
) -> Any:
    """
    Execute an async function with exponential backoff on retriable errors.

    Args:
        func: Async callable to execute.
        max_retries: Maximum number of retry attempts.

    Returns:
        The result of the function call.

    Raises:
        ProviderError: On permanent failure or exhausted retries.
    """
    delay = BASE_DELAY
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except ProviderError as e:
            last_error = e
            if not e.retriable:
                raise

            if attempt < max_retries:
                sleep_for = min(delay, MAX_DELAY)
                if isinstance(e, RateLimitError) and e.retry_after:
                    sleep_for = min(e.retry_after, MAX_DELAY)

                logger.warning(
                    "Retriable error on attempt %d/%d: %s — sleeping %.1fs",
                    attempt + 1,
                    max_retries + 1,
                    e,
                    sleep_for,
                )
                await asyncio.sleep(sleep_for)
                delay = min(delay * 2, MAX_DELAY)
            else:
                logger.error("Exhausted %d retries for provider call: %s", max_retries, e)
                raise

    raise last_error or ProviderError("Unknown error after retries")
