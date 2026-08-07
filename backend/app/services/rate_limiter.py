from collections import defaultdict, deque
import threading
import time


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        if limit <= 0 or window_seconds <= 0:
            return True

        now = time.monotonic()
        window_start = now - window_seconds

        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()

            if len(timestamps) >= limit:
                return False

            timestamps.append(now)
            return True


api_rate_limiter = InMemoryRateLimiter()
