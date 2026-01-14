from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.intervention.cache import TimedCache
from app.intervention.enums import CensorSource, MiningStatus, WhitelistStatus
from app.intervention.matcher import AhoCorasickMatcher
from app.intervention.miner import mine_ngrams, suggest_level
from app.intervention.policies import CensorDecision, LevelPolicy
from app.intervention.repositories import CensorMiningRepository, CensorRepository, WhitelistRepository

# 3 个核心 Service：
# WhitelistService	用户级白名单 / 封禁：判断某个用户是否被锁 / 是否绕过审查
# # CensorService	实时文本审查（查词 + 决策）：
#     给定一段文本，快速判断：
#     是否命中敏感词
#     命中最高等级
#     是 mask / refuse / lock
#     返回命中的词和位置
# CensorMiningService	离线挖掘潜在敏感词



@dataclass(frozen=True)
class WhitelistSnapshot:
    user_status: dict[str, str]


@dataclass(frozen=True)
class CensorSnapshot:
    patterns: list[tuple[str, int]]  # (word, level)


class WhitelistService:
    def __init__(self, repo: WhitelistRepository | None = None, ttl_seconds: int = 300) -> None:
        self._repo = repo or WhitelistRepository()
        self._cache: TimedCache[WhitelistSnapshot] | None = None
        self._ttl_seconds = ttl_seconds

    def _get_cache(self, db: Session) -> TimedCache[WhitelistSnapshot]:
        if self._cache is None:
            # IMPORTANT: do NOT close over the request-scoped Session here.
            # This service is a module-level singleton and will be reused across requests.
            # If we capture `db` from the first request, later refreshes will use a closed/invalid session.
            def _load() -> WhitelistSnapshot:
                s = SessionLocal()
                try:
                    return WhitelistSnapshot(self._repo.snapshot(s))
                finally:
                    s.close()

            self._cache = TimedCache(self._ttl_seconds, loader=_load)
        return self._cache

    def invalidate(self) -> None:
        if self._cache is not None:
            self._cache.invalidate()

    def upsert_users(self, db: Session, user_ids: Sequence[str], status: WhitelistStatus, updated_by: str | None = None, reason: str | None = None) -> int:
        n = self._repo.upsert_many(db, user_ids=user_ids, status=status, updated_by=updated_by, reason=reason)
        # admin intervention should take effect immediately
        self.invalidate()
        return n

    def delete_users(self, db: Session, user_ids: Sequence[str]) -> int:
        n = self._repo.delete_many(db, user_ids=user_ids)
        self.invalidate()
        return n

    def get_status(self, db: Session, user_id: str) -> str:
        snap = self._get_cache(db).get()
        return snap.user_status.get(user_id, WhitelistStatus.unlocked.value)

    def is_locked(self, db: Session, user_id: str) -> bool:
        return self.get_status(db, user_id) == WhitelistStatus.locked.value


class CensorService:
    def __init__(
        self,
        repo: CensorRepository | None = None,
        ttl_seconds: int = 300,
        policy: LevelPolicy | None = None,
    ) -> None:
        self._repo = repo or CensorRepository()
        self._ttl_seconds = ttl_seconds
        self._policy = policy or LevelPolicy()
        self._cache: TimedCache[CensorSnapshot] | None = None
        self._matcher: AhoCorasickMatcher | None = None

    def _load_snapshot(self) -> CensorSnapshot:
        s = SessionLocal()
        try:
            rows = self._repo.list_active(s)
            patterns = [(r.word, int(r.level)) for r in rows]
            return CensorSnapshot(patterns=patterns)
        finally:
            s.close()

    def _get_cache(self, db: Session) -> TimedCache[CensorSnapshot]:
        if self._cache is None:
            # Same reason as WhitelistService: never capture request Session in a singleton cache loader.
            self._cache = TimedCache(self._ttl_seconds, loader=self._load_snapshot)
        return self._cache

    def _get_matcher(self, db: Session) -> AhoCorasickMatcher:
        snap = self._get_cache(db).get()
        if self._matcher is None or self._get_cache(db)._invalidated:  # type: ignore[attr-defined]
            matcher = AhoCorasickMatcher()
            matcher.build(snap.patterns)
            self._matcher = matcher
        return self._matcher

    def invalidate(self) -> None:
        if self._cache is not None:
            self._cache.invalidate()
        self._matcher = None

    def upsert_words(
        self,
        db: Session,
        words: Sequence[str],
        levels: Sequence[int],
        *,
        updated_by: str | None = None,
        source: CensorSource = CensorSource.manual,
        approved: bool = True,
        enabled: bool = True,
    ) -> int:
        n = self._repo.upsert_many(
            db,
            words=words,
            levels=levels,
            updated_by=updated_by,
            source=source,
            approved=approved,
            enabled=enabled,
        )
        self.invalidate()
        return n

    def delete_words(self, db: Session, words: Sequence[str]) -> int:
        n = self._repo.delete_many(db, words=words)
        self.invalidate()
        return n

    def check(self, db: Session, text: str) -> CensorDecision:
        matcher = self._get_matcher(db)
        matches = matcher.find(text)
        return self._policy.decide(text, matches)


class CensorMiningService:
    def __init__(
        self,
        repo: CensorMiningRepository | None = None,
        censor_repo: CensorRepository | None = None,
    ) -> None:
        self._repo = repo or CensorMiningRepository()
        self._censor_repo = censor_repo or CensorRepository()

    def mine_and_submit(
        self,
        db: Session,
        texts: Sequence[str],
        *,
        ngram_range=(2, 4),
        min_count: int = 5,
        top_k: int = 200,
        evidence: str | None = None,
    ) -> int:
        mined = mine_ngrams(texts, ngram_range=ngram_range, min_count=min_count, top_k=top_k)
        candidates = []
        for c in mined:
            candidates.append((c.word, suggest_level(c.word), c.score, evidence))
        return self._repo.submit_candidates(db, candidates)

    def list_pending(self, db: Session, skip: int = 0, limit: int = 200):
        return self._repo.list_pending(db, skip=skip, limit=limit)

    def approve(self, db: Session, candidate_ids: Sequence[int], reviewed_by: str | None = None) -> int:
        return self._repo.mark_reviewed(db, candidate_ids, status=MiningStatus.approved, reviewed_by=reviewed_by)

    def approve_and_publish(
        self,
        db: Session,
        candidate_ids: Sequence[int],
        *,
        reviewed_by: str | None = None,
        updated_by: str | None = None,
    ) -> tuple[int, int]:
        """Approve mining candidates and publish them into active censor word list.

        Returns: (approved_count, published_count)
        """

        approved_count = self.approve(db, candidate_ids, reviewed_by=reviewed_by)
        candidates = self._repo.get_by_ids(db, candidate_ids)

        words: list[str] = []
        levels: list[int] = []
        for c in candidates:
            if c.status != MiningStatus.approved.value:
                continue
            words.append(c.word)
            levels.append(int(c.suggested_level))

        if not words:
            return approved_count, 0

        published_count = self._censor_repo.upsert_many(
            db,
            words=words,
            levels=levels,
            approved=True,
            source=CensorSource.mined,
            enabled=True,
            updated_by=updated_by or reviewed_by,
        )
        return approved_count, published_count

    def reject(self, db: Session, candidate_ids: Sequence[int], reviewed_by: str | None = None) -> int:
        return self._repo.mark_reviewed(db, candidate_ids, status=MiningStatus.rejected, reviewed_by=reviewed_by)
