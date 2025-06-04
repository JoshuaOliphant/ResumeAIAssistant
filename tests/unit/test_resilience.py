import asyncio
import pytest

from app.core.resilience import RateLimiter, CircuitBreaker


@pytest.mark.asyncio
async def test_rate_limiter_allows_within_limit():
    rl = RateLimiter(rate=2, window_seconds=1)
    assert await rl.allow("ip")
    assert await rl.allow("ip")
    assert not await rl.allow("ip")


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    cb = CircuitBreaker(failure_threshold=2, recovery_time_seconds=1)
    assert not await cb.is_open("svc")
    await cb.record_failure("svc")
    assert not await cb.is_open("svc")
    await cb.record_failure("svc")
    assert await cb.is_open("svc")
    await asyncio.sleep(1.1)
    assert not await cb.is_open("svc")

