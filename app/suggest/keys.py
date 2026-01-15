from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SuggestKeys:
    """
    Suggest 模块 Redis Key 集合（可选前缀用于环境隔离）。
    """

    lexicon: str = "suggest:lexicon"
    history_prefix: str = "suggest:history:"

    @classmethod
    def with_prefix(cls, prefix: str) -> "SuggestKeys":
        p = prefix or ""
        return cls(
            lexicon=f"{p}suggest:lexicon",
            history_prefix=f"{p}suggest:history:",
        )

    def history(self, user_id: str) -> str:
        return f"{self.history_prefix}{user_id}"

