"""
融合服务接口定义

定义统一的融合服务接口
"""

from abc import ABC, abstractmethod
from typing import List

from app.rag.models.candidate import CandidateItem


class IFusionService(ABC):
    """
    融合服务接口

    负责将多路召回结果融合为单一的排序列表
    """

    @abstractmethod
    def rrf_merge(
        self,
        candidate_lists: List[List[CandidateItem]],
        top_n: int = 50,
        k: int = 60,
    ) -> List[CandidateItem]:
        """
        RRF (Reciprocal Rank Fusion) 融合算法

        公式: score(d) = Σ 1/(k + rank(d))

        Args:
            candidate_lists: 多路召回结果列表
            top_n: 返回最终结果数量
            k: RRF 参数（默认 60）

        Returns:
            融合后的候选列表
        """
        pass
