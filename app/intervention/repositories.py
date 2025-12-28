from __future__ import annotations

import datetime as dt
from typing import Iterable, Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.intervention.enums import CensorSource, MiningStatus, WhitelistStatus
from app.intervention.models import CensorMiningCandidate, CensorWord, WhitelistEntry


class WhitelistRepository:
    def upsert_many(
        self,
        db: Session,
        user_ids: Sequence[str],
        status: WhitelistStatus,
        updated_by: str | None = None,
        reason: str | None = None,
    ) -> int:
        now = dt.datetime.now(dt.timezone.utc)
        affected = 0
        for user_id in user_ids:
            if not user_id:
                continue
            existing = db.execute(select(WhitelistEntry).where(WhitelistEntry.user_id == user_id)).scalar_one_or_none()
            if existing is None:
                db.add(
                    WhitelistEntry(
                        user_id=user_id,
                        status=status.value,
                        updated_by=updated_by,
                        reason=reason,
                        created_at=now,
                        updated_at=now,
                    )
                )
            else:
                existing.status = status.value
                existing.updated_by = updated_by
                existing.reason = reason
                existing.updated_at = now
            affected += 1
        db.commit()
        return affected

    def delete_many(self, db: Session, user_ids: Sequence[str]) -> int:
        user_ids = [u for u in user_ids if u]
        if not user_ids:
            return 0
        result = db.execute(delete(WhitelistEntry).where(WhitelistEntry.user_id.in_(user_ids)))
        db.commit()
        return int(result.rowcount or 0)

    def list_all(self, db: Session, skip: int = 0, limit: int = 1000) -> list[WhitelistEntry]:
        return list(db.execute(select(WhitelistEntry).offset(skip).limit(limit)).scalars().all())

    def snapshot(self, db: Session) -> dict[str, str]:
        rows = db.execute(select(WhitelistEntry.user_id, WhitelistEntry.status)).all()
        return {user_id: status for user_id, status in rows}


class CensorRepository:
    def upsert_many(
        self,
        db: Session,
        words: Sequence[str],
        levels: Sequence[int],
        *,
        approved: bool = True,
        source: CensorSource = CensorSource.manual,
        enabled: bool = True,
        updated_by: str | None = None,
    ) -> int:
        now = dt.datetime.now(dt.timezone.utc)
        affected = 0
        for word, level in zip(words, levels, strict=False):
            if not word:
                continue
            level = int(level)
            existing = db.execute(select(CensorWord).where(CensorWord.word == word)).scalar_one_or_none()
            if existing is None:
                db.add(
                    CensorWord(
                        word=word,
                        level=level,
                        enabled=enabled,
                        source=source.value,
                        approved=approved,
                        updated_by=updated_by,
                        created_at=now,
                        updated_at=now,
                    )
                )
            else:
                existing.level = level
                existing.enabled = enabled
                existing.approved = approved
                existing.source = source.value
                existing.updated_by = updated_by
                existing.updated_at = now
            affected += 1
        db.commit()
        return affected

    def delete_many(self, db: Session, words: Sequence[str]) -> int:
        words = [w for w in words if w]
        if not words:
            return 0
        result = db.execute(delete(CensorWord).where(CensorWord.word.in_(words)))
        db.commit()
        return int(result.rowcount or 0)

    def list_active(self, db: Session) -> list[CensorWord]:
        stmt = select(CensorWord).where(CensorWord.enabled == True, CensorWord.approved == True)  # noqa: E712
        return list(db.execute(stmt).scalars().all())

    def count(self, db: Session) -> int:
        return int(db.execute(select(func.count()).select_from(CensorWord)).scalar_one())


class CensorMiningRepository:
    def submit_candidates(
        self,
        db: Session,
        candidates: Iterable[tuple[str, int, float, str | None]],
    ) -> int:
        now = dt.datetime.now(dt.timezone.utc)
        n = 0
        for word, level, score, evidence in candidates:
            if not word:
                continue
            db.add(
                CensorMiningCandidate(
                    word=word,
                    suggested_level=int(level),
                    score=float(score),
                    status=MiningStatus.pending.value,
                    evidence=evidence,
                    created_at=now,
                )
            )
            n += 1
        db.commit()
        return n

    def list_pending(self, db: Session, skip: int = 0, limit: int = 200) -> list[CensorMiningCandidate]:
        stmt = (
            select(CensorMiningCandidate)
            .where(CensorMiningCandidate.status == MiningStatus.pending.value)
            .order_by(CensorMiningCandidate.score.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def mark_reviewed(
        self,
        db: Session,
        candidate_ids: Sequence[int],
        status: MiningStatus,
        reviewed_by: str | None = None,
    ) -> int:
        now = dt.datetime.now(dt.timezone.utc)
        ids = [int(i) for i in candidate_ids]
        if not ids:
            return 0
        rows = list(db.execute(select(CensorMiningCandidate).where(CensorMiningCandidate.id.in_(ids))).scalars().all())
        for row in rows:
            row.status = status.value
            row.reviewed_at = now
            row.reviewed_by = reviewed_by
        db.commit()
        return len(rows)
