"""
热搜服务 API Schema

定义热搜榜单、治理规则（屏蔽/置顶/加权）相关请求与响应模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TrendingItem(BaseModel):
    """热搜榜单项"""

    rank: int = Field(..., ge=1, description="排名（1-based）")
    keyword: str = Field(..., min_length=1, description="搜索词（已规范化）")
    heat_score: float = Field(..., ge=0, description="热度分")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展信息")


class TrendingListResponse(BaseModel):
    """热搜榜单响应"""

    limit: int = Field(..., ge=1, description="返回条数")
    generated_at: datetime = Field(..., description="生成时间（UTC）")
    items: list[TrendingItem] = Field(default_factory=list, description="榜单列表")


class BlockedWordsRequest(BaseModel):
    action: str = Field(..., description="操作类型: add/remove")
    words: list[str] = Field(default_factory=list, description="词列表")


class BlockedWordsResponse(BaseModel):
    action: str
    affected_count: int
    total_count: int


class PinWordRequest(BaseModel):
    keyword: str = Field(..., min_length=1, description="置顶词（将被规范化）")


class PinWordResponse(BaseModel):
    rank: int = Field(..., ge=1)
    keyword: str


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class BoostUpsertRequest(BaseModel):
    search_boost: Optional[float] = Field(
        default=None, gt=0, description="搜索增量倍率（>0）"
    )
    decay_factor: Optional[float] = Field(
        default=None, gt=0, le=1, description="衰减系数（(0,1]；1=豁免衰减）"
    )


class BoostEntry(BaseModel):
    keyword: str
    search_boost: Optional[float] = None
    decay_factor: Optional[float] = None


class BoostResponse(BaseModel):
    keyword: str
    search_boost: Optional[float] = None
    decay_factor: Optional[float] = None

