from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

# 匹配算法（Aho–Corasick）

@dataclass(frozen=True)
class Match:
    word: str
    start: int
    end: int
    level: int


class AhoCorasickMatcher:
    """Minimal Aho-Corasick matcher.

    Supports Unicode strings and substring matching (useful for Chinese).
    """

    def __init__(self) -> None:
        self._next: List[Dict[str, int]] = [dict()]
        self._fail: List[int] = [0]
        self._out: List[List[Tuple[str, int]]] = [[]]  # (word, level)

    def build(self, patterns: Iterable[Tuple[str, int]]) -> None:
        self._next = [dict()]
        self._fail = [0]
        self._out = [[]]

        # Build trie
        for word, level in patterns:
            if not word:
                continue
            state = 0
            for ch in word:
                nxt = self._next[state].get(ch)
                if nxt is None:
                    nxt = len(self._next)
                    self._next[state][ch] = nxt
                    self._next.append(dict())
                    self._fail.append(0)
                    self._out.append([])
                state = nxt
            self._out[state].append((word, level))

        # Build failure links (BFS)
        queue: List[int] = []
        for ch, nxt in self._next[0].items():
            queue.append(nxt)
            self._fail[nxt] = 0

        head = 0
        while head < len(queue):
            r = queue[head]
            head += 1
            for ch, s in self._next[r].items():
                queue.append(s)
                f = self._fail[r]
                while f != 0 and ch not in self._next[f]:
                    f = self._fail[f]
                self._fail[s] = self._next[f].get(ch, 0)
                self._out[s].extend(self._out[self._fail[s]])

    def find(self, text: str) -> List[Match]:
        res: List[Match] = []
        state = 0
        for i, ch in enumerate(text):
            while state != 0 and ch not in self._next[state]:
                state = self._fail[state]
            state = self._next[state].get(ch, 0)
            if self._out[state]:
                for word, level in self._out[state]:
                    res.append(Match(word=word, start=i - len(word) + 1, end=i + 1, level=level))
        return res
