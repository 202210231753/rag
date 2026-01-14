from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List


@dataclass
class _TrieNode:
    children: Dict[str, "_TrieNode"] = field(default_factory=dict)
    is_word: bool = False


class TermTrie:
    """
    面向中文短语的前缀树，用于高效匹配自定义词条。

    设计目标：
    - 构建开销可接受（词条变更时重建）
    - 查找最长/全部匹配用于不同分词策略
    """

    def __init__(self, terms: Iterable[str] = ()) -> None:
        self._root = _TrieNode()
        self._term_count = 0
        for term in terms:
            self.insert(term)

    @property
    def term_count(self) -> int:
        return self._term_count

    def insert(self, term: str) -> None:
        if not term:
            return
        node = self._root
        for ch in term:
            node = node.children.setdefault(ch, _TrieNode())
        if not node.is_word:
            node.is_word = True
            self._term_count += 1

    def find_longest(self, text: str, start: int) -> int:
        """
        返回从 start 开始的最长匹配长度（未命中返回 0）。
        """
        node = self._root
        longest = 0
        for offset, ch in enumerate(text[start:], start=1):
            node = node.children.get(ch)
            if node is None:
                break
            if node.is_word:
                longest = offset
        return longest

    def find_all(self, text: str, start: int) -> List[int]:
        """
        返回从 start 开始的全部匹配长度列表（升序）。
        """
        node = self._root
        matches: List[int] = []
        for offset, ch in enumerate(text[start:], start=1):
            node = node.children.get(ch)
            if node is None:
                break
            if node.is_word:
                matches.append(offset)
        return matches

