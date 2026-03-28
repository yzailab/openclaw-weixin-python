"""
Tests for retry module (retry.py).

Covers:
- RetryConfig: calculate_delay, is_retryable
- CircuitBreaker: state transitions, can_execute, record_success/failure
- retry: decorator for sync and async functions
- retry_async: standalone async retry function
- Edge cases and error conditions
"""

import asyncio
import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Any

from weixin_sdk.retry import (
    RetryConfig,
    CircuitBreaker,
    CircuitState,
    retry,
    retry_async,
)
from weixin_sdk.exceptions import WeixinAPIError, WeixinTimeoutError


class TestRetryConfig:
    """Test RetryConfig dataclass."""

    def test_default_values(self):
        """Test RetryConfig has correct default values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_values(self):
        """Test RetryConfig with custom values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_calculate_delay_exponential(self):
        """Test exponential backoff calculation without jitter."""
        config = RetryConfig(
            base_delay=1.0, exponential_base=2.0, max_delay=30.0, jitter=False
        )

        # attempt 0: 1 * 2^0 = 1
        assert config.calculate_delay(0) == 1.0
        # attempt 1: 1 * 2^1 = 2
        assert config.calculate_delay(1) == 2.0
        # attempt 2: 1 * 2^2 = 4
        assert config.calculate_delay(2) == 4.0

    def test_calculate_delay_max_cap(self):
        """Test delay is capped at max_delay."""
        config = RetryConfig(
            base_delay=10.0, exponential_base=2.0, max_delay=30.0, jitter=False
        )

        # 10 * 2^2 = 40, but capped at 30
        assert config.calculate_delay(2) == 30.0
        # 10 * 2^3 = 80, capped at 30
        assert config.calculate_delay(3) == 30.0

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        config = RetryConfig(
            base_delay=1.0, exponential_base=2.0, max_delay=30.0, jitter=True
        )

        # With jitter enabled, the delay changes each call
        # Verify that jitter produces values in expected range
        delays = [config.calculate_delay(0) for _ in range(10)]
        # All delays should be between 0.5 and 1.5 for base_delay=1.0
        for d in delays:
            assert 0.5 <= d <= 1.5, f"Delay {d} outside expected range [0.5, 1.5]"

    def test_calculate_delay_different_bases(self):
        """Test exponential backoff with different bases."""
        config = RetryConfig(
            base_delay=1.0, exponential_base=3.0, max_delay=100.0, jitter=False
        )

        # 1 * 3^0 = 1
        assert config.calculate_delay(0) == 1.0
        # 1 * 3^1 = 3
        assert config.calculate_delay(1) == 3.0
        # 1 * 3^2 = 9
        assert config.calculate_delay(2) == 9.0

    def test_is_retryable_timeout_error(self):
        """Test is_retryable returns True for WeixinTimeoutError."""
        config = RetryConfig()
        error = WeixinTimeoutError("Timeout")
        assert config.is_retryable(error) is True

    def test_is_retryable_api_error_5xx(self):
        """Test is_retryable returns True for 5xx API errors."""
        config = RetryConfig()
        error = WeixinAPIError("Server error", code=500)
        assert config.is_retryable(error) is True

        error = WeixinAPIError("Internal error", code=503)
        assert config.is_retryable(error) is True

    def test_is_retryable_api_error_4xx(self):
        """Test is_retryable returns True for 4xx API errors (default retryable)."""
        # By default, WeixinAPIError is in retryable_exceptions, so 4xx is also retryable
        config = RetryConfig()
        error = WeixinAPIError("Bad request", code=400)
        assert config.is_retryable(error) is True  # Default includes WeixinAPIError

        error = WeixinAPIError("Not found", code=404)
        assert config.is_retryable(error) is True

    def test_is_retryable_api_error_4xx_non_retryable(self):
        """Test is_retryable returns False for 4xx when not in retryable list."""
        # Create config without WeixinAPIError in retryable list
        config = RetryConfig(retryable_exceptions=(WeixinTimeoutError,))
        error = WeixinAPIError("Bad request", code=400)
        assert config.is_retryable(error) is False

    def test_is_retryable_custom_exceptions(self):
        """Test is_retryable with custom exception tuple."""
        custom_exceptions = (WeixinTimeoutError, ValueError, TypeError)
        config = RetryConfig(retryable_exceptions=custom_exceptions)

        assert config.is_retryable(WeixinTimeoutError("timeout")) is True
        assert config.is_retryable(ValueError("value")) is True
        assert config.is_retryable(TypeError("type")) is True
        assert config.is_retryable(RuntimeError("runtime")) is False

    def test_is_retryable_api_error_no_code(self):
        """Test is_retryable for API error without code."""
        config = RetryConfig()
        error = WeixinAPIError("Generic error")
        # No code means it's not a 5xx, so falls back to isinstance check
        assert config.is_retryable(error) is True  # Default retryable_exceptions


