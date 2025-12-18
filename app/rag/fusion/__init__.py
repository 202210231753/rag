"""
融合服务模块

实现 RRF (Reciprocal Rank Fusion) 等多路召回结果融合算法
"""

from app.rag.fusion.base import IFusionService
from app.rag.fusion.rrf_fusion import RRFMergeImpl

__all__ = ["IFusionService", "RRFMergeImpl"]
