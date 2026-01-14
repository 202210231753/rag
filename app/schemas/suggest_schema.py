"""
输入提示（Suggest）Schema

提供零查询推荐与输入中补全/纠错的请求响应模型。
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


SuggestionType = Literal["HISTORY", "TRENDING", "CONTEXT", "COMPLETION", "CORRECTION"]


class SuggestionItem(BaseModel):
    content: str = Field(..., min_length=1, description="候选词（已规范化）")
    type: SuggestionType = Field(..., description="候选来源类型")
    highlight_range: Optional[tuple[int, int]] = Field(
        default=None,
        description="高亮范围（0-based，[start,end)）",
        examples=[(0, 2)],
    )
    score: Optional[float] = Field(default=None, description="可选打分（越大越优）")


class SuggestionListResponse(BaseModel):
    limit: int = Field(..., ge=1, description="返回条数上限")
    items: list[SuggestionItem] = Field(default_factory=list, description="推荐列表")


class CompletionListResponse(BaseModel):
    limit: int = Field(..., ge=1, description="返回条数上限")
    items: list[SuggestionItem] = Field(default_factory=list, description="补全列表")

