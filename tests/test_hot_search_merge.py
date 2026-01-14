from __future__ import annotations

import unittest

from app.hot_search.merge import merge_and_rank
from app.hot_search.normalization import normalize_keyword


class HotSearchNormalizationTestCase(unittest.TestCase):
    def test_normalize_keyword_casefold_and_whitespace(self) -> None:
        self.assertEqual(normalize_keyword("  RAG   Demo "), "rag demo")
        self.assertEqual(normalize_keyword("中文 RAG"), "中文 rag")
        self.assertEqual(normalize_keyword(""), "")


class HotSearchMergeTestCase(unittest.TestCase):
    def test_merge_blocked_and_pinned(self) -> None:
        raw = [("a", 10), ("b", 9), ("c", 8)]
        blocked = {"b"}
        pinned = {1: "c"}

        items = merge_and_rank(raw_items=raw, blocked_words=blocked, pinned_positions=pinned, limit=3)
        self.assertEqual([i.keyword for i in items], ["c", "a"])
        self.assertTrue(items[0].is_pinned)
        self.assertEqual(items[0].heat_score, 8.0)

    def test_blocked_overrides_pinned(self) -> None:
        raw = [("a", 10), ("b", 9)]
        blocked = {"b"}
        pinned = {1: "b"}

        items = merge_and_rank(raw_items=raw, blocked_words=blocked, pinned_positions=pinned, limit=2)
        self.assertEqual([i.keyword for i in items], ["a"])

    def test_duplicate_pinned_word_deduped(self) -> None:
        raw = [("a", 10), ("b", 9), ("c", 8)]
        pinned = {1: "b", 2: "b"}

        items = merge_and_rank(raw_items=raw, blocked_words=set(), pinned_positions=pinned, limit=3)
        self.assertEqual([i.keyword for i in items], ["b", "a", "c"])

    def test_pinned_rank_beyond_limit_is_ignored(self) -> None:
        raw = [("a", 10), ("b", 9), ("c", 8)]
        pinned = {5: "x"}

        items = merge_and_rank(raw_items=raw, blocked_words=set(), pinned_positions=pinned, limit=3)
        self.assertEqual([i.keyword for i in items], ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()