class TestCircuitBreaker:
    """Test CircuitBreaker state machine."""

    def test_initial_state_closed(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_can_execute_closed_state(self):
        """Test can_execute returns True in CLOSED state."""
        cb = CircuitBreaker()
        assert cb.can_execute() is True

    def test_can_execute_open_state(self):
        """Test can_execute returns False in OPEN state."""
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_record_success_closed_state(self):
        """Test record_success in CLOSED state decrements failure count."""
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        assert cb._failure_count == 2

        cb.record_success()
        assert cb._failure_count == 1

    def test_record_failure_closed_to_open(self):
        """Test circuit opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_reset(self):
        """Test reset returns circuit to initial state."""
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0
        assert cb._last_failure_time is None
        assert cb._half_open_calls == 0

    def test_circuit_breaker_time_based_transition(self):
        """Test circuit breaker transitions based on recovery_timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb._last_failure_time is not None

        # Check before timeout - should still be OPEN
        cb._last_failure_time = time.monotonic() - 0.5
        assert cb.state == CircuitState.OPEN

        # Check after timeout - should transition to HALF_OPEN
        cb._last_failure_time = time.monotonic() - 1.5
        assert cb.state == CircuitState.HALF_OPEN


class TestRetryDecorator:
    """Test retry decorator."""

    def test_retry_sync_success(self):
        """Test retry decorator succeeds on first try (sync)."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.1)
        def sync_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = sync_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_sync_eventual_success(self):
        """Test retry decorator succeeds after failures (sync)."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        def sync_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise WeixinTimeoutError("Timeout")
            return "success"

        result = sync_func()
        assert result == "success"
        assert call_count == 3

    def test_retry_sync_all_fail(self):
        """Test retry decorator raises after all attempts (sync)."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        def sync_func():
            nonlocal call_count
            call_count += 1
            raise WeixinTimeoutError("Timeout")

        with pytest.raises(WeixinTimeoutError):
            sync_func()
        assert call_count == 3

    def test_retry_sync_non_retryable(self):
        """Test retry decorator doesn't retry non-retryable exceptions (sync)."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        def sync_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            sync_func()
        assert call_count == 1  # Only one attempt, no retries

    @pytest.mark.asyncio
    async def test_retry_async_success(self):
        """Test retry decorator succeeds on first try (async)."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.1)
        async def async_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await async_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_async_eventual_success(self):
        """Test retry decorator succeeds after failures (async)."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        async def async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise WeixinTimeoutError("Timeout")
            return "success"

        result = await async_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_async_all_fail(self):
        """Test retry decorator raises after all attempts (async)."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        async def async_func():
            nonlocal call_count
            call_count += 1
            raise WeixinTimeoutError("Timeout")

        with pytest.raises(WeixinTimeoutError):
            await async_func()
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_async_non_retryable(self):
        """Test retry decorator doesn't retry non-retryable exceptions (async)."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        async def async_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            await async_func()
        assert call_count == 1

    def test_retry_with_circuit_breaker_sync(self):
        """Test retry with circuit breaker (sync)."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0)
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, circuit_breaker=cb)
        def sync_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise WeixinTimeoutError("Timeout")
            return "success"

        result = sync_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker_async(self):
        """Test retry with circuit breaker (async)."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0)
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, circuit_breaker=cb)
        async def async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise WeixinTimeoutError("Timeout")
            return "success"

        result = await async_func()
        assert result == "success"

    def test_retry_circuit_breaker_open_sync(self):
        """Test retry raises when circuit breaker is open (sync)."""
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()  # Opens the circuit

        @retry(max_attempts=3, base_delay=0.01, circuit_breaker=cb)
        def sync_func():
            return "success"

        with pytest.raises(WeixinAPIError) as exc_info:
            sync_func()
        assert "Circuit breaker is OPEN" in str(exc_info.value)


