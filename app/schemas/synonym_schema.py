"""同义词相关 Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SynonymTermSchema(BaseModel):
    """同义词项 Schema。"""

    term: str = Field(..., description="同义词")
    weight: float = Field(default=1.0, description="权重")

    model_config = ConfigDict(populate_by_name=True)


class SynonymGroupSchema(BaseModel):
    """同义词组 Schema。"""

    group_id: Optional[int] = Field(default=None, alias="groupId")
    domain: str = Field(default="default", description="领域")
    canonical: str = Field(..., description="标准词")
    enabled: int = Field(default=1, description="是否启用：1启用，0禁用")
    terms: List[SynonymTermSchema] = Field(default_factory=list, description="同义词列表")
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class SynonymCandidateSchema(BaseModel):
    """同义词候选 Schema。"""

    candidate_id: Optional[int] = Field(default=None, alias="candidateId")
    domain: str = Field(default="default", description="领域")
    canonical: str = Field(..., description="标准词")
    synonym: str = Field(..., description="候选同义词")
    score: float = Field(..., description="相似度分数")
    status: str = Field(default="pending", description="状态：pending/approved/rejected")
    source: str = Field(default="embedding", description="来源")
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


# ========== API 请求/响应 Schema ==========


class ManualUpsertRequest(BaseModel):
    """手动添加同义词请求。"""

    domain: str = Field(default="default", description="领域")
    canonical: str = Field(..., description="标准词")
    synonyms: List[str] = Field(..., description="同义词列表")

    model_config = ConfigDict(populate_by_name=True)


class BatchImportRequest(BaseModel):
    """批量导入请求。"""

    domain: str = Field(default="default", description="领域")
    groups: List[dict] = Field(..., description="同义词组列表，每个元素包含 canonical 和 synonyms")

    model_config = ConfigDict(populate_by_name=True)


class DeleteGroupsRequest(BaseModel):
    """删除同义词组请求。"""

    group_ids: List[int] = Field(..., alias="groupIds", description="同义词组ID列表")

    model_config = ConfigDict(populate_by_name=True)


class CandidateListResponse(BaseModel):
    """候选列表响应。"""

    candidates: List[SynonymCandidateSchema] = Field(default_factory=list)
    total: int = Field(default=0)

    model_config = ConfigDict(populate_by_name=True)


class ApproveRejectRequest(BaseModel):
    """审核请求。"""

    ids: List[int] = Field(..., description="候选ID列表")

    model_config = ConfigDict(populate_by_name=True)


class RewriteRequest(BaseModel):
    """查询改写请求。"""

    domain: str = Field(default="default", description="领域")
    query: str = Field(..., description="原始查询")

    model_config = ConfigDict(populate_by_name=True)


class RewritePlan(BaseModel):
    """查询改写计划。"""

    original_query: str = Field(..., alias="originalQuery", description="原始查询")
    expanded_terms: List[str] = Field(default_factory=list, alias="expandedTerms", description="扩展词列表")
    debug: dict = Field(default_factory=dict, description="调试信息")

    model_config = ConfigDict(populate_by_name=True)


















