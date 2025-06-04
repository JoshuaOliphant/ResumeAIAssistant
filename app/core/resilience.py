from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Deque, Dict

from app.core.config import settings
from app.core.logging import get_logger


class RateLimitExceeded(Exception):
    """Exception raised when a rate limit is exceeded."""


class RateLimiter:
    """Simple sliding window rate limiter with optional burst capacity."""

    def __init__(self, rate: int, window_seconds: int = 60, burst: int = 0) -> None:
        self.rate = rate
        self.window = window_seconds
        self.burst = burst
        self.requests: Dict[str, Deque[float]] = defaultdict(deque)
        self.lock = asyncio.Lock()
        self.logger = get_logger("RateLimiter")

    async def allow(self, key: str) -> bool:
        """Return True if a request is allowed for the given key."""
        async with self.lock:
            now = time.time()
            window_start = now - self.window
            q = self.requests[key]
            while q and q[0] < window_start:
                q.popleft()

            if len(q) >= self.rate + self.burst:
                return False

            q.append(now)
            return True


@dataclass
class CircuitState:
    failures: int = 0
    open_until: datetime | None = None


class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(self, failure_threshold: int = 5, recovery_time_seconds: int = 60) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_time = timedelta(seconds=recovery_time_seconds)
        self.state: Dict[str, CircuitState] = defaultdict(CircuitState)
        self.lock = asyncio.Lock()
        self.logger = get_logger("CircuitBreaker")

    async def is_open(self, key: str) -> bool:
        async with self.lock:
            state = self.state[key]
            if state.open_until and datetime.now() < state.open_until:
                return True
            if state.open_until and datetime.now() >= state.open_until:
                state.open_until = None
                state.failures = 0
            return False

    async def record_failure(self, key: str) -> None:
        async with self.lock:
            state = self.state[key]
            state.failures += 1
            if state.failures >= self.failure_threshold:
                state.open_until = datetime.now() + self.recovery_time
                self.logger.warning(
                    f"Circuit opened for {key} until {state.open_until.isoformat()}"
                )

    async def record_success(self, key: str) -> None:
        async with self.lock:
            self.state[key] = CircuitState()

    async def call(self, key: str, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
        if await self.is_open(key):
            raise RuntimeError(f"Circuit open for {key}")
        try:
            result = await func(*args, **kwargs)
            await self.record_success(key)
            return result
        except Exception:
            await self.record_failure(key)
            raise


# Global instances configured from settings

evaluation_rate_limiter = RateLimiter(
    rate=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW,
    burst=settings.RATE_LIMIT_BURST,
)

evaluation_circuit_breaker = CircuitBreaker(
    failure_threshold=settings.CB_FAILURE_THRESHOLD,
    recovery_time_seconds=settings.CB_RECOVERY_TIME,
)


def get_circuit_breaker_status() -> Dict[str, Any]:
    """Return current circuit breaker status."""
    status = {}
    for key, state in evaluation_circuit_breaker.state.items():
        status[key] = {
            "failures": state.failures,
            "open_until": state.open_until.isoformat() if state.open_until else None,
            "is_open": state.open_until is not None and datetime.now() < state.open_until,
        }
    return {
        "failure_threshold": evaluation_circuit_breaker.failure_threshold,
        "recovery_time_seconds": evaluation_circuit_breaker.recovery_time.total_seconds(),
        "circuits": status,
        "timestamp": datetime.now().isoformat(),
    }


def reset_circuit_breaker(key: str | None = None) -> Dict[str, Any]:
    """Reset circuit breaker state."""
    if key:
        evaluation_circuit_breaker.state.pop(key, None)
    else:
        evaluation_circuit_breaker.state.clear()
    return {"status": "success", "reset_key": key}

