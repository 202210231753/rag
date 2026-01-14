from __future__ import annotations

from typing import Protocol, Any

from app.suggest.keys import SuggestKeys


class _RedisLike(Protocol):
    @property
    def client(self) -> Any: ...


class SuggestRepository:
    def __init__(self, redis_client: _RedisLike, *, keys: SuggestKeys):
        self._redis_client = redis_client
        self._keys = keys

    async def record_history(self, user_id: str, keyword: str, *, max_len: int) -> None:
        if not user_id or not keyword:
            return
        key = self._keys.history(user_id)
        await self._redis_client.client.lpush(key, keyword)
        await self._redis_client.client.ltrim(key, 0, max_len - 1)

    async def get_history(self, user_id: str, *, limit: int) -> list[str]:
        if not user_id or limit <= 0:
            return []
        key = self._keys.history(user_id)
        items = await self._redis_client.client.lrange(key, 0, limit - 1)
        return [str(x) for x in (items or []) if x]

    async def add_to_lexicon(self, keyword: str) -> None:
        if not keyword:
            return
        await self._redis_client.client.zadd(self._keys.lexicon, {keyword: 0.0})

    async def search_prefix(self, prefix: str, *, limit: int) -> list[str]:
        if not prefix or limit <= 0:
            return []
        min_lex = f"[{prefix}"
        max_lex = f"[{prefix}\uffff"
        items = await self._redis_client.client.zrangebylex(
            self._keys.lexicon,
            min_lex,
            max_lex,
            start=0,
            num=limit,
        )
        return [str(x) for x in (items or []) if x]

