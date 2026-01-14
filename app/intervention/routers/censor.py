from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.intervention.deps import require_admin
from app.intervention.schemas import (
    BulkCensorDelete,
    BulkCensorUpsert,
    CensorCheckRequest,
    CensorCheckResponse,
    MiningCandidateItem,
    MiningReviewRequest,
    MiningSubmitRequest,
)
from app.intervention.services import CensorMiningService, CensorService

router = APIRouter()
service = CensorService()
miner = CensorMiningService()


@router.post("/upsert")
def upsert_words(
    payload: BulkCensorUpsert,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    if len(payload.levels) == 1 and len(payload.words) > 1:
        levels = [payload.levels[0]] * len(payload.words)
    else:
        levels = payload.levels
    n = service.upsert_words(db, payload.words, levels, updated_by=payload.updated_by)
    return {"affected": n}


@router.post("/delete")
def delete_words(
    payload: BulkCensorDelete,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    n = service.delete_words(db, payload.words)
    return {"deleted": n}


@router.post("/check", response_model=CensorCheckResponse)
def check_text(
    payload: CensorCheckRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    decision = service.check(db, payload.text)
    return CensorCheckResponse(
        hit=decision.hit,
        max_level=decision.max_level,
        action=decision.action.value,
        masked_text=decision.masked_text,
        matches=[{"word": m.word, "start": m.start, "end": m.end, "level": m.level} for m in decision.matches],
    )


@router.post("/mining/submit")
def mining_submit(
    payload: MiningSubmitRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    n = miner.mine_and_submit(db, payload.texts, min_count=payload.min_count, top_k=payload.top_k)
    return {"submitted": n}


@router.get("/mining/pending", response_model=list[MiningCandidateItem])
def mining_pending(
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    rows = miner.list_pending(db, skip=skip, limit=limit)
    return [
        MiningCandidateItem(
            id=r.id,
            word=r.word,
            suggested_level=int(r.suggested_level),
            score=float(r.score),
            status=r.status,
            evidence=r.evidence,
            created_at=r.created_at,
            reviewed_at=r.reviewed_at,
            reviewed_by=r.reviewed_by,
        )
        for r in rows
    ]


@router.post("/mining/approve")
def mining_approve(
    payload: MiningReviewRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    approved, published = miner.approve_and_publish(
        db,
        payload.candidate_ids,
        reviewed_by=payload.reviewed_by,
        updated_by=payload.reviewed_by,
    )
    service.invalidate()
    return {"approved": approved, "published": published}


@router.post("/mining/reject")
def mining_reject(
    payload: MiningReviewRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    n = miner.reject(db, payload.candidate_ids, reviewed_by=payload.reviewed_by)
    return {"rejected": n}
