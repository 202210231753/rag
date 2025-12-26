"""
重排服务实现

整合重排模型和个性化策略，提供完整的重排能力
"""

from typing import List, Optional, Dict, Any
from loguru import logger

from app.rag.models.candidate import CandidateItem, ScoredItem
from app.rag.rerank.base import IRerankService
from app.rag.rerank.models import BaseRerankModel
from app.rag.rerank.policy import PolicyEngine


class RerankService(IRerankService):
    """
    重排服务实现

    流程：
    1. 使用重排模型计算语义相关性分数
    2. 应用个性化策略和业务规则
    3. 验证排序结果的降序性
    4. 返回最终排序结果
    """

    def __init__(
        self,
        rerank_model: BaseRerankModel,
        policy_engine: Optional[PolicyEngine] = None,
        enable_validation: bool = True,
    ):
        """
        初始化重排服务

        Args:
            rerank_model: 重排模型实例
            policy_engine: 策略引擎（可选）
            enable_validation: 是否启用降序验证
        """
        self.rerank_model = rerank_model
        self.policy_engine = policy_engine or PolicyEngine()
        self.enable_validation = enable_validation

        logger.info(
            f"[RerankService] 初始化: model={rerank_model.model_name}, "
            f"validation={enable_validation}"
        )

    async def predict(
        self,
        query: str,
        candidates: List[CandidateItem],
        user_features: Optional[Dict[str, Any]] = None,
    ) -> List[ScoredItem]:
        """
        对候选文档进行重排

        Args:
            query: 用户查询
            candidates: 候选文档列表
            user_features: 用户画像（可选）

        Returns:
            重排后的文档列表（按 final_score 降序排列）
        """
        if not candidates:
            logger.warning("[RerankService] 候选列表为空，直接返回")
            return []

        try:
            logger.info(
                f"[RerankService] 开始重排: query='{query[:30]}...', "
                f"candidates={len(candidates)}, has_user={user_features is not None}"
            )

            # Step 1: 提取文档内容和元数据
            doc_ids = [c.doc_id for c in candidates]
            documents = [c.content or "" for c in candidates]
            metadata_list = [c.metadata or {} for c in candidates]
            original_scores = [c.score for c in candidates]

            # Step 2: 使用重排模型计算语义分数
            semantic_scores = await self.rerank_model.predict_scores(query, documents)

            # Step 3: 应用个性化策略
            final_scores = self.policy_engine.apply_policies(
                doc_ids, semantic_scores, metadata_list, user_features
            )

            # Step 4: 构建 ScoredItem 列表
            scored_items = [
                ScoredItem(
                    doc_id=doc_id,
                    final_score=final_score,
                    original_score=original_score,
                    rerank_score=semantic_score,
                    content=content,
                    metadata=metadata,
                )
                for doc_id, final_score, original_score, semantic_score, content, metadata in zip(
                    doc_ids,
                    final_scores,
                    original_scores,
                    semantic_scores,
                    documents,
                    metadata_list,
                )
            ]

            # Step 5: 按 final_score 降序排序
            sorted_items = sorted(
                scored_items, key=lambda x: x.final_score, reverse=True
            )

            # Step 6: 验证降序性
            if self.enable_validation:
                self._validate_descending_order(sorted_items)

            logger.info(
                f"[RerankService] 重排完成: results={len(sorted_items)}, "
                f"top_score={sorted_items[0].final_score:.4f}"
            )

            return sorted_items

        except Exception as e:
            logger.error(f"[RerankService] 重排失败: {e}")
            # 降级：返回原始候选列表（转换为 ScoredItem）
            return self._fallback_to_candidates(candidates)

    def _validate_descending_order(self, scored_items: List[ScoredItem]) -> None:
        """
        验证排序结果是否为降序

        Args:
            scored_items: 排序后的结果列表

        Raises:
            ValueError: 如果不是降序排列
        """
        scores = [item.final_score for item in scored_items]

        for i in range(len(scores) - 1):
            if scores[i] < scores[i + 1]:
                error_msg = (
                    f"[RerankService] 排序验证失败: "
                    f"scores[{i}]={scores[i]:.4f} < scores[{i+1}]={scores[i+1]:.4f}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

        logger.debug(
            f"[RerankService] 排序验证通过: {len(scores)} 个结果均为降序"
        )

    def _fallback_to_candidates(
        self, candidates: List[CandidateItem]
    ) -> List[ScoredItem]:
        """
        降级策略：将候选列表转换为 ScoredItem

        Args:
            candidates: 原始候选列表

        Returns:
            转换后的 ScoredItem 列表
        """
        logger.warning("[RerankService] 使用降级策略，返回原始候选列表")
        return [
            ScoredItem(
                doc_id=c.doc_id,
                final_score=c.score,
                original_score=c.score,
                rerank_score=None,
                content=c.content,
                metadata=c.metadata,
            )
            for c in candidates
        ]
