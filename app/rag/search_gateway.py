"""
搜索网关 - 多路召回系统核心入口

协调向量化、分词、并行召回、融合和重排的完整流程
"""

import asyncio
import time
from typing import List, Optional
from loguru import logger

from app.rag.models.search_context import SearchContext
from app.rag.models.candidate import CandidateItem
from app.rag.models.search_result import SearchResult, SearchResultItem
from app.rag.strategies.base import IRecallStrategy
from app.rag.fusion.base import IFusionService
from app.rag.rerank.base import IRerankService
from app.services.embedding_service import EmbeddingService
from app.services.tokenizer_service import TokenizerService
from app.rag.ranking.engine import RankingEngine


class SearchGateway:
    """
    搜索网关

    多路召回系统的主入口，负责：
    1. 创建搜索上下文（向量化、分词）
    2. 并行执行多路召回
    3. RRF 融合
    4. 重排（可选）
    5. 构建返回结果
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        tokenizer_service: TokenizerService,
        recall_strategies: List[IRecallStrategy],
        fusion_service: IFusionService,
        rerank_service: Optional[IRerankService] = None,
        ranking_engine: Optional[RankingEngine] = None,
    ):
        """
        初始化搜索网关

        Args:
            embedding_service: 向量化服务
            tokenizer_service: 分词服务
            recall_strategies: 召回策略列表（向量、关键词等）
            fusion_service: 融合服务
            rerank_service: 重排服务（可选）
            ranking_engine: 排序引擎（可选）
        """
        self.embedding_service = embedding_service
        self.tokenizer_service = tokenizer_service
        self.recall_strategies = recall_strategies
        self.fusion_service = fusion_service
        self.rerank_service = rerank_service
        self.ranking_engine = ranking_engine

        logger.info(
            f"SearchGateway 初始化完成: recall_strategies={len(recall_strategies)}, "
            f"rerank={'enabled' if rerank_service else 'disabled'}, "
            f"ranking={'enabled' if ranking_engine else 'disabled'}"
        )

    async def search(
        self,
        query: str,
        top_n: int = 10,
        recall_top_k: int = 100,
        enable_rerank: bool = False,
        enable_ranking: bool = True,
    ) -> SearchResult:
        """
        执行多路召回搜索

        流程:
        1. 创建 SearchContext（向量化 + 分词）
        2. 并行召回（多个策略并发执行）
        3. RRF 融合
        4. 重排（可选）
        5. 排序引擎（可选）
        6. 返回结果

        Args:
            query: 用户查询
            top_n: 返回结果数量
            recall_top_k: 每路召回的 TopK
            enable_rerank: 是否启用重排
            enable_ranking: 是否启用排序引擎

        Returns:
            搜索结果
        """
        start_time = time.time()

        try:
            logger.info(
                f"[SearchGateway] 开始搜索: query='{query}', top_n={top_n}, "
                f"recall_top_k={recall_top_k}, enable_rerank={enable_rerank}, "
                f"enable_ranking={enable_ranking}"
            )

            # Step 1: 创建搜索上下文
            context = await self._create_search_context(query)

            # Step 2: 并行召回
            candidate_lists = await self._parallel_recall(context, recall_top_k)

            # Step 3: RRF 融合
            merged_candidates = self.fusion_service.rrf_merge(
                candidate_lists,
                top_n=top_n if not enable_rerank else top_n * 2,  # 重排时多召回一些
            )

            # Step 4: 重排（可选）
            if enable_rerank and self.rerank_service:
                logger.info("[SearchGateway] 执行重排...")
                scored_items = await self.rerank_service.predict(
                    query, merged_candidates
                )
                final_results = sorted(
                    scored_items, key=lambda x: x.final_score, reverse=True
                )[:top_n]
            else:
                final_results = merged_candidates[:top_n]

            # Step 5: 排序引擎（可选）
            if enable_ranking and self.ranking_engine:
                logger.info("[SearchGateway] 应用排序引擎...")
                final_results = await self.ranking_engine.apply(
                    query=query,
                    items=final_results,
                    top_n=top_n,
                )

            # Step 6: 构建响应
            took_ms = (time.time() - start_time) * 1000
            result = self._build_search_result(
                query, final_results, candidate_lists, took_ms
            )

            logger.info(
                f"[SearchGateway] 搜索完成: results={len(result.results)}, took={took_ms:.2f}ms"
            )
            return result

        except Exception as e:
            logger.error(f"[SearchGateway] 搜索失败: {e}")
            raise

    async def _create_search_context(self, query: str) -> SearchContext:
        """
        创建搜索上下文

        并行执行向量化和分词，提高效率

        Args:
            query: 用户查询

        Returns:
            搜索上下文
        """
        try:
            logger.info("[SearchGateway] 创建搜索上下文...")

            # 并行执行向量化和分词
            vector, tokens = await asyncio.gather(
                self.embedding_service.embed(query),
                self.tokenizer_service.analyze(query),
            )

            context = SearchContext(
                original_query=query, query_vector=vector, tokens=tokens
            )

            logger.info(
                f"[SearchGateway] 搜索上下文创建完成: vector_dim={len(vector)}, token_count={len(tokens)}"
            )
            return context

        except Exception as e:
            logger.error(f"[SearchGateway] 创建搜索上下文失败: {e}")
            raise

    async def _parallel_recall(
        self, context: SearchContext, top_k: int
    ) -> List[List[CandidateItem]]:
        """
        并行执行多路召回

        Args:
            context: 搜索上下文
            top_k: 每路召回的 TopK

        Returns:
            各路召回结果列表
        """
        try:
            logger.info(
                f"[SearchGateway] 开始并行召回: strategies={len(self.recall_strategies)}, top_k={top_k}"
            )

            # 并发执行所有召回策略
            tasks = [strategy.recall(context, top_k) for strategy in self.recall_strategies]
            candidate_lists = await asyncio.gather(*tasks)

            # 统计各路召回数量
            recall_stats = {
                self.recall_strategies[i].strategy_name: len(candidate_lists[i])
                for i in range(len(self.recall_strategies))
            }
            logger.info(f"[SearchGateway] 并行召回完成: {recall_stats}")

            return candidate_lists

        except Exception as e:
            logger.error(f"[SearchGateway] 并行召回失败: {e}")
            raise

    def _build_search_result(
        self,
        query: str,
        final_results: List[CandidateItem],
        candidate_lists: List[List[CandidateItem]],
        took_ms: float,
    ) -> SearchResult:
        """
        构建搜索结果响应

        Args:
            query: 原始查询
            final_results: 最终结果列表
            candidate_lists: 各路召回结果（用于统计）
            took_ms: 耗时（毫秒）

        Returns:
            搜索结果
        """
        # 转换为 SearchResultItem
        result_items = [
            SearchResultItem(
                doc_id=item.doc_id,
                score=item.score,
                content=item.content,
                metadata=item.metadata,
            )
            for item in final_results
        ]

        # 统计各路召回数量
        recall_stats = {
            self.recall_strategies[i].strategy_name: len(candidate_lists[i])
            for i in range(len(self.recall_strategies))
        }
        recall_stats["merged"] = len(final_results)

        return SearchResult(
            query=query,
            results=result_items,
            total=len(result_items),
            took_ms=took_ms,
            recall_stats=recall_stats,
        )
