"""学术论文搜索相关的 Schema 定义。"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PaperSearchRequest(BaseModel):
    """论文搜索请求。"""
    
    query: str = Field(..., description="搜索关键词或主题")
    limit: int = Field(default=5, ge=1, le=20, description="返回结果数量限制")
    venue: Optional[str] = Field(default=None, description="会议/期刊名称筛选")
    year_from: Optional[int] = Field(default=None, alias="yearFrom", description="起始年份")
    year_to: Optional[int] = Field(default=None, alias="yearTo", description="结束年份")


class Author(BaseModel):
    """论文作者信息。"""
    
    name: str = Field(..., description="作者姓名")
    author_id: Optional[str] = Field(default=None, alias="authorId", description="作者ID")


class Paper(BaseModel):
    """论文基本信息。"""
    
    paper_id: str = Field(..., alias="paperId", description="论文ID")
    title: str = Field(..., description="论文标题")
    abstract: Optional[str] = Field(default=None, description="摘要")
    authors: List[Author] = Field(default_factory=list, description="作者列表")
    year: Optional[int] = Field(default=None, description="发表年份")
    venue: Optional[str] = Field(default=None, description="发表会议/期刊")
    citation_count: Optional[int] = Field(default=None, alias="citationCount", description="引用数")
    url: Optional[str] = Field(default=None, description="论文链接")
    arxiv_id: Optional[str] = Field(default=None, alias="arxivId", description="arXiv ID")


class PaperSearchResponse(BaseModel):
    """论文搜索响应。"""
    
    query: str = Field(..., description="搜索查询")
    total: int = Field(..., description="结果总数")
    papers: List[Paper] = Field(..., description="论文列表")
    source: str = Field(default="semantic_scholar", description="数据来源")
