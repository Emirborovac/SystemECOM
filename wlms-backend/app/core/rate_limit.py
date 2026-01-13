import time
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.core.config import settings

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore


@dataclass
class _Window:
    reset_at: float
    count: int


_mem: dict[str, _Window] = {}
_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if redis is None:
        return None
    try:
        _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception:
        _redis_client = None
        return None


def rate_limit(*, key: str, limit: int, window_seconds: int) -> None:
    """
    Best-effort rate limiter.
    Uses Redis if reachable; otherwise falls back to in-memory (single process).
    """
    if limit <= 0:
        return

    r = _get_redis()
    if r is not None:
        bucket = f"rl:{key}:{window_seconds}"
        try:
            # Atomic-ish: INCR then set expiry on first hit
            n = r.incr(bucket)
            if n == 1:
                r.expire(bucket, window_seconds)
            if n > limit:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
            return
        except HTTPException:
            raise
        except Exception:
            # Fall back to memory on any Redis hiccup
            pass

    now = time.time()
    w = _mem.get(key)
    if w is None or now >= w.reset_at:
        _mem[key] = _Window(reset_at=now + window_seconds, count=1)
        return
    w.count += 1
    if w.count > limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")

