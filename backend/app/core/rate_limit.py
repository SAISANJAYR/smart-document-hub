"""
rate_limit.py — Fixed-window rate limiting as a FastAPI dependency.

Uses Redis (INCR + EXPIRE) when available so limits are shared across workers,
and falls back to an in-process counter when Redis is not running.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from app.services.redis_cache import redis_service

_memory: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))


class RateLimit:
    def __init__(self, times: int, seconds: int):
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request):
        ip = request.client.host if request.client else "anon"
        key = f"rl:{request.url.path}:{ip}"

        count: int
        client = redis_service.redis_client
        if client is not None:
            try:
                count = await client.incr(key)
                if count == 1:
                    await client.expire(key, self.seconds)
            except Exception:
                client = None
        if client is None:
            n, start = _memory[key]
            now = time.monotonic()
            if now - start > self.seconds:
                n, start = 0, now
            n += 1
            _memory[key] = (n, start)
            count = n

        if count > self.times:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a moment and try again.",
            )


def reset_memory_limits():
    _memory.clear()
