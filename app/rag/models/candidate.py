"""
候选文档数据模型

定义召回阶段和重排阶段的文档表示
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class CandidateItem:
    """
    召回候选文档

    表示从某一召回策略（向量或关键词）返回的文档项
    """

    doc_id: str  # 文档ID（对应 Milvus/ES 中的ID）
    score: float  # 原始召回分数（相似度或BM25分数）
    source: str  # 召回来源标识（"vector" 或 "keyword"）
    content: Optional[str] = None  # 文档内容片段（可选）
    metadata: Optional[Dict[str, Any]] = None  # 额外元数据

    def __hash__(self):
        """
        用于去重

        当多路召回返回相同文档时，可以使用 set() 去重
        """
        return hash(self.doc_id)

    def __eq__(self, other):
        """相等性判断：仅比较 doc_id"""
        if not isinstance(other, CandidateItem):
            return False
        return self.doc_id == other.doc_id


@dataclass
class ScoredItem:
    """
    重排后的文档

    经过重排模型打分后的最终结果
    """

    doc_id: str
    final_score: float  # 重排后的最终分数
    original_score: float  # 原始召回分数（用于对比）
    rerank_score: Optional[float] = None  # 重排模型分数（可选）
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "doc_id": self.doc_id,
            "final_score": self.final_score,
            "original_score": self.original_score,
            "rerank_score": self.rerank_score,
            "content": self.content,
            "metadata": self.metadata,
        }
