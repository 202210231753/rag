from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from app.intervention.enums import CensorPolicyAction
from app.intervention.matcher import Match


@dataclass(frozen=True)
class CensorDecision:
    hit: bool
    max_level: int
    action: CensorPolicyAction
    masked_text: str | None
    matches: Sequence[Match]


class LevelPolicy:
    """Simple tiered policy.

    You can change the thresholds in one place.

    Default:
    - level 1 => mask
    - level 2 => refuse
    - level 3+ => refuse (and can be extended to lock_user)
    """

    def __init__(
        self,
        mask_level: int = 1,
        refuse_level: int = 2,
        lock_level: int = 99,
        mask_char: str = "*",
    ) -> None:
        self.mask_level = mask_level
        self.refuse_level = refuse_level
        self.lock_level = lock_level
        self.mask_char = mask_char

    def decide(self, text: str, matches: Iterable[Match]) -> CensorDecision:
        matches = list(matches)
        if not matches:
            return CensorDecision(False, 0, CensorPolicyAction.allow, None, [])

        max_level = max(m.level for m in matches)

        if max_level >= self.lock_level:
            return CensorDecision(True, max_level, CensorPolicyAction.lock_user, None, matches)

        if max_level >= self.refuse_level:
            return CensorDecision(True, max_level, CensorPolicyAction.refuse, None, matches)

        if max_level >= self.mask_level:
            return CensorDecision(True, max_level, CensorPolicyAction.mask, self._mask(text, matches), matches)

        return CensorDecision(True, max_level, CensorPolicyAction.allow, None, matches)

    def _mask(self, text: str, matches: Sequence[Match]) -> str:
        chars = list(text)
        for m in matches:
            for i in range(max(0, m.start), min(len(chars), m.end)):
                chars[i] = self.mask_char
        return "".join(chars)
