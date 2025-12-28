from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class MiningCandidate:
    word: str
    score: float


def mine_ngrams(
    texts: Iterable[str],
    ngram_range: Tuple[int, int] = (2, 4),
    min_count: int = 5,
    top_k: int = 200,
) -> List[MiningCandidate]:
    """A simple frequency-based miner.

    Works reasonably for Chinese (character ngrams) and general text.
    This is intentionally lightweight (no extra dependencies).
    """

    min_n, max_n = ngram_range
    counter: Counter[str] = Counter()

    for text in texts:
        if not text:
            continue
        s = str(text)
        length = len(s)
        for n in range(min_n, max_n + 1):
            if length < n:
                continue
            for i in range(0, length - n + 1):
                gram = s[i : i + n]
                if gram.strip() == "":
                    continue
                counter[gram] += 1

    items = [(w, c) for w, c in counter.items() if c >= min_count]
    items.sort(key=lambda x: x[1], reverse=True)
    items = items[:top_k]
    return [MiningCandidate(word=w, score=float(c)) for w, c in items]


def suggest_level(word: str) -> int:
    """Heuristic level suggestion.

    You can replace this with a model/LLM-based classifier later.
    """
    if len(word) >= 6:
        return 2
    return 1
