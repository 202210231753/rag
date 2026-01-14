from __future__ import annotations

from app.hot_search.service import HotSearchService


class DecayScheduler:
    def __init__(self, hot_search_service: HotSearchService, *, lock_ttl_seconds: int = 3300):
        self._service = hot_search_service
        self._lock_ttl_seconds = int(lock_ttl_seconds)

    async def execute_decay_cycle(self) -> bool:
        return await self._service.decay_once(lock_ttl_seconds=self._lock_ttl_seconds)

