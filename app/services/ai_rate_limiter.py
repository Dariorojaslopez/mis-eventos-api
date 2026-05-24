import asyncio
import time
from collections import defaultdict

from app.core.exceptions import AIRateLimitError


class AIRateLimiter:
    """Rate limiting en memoria por clave (p. ej. user_id)."""

    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def acquire(self, key: str) -> None:
        async with self._lock:
            now = time.monotonic()
            window_start = now - self._window_seconds
            recent = [ts for ts in self._hits[key] if ts > window_start]

            if len(recent) >= self._max_requests:
                raise AIRateLimitError(
                    "AI rate limit exceeded. Try again later.",
                    details={"retry_after_seconds": self._window_seconds},
                )

            recent.append(now)
            self._hits[key] = recent

    def reset(self) -> None:
        """Limpia contadores (útil en tests)."""
        self._hits.clear()
