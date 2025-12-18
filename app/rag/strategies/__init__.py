"""
召回策略模块

定义召回策略接口和具体实现（向量召回、关键词召回等）
"""

from app.rag.strategies.base import IRecallStrategy
from app.rag.strategies.vector_strategy import VectorRecallStrategy
from app.rag.strategies.keyword_strategy import KeywordRecallStrategy

__all__ = ["IRecallStrategy", "VectorRecallStrategy", "KeywordRecallStrategy"]
