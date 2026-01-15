from __future__ import annotations

from pydantic import BaseModel, Field

from datetime import datetime

from app.intervention.enums import WhitelistStatus


class BulkWhitelistUpsert(BaseModel):
    user_ids: list[str] = Field(..., min_length=1)
    status: WhitelistStatus = Field(default=WhitelistStatus.unlocked)
    updated_by: str | None = None
    reason: str | None = None


class BulkWhitelistDelete(BaseModel):
    user_ids: list[str] = Field(..., min_length=1)


class WhitelistStatusResponse(BaseModel):
    user_id: str
    status: str


class BulkCensorUpsert(BaseModel):
    words: list[str] = Field(..., min_length=1)
    levels: list[int] = Field(..., min_length=1)
    updated_by: str | None = None


class BulkCensorDelete(BaseModel):
    words: list[str] = Field(..., min_length=1)


class CensorCheckRequest(BaseModel):
    text: str


class CensorCheckResponse(BaseModel):
    hit: bool
    max_level: int
    action: str
    masked_text: str | None
    matches: list[dict]


class MiningSubmitRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1)
    min_count: int = 5
    top_k: int = 200
    updated_by: str | None = None


class MiningReviewRequest(BaseModel):
    candidate_ids: list[int] = Field(..., min_length=1)
    reviewed_by: str | None = None


class MiningCandidateItem(BaseModel):
    id: int
    word: str
    suggested_level: int
    score: float
    status: str
    evidence: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
