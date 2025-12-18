"""
召回策略接口定义

定义统一的召回策略接口，所有召回策略必须实现此接口
"""

from abc import ABC, abstractmethod
from typing import List

from app.rag.models.search_context import SearchContext
from app.rag.models.candidate import CandidateItem


class IRecallStrategy(ABC):
    """
    召回策略接口

    所有召回策略（向量召回、关键词召回、混合召回等）的基类
    """

    @abstractmethod
    async def recall(
        self, context: SearchContext, top_k: int = 100
    ) -> List[CandidateItem]:
        """
        执行召回

        Args:
            context: 搜索上下文（包含 query、向量、tokens 等）
            top_k: 返回结果数量

        Returns:
            候选文档列表
        """
        pass

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """
        策略名称

        用于日志记录和监控，例如 "vector" 或 "keyword"
        """
        pass
