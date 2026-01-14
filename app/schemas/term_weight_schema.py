from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TermWeightSetRequest(BaseModel):
    term: str = Field(..., min_length=1, description="目标词条")
    weight: float = Field(..., ge=0.0, description="权重值（通常大于1提升权重，0-1降低权重）")

    model_config = ConfigDict(populate_by_name=True)

