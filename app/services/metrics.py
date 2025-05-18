from __future__ import annotations

"""Lightweight metrics collection utilities."""

from collections import defaultdict
from contextlib import contextmanager
import time
import logfire


class MetricsCollector:
    """Collect counters and latency measurements for monitoring."""

    def __init__(self) -> None:
        self.counters: dict[str, int] = defaultdict(int)
        self.latencies: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a named counter."""
        self.counters[name] += value

    def observe_latency(self, name: str, seconds: float) -> None:
        """Record a latency measurement for a metric."""
        self.latencies[name].append(seconds)

    def summary(self) -> dict:
        """Return collected metrics as a dictionary."""
        avg_latencies = {
            k: (sum(v) / len(v)) if v else 0 for k, v in self.latencies.items()
        }
        return {"counters": dict(self.counters), "avg_latencies": avg_latencies}


metrics_collector = MetricsCollector()


@contextmanager
def track_latency(metric_name: str) -> None:
    """Context manager that records the execution time of a block."""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        metrics_collector.observe_latency(metric_name, duration)
        logfire.debug(
            "Latency recorded", metric=metric_name, duration=round(duration, 4)
        )
