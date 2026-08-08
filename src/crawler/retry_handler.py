"""
Retry handler with exponential backoff.

Provides configurable retry logic for different types of errors
encountered during web crawling (timeouts, rate limits, network errors).
"""

from __future__ import annotations

import asyncio
import random
from enum import Enum
from typing import Optional, Callable, Any, TypeVar, Coroutine

from src.utils.constants import RetryConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ErrorType(Enum):
    """Classification of errors for retry behavior selection."""
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"          # HTTP 429
    SERVICE_UNAVAILABLE = "service_unavailable"  # HTTP 503
    NETWORK = "network"
    CAPTCHA = "captcha"
    UNKNOWN = "unknown"


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(
        self,
        message: str,
        error_type: ErrorType,
        attempts: int,
        last_error: Optional[Exception] = None,
    ):
        self.error_type = error_type
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(message)


class RetryHandler:
    """
    Handles retry logic with exponential backoff and jitter.

    Supports different retry configurations based on error type,
    ensuring appropriate delays for rate limits vs. simple timeouts.
    """

    def __init__(self):
        self._config = RetryConfig()

    def get_retry_params(self, error_type: ErrorType) -> tuple[int, float]:
        """
        Get max retries and base delay for a given error type.

        Args:
            error_type: The classification of the error.

        Returns:
            A tuple of (max_retries, base_delay_seconds).
        """
        config_map = {
            ErrorType.TIMEOUT: (
                self._config.TIMEOUT_MAX_RETRIES,
                self._config.TIMEOUT_BASE_DELAY,
            ),
            ErrorType.RATE_LIMIT: (
                self._config.RATE_LIMIT_MAX_RETRIES,
                self._config.RATE_LIMIT_BASE_DELAY,
            ),
            ErrorType.SERVICE_UNAVAILABLE: (
                self._config.SERVICE_UNAVAILABLE_MAX_RETRIES,
                self._config.SERVICE_UNAVAILABLE_BASE_DELAY,
            ),
            ErrorType.NETWORK: (
                self._config.NETWORK_MAX_RETRIES,
                self._config.NETWORK_BASE_DELAY,
            ),
        }
        return config_map.get(
            error_type,
            (self._config.NETWORK_MAX_RETRIES, self._config.NETWORK_BASE_DELAY),
        )

    def calculate_delay(
        self, attempt: int, base_delay: float, add_jitter: bool = True
    ) -> float:
        """
        Calculate the delay for a specific retry attempt using exponential backoff.

        Args:
            attempt: The current attempt number (0-indexed).
            base_delay: The base delay in seconds.
            add_jitter: Whether to add random jitter to prevent thundering herd.

        Returns:
            The calculated delay in seconds.
        """
        delay = base_delay * (self._config.BACKOFF_MULTIPLIER ** attempt)
        delay = min(delay, self._config.MAX_DELAY)

        if add_jitter:
            # Add ±25% jitter
            jitter = delay * 0.25 * (2 * random.random() - 1)
            delay += jitter

        return max(delay, 0.1)  # Minimum 100ms

    @classmethod
    def classify_error(cls, error: Exception) -> ErrorType:
        """
        Classify an exception into an ErrorType for retry configuration.

        Args:
            error: The exception to classify.

        Returns:
            The appropriate ErrorType.
        """
        error_str = str(error).lower()

        # Timeout errors
        if "timeout" in error_str or "TimeoutError" in type(error).__name__:
            return ErrorType.TIMEOUT

        # Rate limiting (HTTP 429)
        if "429" in error_str or "too many requests" in error_str:
            return ErrorType.RATE_LIMIT

        # Service unavailable (HTTP 503)
        if "503" in error_str or "service unavailable" in error_str:
            return ErrorType.SERVICE_UNAVAILABLE

        # Network errors
        network_indicators = [
            "network", "connection", "dns", "socket",
            "econnrefused", "econnreset", "enotfound",
            "net::", "err_",
        ]
        if any(indicator in error_str for indicator in network_indicators):
            return ErrorType.NETWORK

        # CAPTCHA
        if "captcha" in error_str:
            return ErrorType.CAPTCHA

        return ErrorType.UNKNOWN

    async def execute_with_retry(
        self,
        operation: Callable[..., Coroutine[Any, Any, T]],
        *args,
        error_type: Optional[ErrorType] = None,
        on_retry: Optional[Callable[[int, float, ErrorType], None]] = None,
        **kwargs,
    ) -> T:
        """
        Execute an async operation with automatic retry on failure.

        Args:
            operation: The async function to execute.
            *args: Positional arguments for the operation.
            error_type: Override error classification (auto-detected if None).
            on_retry: Optional callback called before each retry with
                      (attempt, delay, error_type).
            **kwargs: Keyword arguments for the operation.

        Returns:
            The result of the operation.

        Raises:
            RetryExhaustedError: If all retry attempts fail.
        """
        last_error: Optional[Exception] = None
        detected_type = error_type or ErrorType.UNKNOWN
        max_retries, base_delay = self.get_retry_params(
            detected_type if error_type else ErrorType.NETWORK
        )

        for attempt in range(max_retries + 1):
            try:
                return await operation(*args, **kwargs)

            except Exception as e:
                last_error = e

                # Classify the error if not overridden
                if error_type is None:
                    detected_type = self.classify_error(e)
                    max_retries, base_delay = self.get_retry_params(detected_type)

                # CAPTCHA errors should not be retried
                if detected_type == ErrorType.CAPTCHA:
                    logger.warning("CAPTCHA tespit edildi. Retry yapılmayacak.")
                    raise RetryExhaustedError(
                        f"CAPTCHA detected: {e}",
                        error_type=detected_type,
                        attempts=attempt + 1,
                        last_error=e,
                    )

                # Check if we've exhausted retries
                if attempt >= max_retries:
                    break

                # Calculate delay
                delay = self.calculate_delay(attempt, base_delay)

                logger.warning(
                    "Hata oluştu (tip: %s, deneme: %d/%d): %s — "
                    "%.1f saniye sonra tekrar denenecek.",
                    detected_type.value,
                    attempt + 1,
                    max_retries + 1,
                    str(e),
                    delay,
                )

                # Notify caller before retry
                if on_retry:
                    on_retry(attempt + 1, delay, detected_type)

                await asyncio.sleep(delay)

        # All retries exhausted
        raise RetryExhaustedError(
            f"Tüm denemeler ({max_retries + 1}) başarısız oldu: {last_error}",
            error_type=detected_type,
            attempts=max_retries + 1,
            last_error=last_error,
        )
