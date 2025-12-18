"""
向量召回策略

基于 Milvus 向量检索的召回策略
"""

from typing import List
from loguru import logger

from app.rag.strategies.base import IRecallStrategy
from app.rag.models.search_context import SearchContext
from app.rag.models.candidate import CandidateItem
from app.rag.clients.milvus_client import VectorDBClient


class VectorRecallStrategy(IRecallStrategy):
    """
    向量召回策略

    使用查询向量在 Milvus 中进行相似度检索
    """

    def __init__(self, milvus_client: VectorDBClient):
        """
        初始化

        Args:
            milvus_client: Milvus 客户端实例
        """
        self.milvus_client = milvus_client
        logger.info("向量召回策略初始化完成")

    async def recall(
        self, context: SearchContext, top_k: int = 100
    ) -> List[CandidateItem]:
        """
        执行向量召回

        Args:
            context: 搜索上下文
            top_k: 返回结果数量

        Returns:
            候选文档列表
        """
        try:
            logger.info(
                f"[VectorRecall] 开始执行向量召回: query='{context.original_query}', top_k={top_k}"
            )

            # 检查是否有查询向量
            if not context.query_vector:
                logger.warning("搜索上下文中没有查询向量，跳过向量召回")
                return []

            # 调用 Milvus 进行向量检索
            raw_results = await self.milvus_client.search_vector(
                query_vector=context.query_vector, top_k=top_k
            )

            # 转换为 CandidateItem 格式
            candidates = []
            for item in raw_results:
                candidates.append(
                    CandidateItem(
                        doc_id=item["id"],
                        score=1.0 / (1.0 + item["score"]),  # L2距离转相似度分数
                        source="vector",
                        content=item["entity"].get("content"),  # 文档内容
                        metadata=item["entity"],  # 完整实体数据
                    )
                )

            logger.info(f"[VectorRecall] 向量召回完成，返回 {len(candidates)} 条结果")
            return candidates

        except Exception as e:
            logger.error(f"[VectorRecall] 向量召回失败: {e}")
            # 召回失败时返回空列表，不影响其他召回路径
            return []

    @property
    def strategy_name(self) -> str:
        """策略名称"""
        return "vector"
