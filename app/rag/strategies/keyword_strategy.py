"""
关键词召回策略

基于 ElasticSearch BM25 的关键词召回策略
"""

from typing import List
from loguru import logger

from app.rag.strategies.base import IRecallStrategy
from app.rag.models.search_context import SearchContext
from app.rag.models.candidate import CandidateItem
from app.rag.clients.es_client import SearchEngineClient


class KeywordRecallStrategy(IRecallStrategy):
    """
    关键词召回策略

    使用分词结果在 ElasticSearch 中进行 BM25 检索
    """

    def __init__(self, es_client: SearchEngineClient):
        """
        初始化

        Args:
            es_client: ES 客户端实例
        """
        self.es_client = es_client
        logger.info("关键词召回策略初始化完成")

    async def recall(
        self, context: SearchContext, top_k: int = 100
    ) -> List[CandidateItem]:
        """
        执行关键词召回

        Args:
            context: 搜索上下文
            top_k: 返回结果数量

        Returns:
            候选文档列表
        """
        try:
            logger.info(
                f"[KeywordRecall] 开始执行关键词召回: query='{context.original_query}', top_k={top_k}"
            )

            # 检查是否有分词结果
            if not context.tokens:
                logger.warning("搜索上下文中没有分词结果，跳过关键词召回")
                return []

            # 调用 ES 进行 BM25 检索
            raw_results = await self.es_client.search_bm25(
                tokens=context.tokens, top_k=top_k
            )

            # 转换为 CandidateItem 格式
            candidates = []
            for item in raw_results:
                candidates.append(
                    CandidateItem(
                        doc_id=item["id"],
                        score=float(item["score"]),  # BM25 分数
                        source="keyword",
                        content=item["source"].get("content"),  # 文档内容
                        metadata=item["source"],  # 完整 source 数据
                    )
                )

            logger.info(
                f"[KeywordRecall] 关键词召回完成，返回 {len(candidates)} 条结果"
            )
            return candidates

        except Exception as e:
            logger.error(f"[KeywordRecall] 关键词召回失败: {e}")
            # 召回失败时返回空列表，不影响其他召回路径
            return []

    @property
    def strategy_name(self) -> str:
        """策略名称"""
        return "keyword"
