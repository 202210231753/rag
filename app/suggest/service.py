from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.hot_search.normalization import normalize_keyword
from app.hot_search.service import HotSearchService
from app.schemas.suggest_schema import SuggestionItem, SuggestionType
from app.suggest.fuzzy import levenshtein_distance_limited
from app.suggest.repository import SuggestRepository


@dataclass(frozen=True)
class SuggestConfig:
    history_max: int = 50
    trending_candidate_limit: int = 50
    fuzzy_candidate_limit: int = 200


class SuggestService:
    def __init__(
        self,
        repo: SuggestRepository,
        hot_search: HotSearchService,
        *,
        config: SuggestConfig | None = None,
    ) -> None:
        self._repo = repo
        self._hot_search = hot_search
        self._cfg = config or SuggestConfig()

    async def record_search(self, user_id: str | None, query: str) -> None:
        if not user_id:
            return
        keyword = normalize_keyword(query)
        if not keyword:
            return
        await asyncio.gather(
            self._repo.add_to_lexicon(keyword),
            self._repo.record_history(user_id, keyword, max_len=self._cfg.history_max),
        )

    async def get_zero_query_recs(
        self,
        *,
        user_id: str,
        limit: int,
        context: list[str] | None = None,
    ) -> list[SuggestionItem]:
        if limit <= 0:
            return []

        history_task = self._repo.get_history(user_id, limit=limit)
        trending_task = self._hot_search.get_trending_list(limit)
        history, trending_payload = await asyncio.gather(history_task, trending_task)

        trending = [str(x.get("keyword")) for x in (trending_payload.get("items") or []) if x.get("keyword")]
        ctx = [normalize_keyword(x) for x in (context or [])]
        ctx = [x for x in ctx if x]

        merged: list[SuggestionItem] = []
        seen: set[str] = set()

        def _append(items: list[str], type_name: SuggestionType) -> None:
            for value in items:
                if len(merged) >= limit:
                    return
                if not value or value in seen:
                    continue
                seen.add(value)
                merged.append(SuggestionItem(content=value, type=type_name))

        _append(history, "HISTORY")
        _append(ctx, "CONTEXT")
        _append(trending, "TRENDING")
        return merged

    async def auto_complete(
        self,
        *,
        user_id: str,
        query: str,
        limit: int,
        max_edit_dist: int,
    ) -> list[SuggestionItem]:
        if limit <= 0:
            return []
        max_edit_dist = 1 if max_edit_dist <= 0 else min(int(max_edit_dist), 2)

        q = normalize_keyword(query)
        if not q:
            return []

        # 精确前缀匹配：lexicon + history + trending（后两者规模小，直接过滤）
        lex_task = self._repo.search_prefix(q, limit=limit)
        history_task = self._repo.get_history(user_id, limit=self._cfg.history_max)
        trending_task = self._hot_search.get_trending_list(self._cfg.trending_candidate_limit)
        lex_matches, history, trending_payload = await asyncio.gather(lex_task, history_task, trending_task)

        trending = [str(x.get("keyword")) for x in (trending_payload.get("items") or []) if x.get("keyword")]
        exact_extra = [x for x in history if x.startswith(q)] + [x for x in trending if x.startswith(q)]

        exact: list[str] = []
        seen_exact: set[str] = set()
        for value in lex_matches + exact_extra:
            if not value or value in seen_exact:
                continue
            seen_exact.add(value)
            exact.append(value)
            if len(exact) >= limit:
                break

        items: list[SuggestionItem] = [
            SuggestionItem(
                content=value,
                type="COMPLETION",
                highlight_range=(0, len(q)),
                score=1.0,
            )
            for value in exact
        ]
        if len(items) >= limit:
            return items[:limit]

        # 模糊纠错：仅在候选池内计算（早停）
        pool: list[str] = []
        pool_seen: set[str] = set()
        for value in exact + history + trending:
            if not value or value in pool_seen:
                continue
            pool_seen.add(value)
            pool.append(value)
            if len(pool) >= self._cfg.fuzzy_candidate_limit:
                break

        corrections: list[tuple[int, str]] = []
        for cand in pool:
            if cand == q:
                continue
            dist = levenshtein_distance_limited(q, cand, max_edit_dist)
            if dist is None:
                continue
            corrections.append((dist, cand))

        corrections.sort(key=lambda x: (x[0], x[1]))
        for dist, cand in corrections:
            if len(items) >= limit:
                break
            score = (max_edit_dist - dist + 1) / (max_edit_dist + 1)
            items.append(
                SuggestionItem(
                    content=cand,
                    type="CORRECTION",
                    highlight_range=None,
                    score=float(score),
                )
            )

        return items