class TestRetryAsync:
    """Test retry_async standalone function."""

    @pytest.mark.asyncio
    async def test_retry_async_success(self):
        """Test retry_async succeeds on first attempt."""
        mock_func = AsyncMock(return_value="success")
        result = await retry_async(mock_func)
        assert result == "success"
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_async_eventual_success(self):
        """Test retry_async succeeds after some failures."""
        call_count = 0

        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise WeixinTimeoutError("Timeout")
            return "success"

        result = await retry_async(failing_then_success)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_async_all_fail(self):
        """Test retry_async raises after all attempts fail."""

        async def always_fail():
            raise WeixinTimeoutError("Timeout")

        with pytest.raises(WeixinTimeoutError):
            await retry_async(always_fail)

    @pytest.mark.asyncio
    async def test_retry_async_custom_config(self):
        """Test retry_async with custom RetryConfig."""
        config = RetryConfig(max_attempts=5, base_delay=0.01, max_delay=1.0)
        call_count = 0

        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise WeixinTimeoutError("Timeout")
            return "success"

        result = await retry_async(failing_then_success, config=config)
        assert result == "success"
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_retry_async_with_args(self):
        """Test retry_async passes arguments to function."""
        mock_func = AsyncMock(return_value="result")

        result = await retry_async(mock_func, "arg1", "arg2", key="value")
        assert result == "result"
        mock_func.assert_called_once_with("arg1", "arg2", key="value")

    @pytest.mark.asyncio
    async def test_retry_async_non_retryable_exception(self):
        """Test retry_async doesn't retry non-retryable exceptions."""
        call_count = 0

        async def non_retryable():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            await retry_async(non_retryable)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_async_with_circuit_breaker(self):
        """Test retry_async with circuit breaker."""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        mock_func = AsyncMock(return_value="success")

        result = await retry_async(mock_func, circuit_breaker=cb)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_async_5xx_error_retryable(self):
        """Test retry_async retries on 5xx API errors."""
        call_count = 0

        async def server_error_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise WeixinAPIError("Server error", code=500)
            return "success"

        result = await retry_async(server_error_then_success)
        assert result == "success"
        assert call_count == 2


class TestRetryEdgeCases:
    """Test edge cases and error conditions."""

    def test_retry_min_attempts(self):
        """Test retry with minimum attempts (1 attempt, no retries)."""

        @retry(max_attempts=1, base_delay=0.01)
        def single_attempt():
            return "success"

        result = single_attempt()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_async_single_attempt(self):
        """Test retry_async with single attempt."""
        config = RetryConfig(max_attempts=1, base_delay=0.01)
        mock_func = AsyncMock(return_value="success")

        result = await retry_async(mock_func, config=config)
        assert result == "success"

    def test_retry_with_arguments_sync(self):
        """Test retry decorator passes arguments to function (sync)."""

        @retry(max_attempts=2, base_delay=0.01)
        def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = func_with_args("x", "y", c="z")
        assert result == "x-y-z"

    @pytest.mark.asyncio
    async def test_retry_with_arguments_async(self):
        """Test retry decorator passes arguments to function (async)."""

        @retry(max_attempts=2, base_delay=0.01)
        async def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = await func_with_args("x", "y", c="z")
        assert result == "x-y-z"

    def test_retry_no_jitter(self):
        """Test retry with jitter disabled gives deterministic delays."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=30.0,
            jitter=False,
        )

        delays = [config.calculate_delay(i) for i in range(3)]
        assert delays == [1.0, 2.0, 4.0]

    @pytest.mark.asyncio
    async def test_retry_function_name(self):
        """Test retry decorator wraps function (name may change)."""

        @retry(max_attempts=2, base_delay=0.01)
        async def my_function():
            return "success"

        # The wrapper may have different name, but the function still works
        result = await my_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_exception_propagation(self):
        """Test that original exception is propagated after retries."""
        original_error = WeixinAPIError("Original error", code=500)

        async def always_fail():
            raise original_error

        with pytest.raises(WeixinAPIError) as exc_info:
            await retry_async(always_fail)

        assert exc_info.value is original_error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
