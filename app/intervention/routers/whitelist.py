from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.intervention.enums import WhitelistStatus
from app.intervention.schemas import (
    BulkWhitelistDelete,
    BulkWhitelistUpsert,
    WhitelistStatusResponse,
)
from app.intervention.services import WhitelistService

router = APIRouter()
service = WhitelistService()


@router.post("/upsert")
def upsert_whitelist(payload: BulkWhitelistUpsert, db: Session = Depends(get_db)):
    n = service.upsert_users(db, payload.user_ids, payload.status, updated_by=payload.updated_by, reason=payload.reason)
    return {"affected": n}


@router.post("/delete")
def delete_whitelist(payload: BulkWhitelistDelete, db: Session = Depends(get_db)):
    n = service.delete_users(db, payload.user_ids)
    return {"deleted": n}


@router.get("/status/{user_id}", response_model=WhitelistStatusResponse)
def get_status(user_id: str, db: Session = Depends(get_db)):
    return WhitelistStatusResponse(user_id=user_id, status=service.get_status(db, user_id))


@router.post("/lock")
def lock_users(payload: BulkWhitelistDelete, db: Session = Depends(get_db)):
    n = service.upsert_users(db, payload.user_ids, WhitelistStatus.locked)
    return {"locked": n}


@router.post("/unlock")
def unlock_users(payload: BulkWhitelistDelete, db: Session = Depends(get_db)):
    n = service.upsert_users(db, payload.user_ids, WhitelistStatus.unlocked)
    return {"unlocked": n}
