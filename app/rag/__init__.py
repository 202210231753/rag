"""
RAG 模块 - 多路召回检索引擎

实现基于向量召回 + 关键词召回的多路召回系统,使用 RRF 融合算法
"""

# 数据模型
from app.rag.models import (
    SearchContext,
    CandidateItem,
    ScoredItem,
    SearchResult,
    SearchResultItem,
)

# 基础设施客户端
from app.rag.clients import VectorDBClient, SearchEngineClient

# 召回策略
from app.rag.strategies import (
    IRecallStrategy,
    VectorRecallStrategy,
    KeywordRecallStrategy,
)

# 融合服务
from app.rag.fusion import IFusionService, RRFMergeImpl

# 重排服务（预留）
from app.rag.rerank import IRerankService

# 搜索网关（核心编排器）
from app.rag.search_gateway import SearchGateway

__all__ = [
    # 数据模型
    "SearchContext",
    "CandidateItem",
    "ScoredItem",
    "SearchResult",
    "SearchResultItem",
    # 客户端
    "VectorDBClient",
    "SearchEngineClient",
    # 召回策略
    "IRecallStrategy",
    "VectorRecallStrategy",
    "KeywordRecallStrategy",
    # 融合服务
    "IFusionService",
    "RRFMergeImpl",
    # 重排服务
    "IRerankService",
    # 核心网关
    "SearchGateway",
]
