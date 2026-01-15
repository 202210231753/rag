from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from app.hot_search.merge import MergedTrendingItem, merge_and_rank
from app.hot_search.normalization import normalize_keyword
from app.hot_search.repository import HotSearchRepository


class GovernanceService:
    def __init__(self, repo: HotSearchRepository):
        self._repo = repo

    async def add_blocked_words(self, words: list[str]) -> int:
        clean = _clean_keywords(words)
        return await self._repo.add_blocked_words(clean)

    async def remove_blocked_words(self, words: list[str]) -> int:
        clean = _clean_keywords(words)
        return await self._repo.remove_blocked_words(clean)

    async def get_blocked_words(self) -> set[str]:
        return await self._repo.get_blocked_words()

    async def pin_word(self, rank: int, keyword: str) -> None:
        if rank <= 0:
            raise ValueError("rank 必须是正整数（1-based）")
        normalized = normalize_keyword(keyword)
        if not normalized:
            raise ValueError("keyword 不能为空")
        await self._repo.set_pinned_word(rank, normalized)

    async def unpin_rank(self, rank: int) -> bool:
        if rank <= 0:
            raise ValueError("rank 必须是正整数（1-based）")
        return await self._repo.delete_pinned_rank(rank)

    async def get_pinned_positions(self) -> dict[int, str]:
        return await self._repo.get_pinned_positions()

    async def set_boosts(
        self,
        keyword: str,
        *,
        search_boost: Optional[float] = None,
        decay_factor: Optional[float] = None,
        base_decay_factor: float = 0.9,
    ) -> None:
        normalized = normalize_keyword(keyword)
        if not normalized:
            raise ValueError("keyword 不能为空")

        if search_boost is None and decay_factor is None:
            raise ValueError("search_boost 与 decay_factor 至少提供一个")

        if search_boost is not None:
            if search_boost <= 0:
                raise ValueError("search_boost 必须 > 0")
            await self._repo.set_search_boost(normalized, float(search_boost))

        if decay_factor is not None:
            if decay_factor <= 0 or decay_factor > 1:
                raise ValueError("decay_factor 必须在 (0, 1] 范围内")
            if decay_factor < base_decay_factor:
                raise ValueError(
                    f"decay_factor 不应小于全局衰减系数 {base_decay_factor}（更慢衰减/豁免才有意义）"
                )
            await self._repo.set_decay_factor(normalized, float(decay_factor))

    async def delete_boosts(self, keyword: str) -> tuple[bool, bool]:
        normalized = normalize_keyword(keyword)
        if not normalized:
            raise ValueError("keyword 不能为空")
        return await self._repo.delete_boost(normalized)

    async def get_all_boosts(self) -> dict[str, tuple[Optional[float], Optional[float]]]:
        return await self._repo.get_all_boosts()

    async def get_boost(self, keyword: str) -> tuple[Optional[float], Optional[float]]:
        normalized = normalize_keyword(keyword)
        if not normalized:
            raise ValueError("keyword 不能为空")
        boosts = await self._repo.get_boosts([normalized])
        return boosts.get(normalized, (None, None))


class HotSearchService:
    def __init__(
        self,
        repo: HotSearchRepository,
        governance: GovernanceService,
        *,
        base_increment: float = 1.0,
        base_decay_factor: float = 0.9,
        candidate_multiplier: int = 3,
    ):
        self._repo = repo
        self._governance = governance
        self._base_increment = float(base_increment)
        self._base_decay_factor = float(base_decay_factor)
        self._candidate_multiplier = int(candidate_multiplier)

    @property
    def base_decay_factor(self) -> float:
        return self._base_decay_factor

    @property
    def governance(self) -> GovernanceService:
        return self._governance

    async def record_search_action(self, keyword: str) -> float:
        normalized = normalize_keyword(keyword)
        if not normalized:
            return 0.0
        return await self._repo.incr_hot_score(normalized, base_increment=self._base_increment)

    async def get_trending_list(self, limit: int) -> dict:
        if limit <= 0:
            raise ValueError("limit 必须 > 0")

        candidate_limit = max(limit * self._candidate_multiplier, limit)
        raw_items = await self._repo.get_top_with_scores(candidate_limit)
        blocked_words, pinned_positions = await self._repo.get_governance_rules()

        merged: list[MergedTrendingItem] = merge_and_rank(
            raw_items=raw_items,
            blocked_words=blocked_words,
            pinned_positions=pinned_positions,
            limit=limit,
        )

        keywords = [item.keyword for item in merged]
        boosts = await self._repo.get_boosts(keywords)
        score_map = await self._repo.get_scores(keywords)

        items = []
        for idx, item in enumerate(merged, start=1):
            search_boost, decay_factor = boosts.get(item.keyword, (None, None))
            items.append(
                {
                    "rank": idx,
                    "keyword": item.keyword,
                    "heat_score": float(score_map.get(item.keyword, item.heat_score)),
                    "metadata": {
                        "is_pinned": item.is_pinned,
                        **(
                            {"search_boost": search_boost}
                            if search_boost is not None
                            else {}
                        ),
                        **(
                            {"decay_factor": decay_factor}
                            if decay_factor is not None
                            else {}
                        ),
                    },
                }
            )

        return {
            "limit": limit,
            "generated_at": datetime.now(timezone.utc),
            "items": items,
        }

    async def decay_once(self, lock_ttl_seconds: int = 3300) -> bool:
        acquired = await self._repo.try_acquire_decay_lock(lock_ttl_seconds)
        if not acquired:
            logger.info("热搜衰减任务跳过：未获取到锁（可能已在执行）")
            return False

        base = self._base_decay_factor
        await self._repo.apply_global_decay(base)

        decay_factors = await self._repo.get_all_decay_factors()
        if not decay_factors:
            return True

        await self._repo.apply_decay_corrections(
            base_factor=base,
            decay_factors=decay_factors,
        )
        return True


def _clean_keywords(words: list[str]) -> list[str]:
    clean: list[str] = []
    for word in words:
        normalized = normalize_keyword(word)
        if normalized:
            clean.append(normalized)
    return list(dict.fromkeys(clean))
