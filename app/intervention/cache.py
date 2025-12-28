from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CachedValue(Generic[T]):
    value: T
    loaded_at: dt.datetime


class TimedCache(Generic[T]):
    """A simple in-process cache with TTL.

    Design goal for this project:
    - 'Intervention takes effect within 5 minutes' is satisfied by TTL refresh.
    - We also provide explicit invalidation so admin operations can take effect immediately.

    This cache is process-local. If you run multiple Uvicorn workers,
    each worker will maintain its own cache (still <= TTL).
    """

    def __init__(self, ttl_seconds: int, loader: Callable[[], T]):
        self._ttl = dt.timedelta(seconds=ttl_seconds)
        self._loader = loader
        self._cached: CachedValue[T] | None = None
        self._invalidated = True

    def invalidate(self) -> None:
        self._invalidated = True

    def get(self) -> T:
        now = dt.datetime.now(dt.timezone.utc)

        if self._cached is None:
            self._cached = CachedValue(self._loader(), now)
            self._invalidated = False
            return self._cached.value

        is_expired = now - self._cached.loaded_at >= self._ttl
        if self._invalidated or is_expired:
            self._cached = CachedValue(self._loader(), now)
            self._invalidated = False
        return self._cached.value
