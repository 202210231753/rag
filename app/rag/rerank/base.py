"""
重排服务接口定义（预留）

定义重排服务接口，暂不实现，预留给未来扩展
"""

from abc import ABC, abstractmethod
from typing import List

from app.rag.models.candidate import CandidateItem, ScoredItem


class IRerankService(ABC):
    """
    重排服务接口

    负责对融合后的候选结果进行精排（使用重排模型）

    注意：当前为预留接口，暂无具体实现
    """

    @abstractmethod
    async def predict(
        self, query: str, candidates: List[CandidateItem]
    ) -> List[ScoredItem]:
        """
        使用重排模型对候选结果打分

        Args:
            query: 用户查询
            candidates: 候选文档列表

        Returns:
            带有重排分数的结果列表
        """
        pass
