from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger

from app.core.redis_client import RedisClient


@dataclass(frozen=True)
class HotSearchKeys:
    hot_list: str = "hot_search_list"
    blocked_words: str = "blocked_words"
    pinned_words: str = "pinned_words"
    boost_search_factors: str = "boost_search_factors"
    boost_decay_factors: str = "boost_decay_factors"
    decay_lock: str = "hot_search:decay_lock"

    @classmethod
    def with_prefix(cls, prefix: str) -> "HotSearchKeys":
        """
        生成带前缀的 Key 集合（用于多环境/多项目共用 Redis 时隔离数据）
        """
        p = prefix or ""
        return cls(
            hot_list=f"{p}hot_search_list",
            blocked_words=f"{p}blocked_words",
            pinned_words=f"{p}pinned_words",
            boost_search_factors=f"{p}boost_search_factors",
            boost_decay_factors=f"{p}boost_decay_factors",
            decay_lock=f"{p}hot_search:decay_lock",
        )


class HotSearchRepository:
    def __init__(self, redis_client: RedisClient, keys: HotSearchKeys | None = None):
        self._redis_client = redis_client
        self._keys = keys or HotSearchKeys()

    @property
    def keys(self) -> HotSearchKeys:
        return self._keys

    async def incr_hot_score(self, keyword: str, base_increment: float = 1.0) -> float:
        """
        热度 +1（支持搜索增量倍率）

        使用 Lua 保证一次 RTT 完成 HGET + ZINCRBY。
        """
        if not keyword:
            return 0.0

        script = """
        local boost = redis.call('HGET', KEYS[1], ARGV[1])
        if (not boost) then
            boost = '1'
        end
        local delta = tonumber(ARGV[2]) * tonumber(boost)
        return redis.call('ZINCRBY', KEYS[2], delta, ARGV[1])
        """
        try:
            new_score = await self._redis_client.client.eval(
                script,
                2,
                self._keys.boost_search_factors,
                self._keys.hot_list,
                keyword,
                str(base_increment),
            )
            return float(new_score)
        except Exception as exc:
            logger.error(f"热度计数失败: keyword='{keyword}', err={exc}")
            raise

    async def get_top_with_scores(self, limit: int) -> list[tuple[str, float]]:
        if limit <= 0:
            return []
        result = await self._redis_client.client.zrevrange(
            self._keys.hot_list, 0, limit - 1, withscores=True
        )
        return [(str(word), float(score)) for word, score in result if word]

    async def get_governance_rules(self) -> tuple[set[str], dict[int, str]]:
        pipe = self._redis_client.client.pipeline()
        pipe.smembers(self._keys.blocked_words)
        pipe.hgetall(self._keys.pinned_words)
        blocked_raw, pinned_raw = await pipe.execute()

        blocked_words = set(blocked_raw or [])
        pinned_positions: dict[int, str] = {}
        for field, keyword in (pinned_raw or {}).items():
            rank = _parse_rank_field(field)
            if rank is None or not keyword:
                continue
            pinned_positions[rank] = str(keyword)

        return blocked_words, pinned_positions

    async def add_blocked_words(self, words: list[str]) -> int:
        if not words:
            return 0
        return await self._redis_client.client.sadd(self._keys.blocked_words, *words)

    async def remove_blocked_words(self, words: list[str]) -> int:
        if not words:
            return 0
        return await self._redis_client.client.srem(self._keys.blocked_words, *words)

    async def get_blocked_words(self) -> set[str]:
        return set(await self._redis_client.client.smembers(self._keys.blocked_words))

    async def set_pinned_word(self, rank: int, keyword: str) -> None:
        await self._redis_client.client.hset(
            self._keys.pinned_words, _format_rank_field(rank), keyword
        )

    async def delete_pinned_rank(self, rank: int) -> bool:
        deleted = await self._redis_client.client.hdel(
            self._keys.pinned_words, _format_rank_field(rank)
        )
        return bool(deleted)

    async def get_pinned_positions(self) -> dict[int, str]:
        raw = await self._redis_client.client.hgetall(self._keys.pinned_words)
        result: dict[int, str] = {}
        for field, keyword in (raw or {}).items():
            rank = _parse_rank_field(field)
            if rank is None or not keyword:
                continue
            result[rank] = str(keyword)
        return result

    async def set_search_boost(self, keyword: str, factor: float) -> None:
        await self._redis_client.client.hset(
            self._keys.boost_search_factors, keyword, str(factor)
        )

    async def set_decay_factor(self, keyword: str, factor: float) -> None:
        await self._redis_client.client.hset(
            self._keys.boost_decay_factors, keyword, str(factor)
        )

    async def delete_boost(self, keyword: str) -> tuple[bool, bool]:
        pipe = self._redis_client.client.pipeline()
        pipe.hdel(self._keys.boost_search_factors, keyword)
        pipe.hdel(self._keys.boost_decay_factors, keyword)
        deleted_search, deleted_decay = await pipe.execute()
        return bool(deleted_search), bool(deleted_decay)

    async def get_boosts(self, keywords: list[str]) -> dict[str, tuple[Optional[float], Optional[float]]]:
        if not keywords:
            return {}
        pipe = self._redis_client.client.pipeline()
        pipe.hmget(self._keys.boost_search_factors, keywords)
        pipe.hmget(self._keys.boost_decay_factors, keywords)
        search_values, decay_values = await pipe.execute()

        result: dict[str, tuple[Optional[float], Optional[float]]] = {}
        for idx, keyword in enumerate(keywords):
            search_factor = _to_float_or_none(search_values[idx]) if search_values else None
            decay_factor = _to_float_or_none(decay_values[idx]) if decay_values else None
            result[keyword] = (search_factor, decay_factor)
        return result

    async def get_all_boosts(self) -> dict[str, tuple[Optional[float], Optional[float]]]:
        pipe = self._redis_client.client.pipeline()
        pipe.hgetall(self._keys.boost_search_factors)
        pipe.hgetall(self._keys.boost_decay_factors)
        search_map, decay_map = await pipe.execute()

        result: dict[str, tuple[Optional[float], Optional[float]]] = {}
        for keyword in set((search_map or {}).keys()) | set((decay_map or {}).keys()):
            result[str(keyword)] = (
                _to_float_or_none((search_map or {}).get(keyword)),
                _to_float_or_none((decay_map or {}).get(keyword)),
            )
        return result

    async def try_acquire_decay_lock(self, ttl_seconds: int) -> bool:
        return bool(
            await self._redis_client.client.set(
                self._keys.decay_lock, "1", nx=True, ex=ttl_seconds
            )
        )

    async def apply_global_decay(self, factor: float) -> None:
        tmp_key = f"{self._keys.hot_list}:tmp_decay"
        # redis-py 的 zunionstore 在新版本中使用 Mapping[key->weight] 传权重
        await self._redis_client.client.zunionstore(tmp_key, {self._keys.hot_list: factor})
        await self._redis_client.client.rename(tmp_key, self._keys.hot_list)

    async def get_all_decay_factors(self) -> dict[str, float]:
        raw = await self._redis_client.client.hgetall(self._keys.boost_decay_factors)
        result: dict[str, float] = {}
        for keyword, value in (raw or {}).items():
            factor = _to_float_or_none(value)
            if factor is None:
                continue
            result[str(keyword)] = factor
        return result

    async def get_scores(self, keywords: list[str]) -> dict[str, float]:
        if not keywords:
            return {}
        pipe = self._redis_client.client.pipeline()
        for keyword in keywords:
            pipe.zscore(self._keys.hot_list, keyword)
        scores = await pipe.execute()

        result: dict[str, float] = {}
        for idx, keyword in enumerate(keywords):
            score = scores[idx]
            if score is None:
                continue
            result[keyword] = float(score)
        return result

    async def apply_decay_corrections(
        self, *, base_factor: float, decay_factors: dict[str, float]
    ) -> int:
        """
        在全局衰减（乘以 base_factor）之后，按词级 decay_factor 做纠偏。

        纠偏目标：old*base -> old*factor
        由于当前分数为 old*base，因此只需对当前分数乘以 (factor/base)。
        """
        if not decay_factors:
            return 0

        keywords = list(decay_factors.keys())
        score_pipe = self._redis_client.client.pipeline()
        for keyword in keywords:
            score_pipe.zscore(self._keys.hot_list, keyword)
        scores = await score_pipe.execute()

        pipe = self._redis_client.client.pipeline()
        adjusted_count = 0
        for idx, keyword in enumerate(keywords):
            score = scores[idx]
            if score is None:
                continue
            factor = decay_factors.get(keyword)
            if factor is None or factor == base_factor:
                continue
            ratio = factor / base_factor
            diff = float(score) * (ratio - 1.0)
            if diff == 0:
                continue
            pipe.zincrby(self._keys.hot_list, diff, keyword)
            adjusted_count += 1

        if adjusted_count > 0:
            await pipe.execute()
        return adjusted_count


def _format_rank_field(rank: int) -> str:
    return f"rank_{rank}"


def _parse_rank_field(field: str) -> Optional[int]:
    if not field or not isinstance(field, str):
        return None
    if not field.startswith("rank_"):
        return None
    try:
        rank = int(field.split("_", 1)[1])
        return rank if rank > 0 else None
    except (ValueError, IndexError):
        return None


def _to_float_or_none(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
