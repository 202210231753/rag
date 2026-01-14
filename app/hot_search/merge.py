from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class MergedTrendingItem:
    keyword: str
    heat_score: float
    is_pinned: bool


def merge_and_rank(
    raw_items: Sequence[tuple[str, float]],
    blocked_words: set[str],
    pinned_positions: dict[int, str],
    limit: int,
) -> list[MergedTrendingItem]:
    """
    合并榜单与治理规则，生成最终 TopN（纯函数，便于单测）

    规则优先级：blocked > pinned > 自然热度排序
    - blocked：无论是否置顶，都不会出现在最终榜单
    - pinned：按 rank(1-based) 强制插入指定位置，并从自然榜中去重
    """
    if limit <= 0:
        return []

    score_map: dict[str, float] = {}
    ordered_keywords: list[str] = []
    seen: set[str] = set()

    for keyword, score in raw_items:
        if not keyword or keyword in blocked_words:
            continue
        if keyword in seen:
            score_map[keyword] = float(score)
            continue
        seen.add(keyword)
        ordered_keywords.append(keyword)
        score_map[keyword] = float(score)

    normalized_pins: list[tuple[int, str]] = [
        (rank, word)
        for rank, word in pinned_positions.items()
        if isinstance(rank, int)
        and 0 < rank <= limit
        and isinstance(word, str)
        and word
    ]
    normalized_pins.sort(key=lambda x: x[0])

    pinned_words: set[str] = set()
    deduped_pins: list[tuple[int, str]] = []
    for rank, word in normalized_pins:
        if word in blocked_words:
            continue
        if word in pinned_words:
            continue
        pinned_words.add(word)
        deduped_pins.append((rank, word))

    base_keywords: list[str] = [
        keyword for keyword in ordered_keywords if keyword not in pinned_words
    ]

    final_keywords: list[str] = list(base_keywords)
    for rank, word in deduped_pins:
        index = rank - 1
        if index < 0:
            index = 0
        if index >= len(final_keywords):
            final_keywords.append(word)
        else:
            final_keywords.insert(index, word)

    items: list[MergedTrendingItem] = []
    for keyword in final_keywords[:limit]:
        items.append(
            MergedTrendingItem(
                keyword=keyword,
                heat_score=float(score_map.get(keyword, 0.0)),
                is_pinned=keyword in pinned_words,
            )
        )
    return items
