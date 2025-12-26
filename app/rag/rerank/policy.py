"""
个性化策略引擎

负责将用户画像融入排序逻辑，提供个性化加权能力
"""

from typing import Dict, Any, List, Optional
from loguru import logger


class PersonalizationPolicy:
    """
    个性化策略

    根据用户画像对排序结果进行个性化调整
    """

    def __init__(
        self,
        interest_boost: float = 0.2,
        history_boost: float = 0.15,
        recency_boost: float = 0.1,
    ):
        """
        初始化个性化策略

        Args:
            interest_boost: 兴趣匹配加权系数
            history_boost: 历史行为加权系数
            recency_boost: 时效性加权系数
        """
        self.interest_boost = interest_boost
        self.history_boost = history_boost
        self.recency_boost = recency_boost

        logger.info(
            f"[PersonalizationPolicy] 初始化: "
            f"interest={interest_boost}, history={history_boost}, recency={recency_boost}"
        )

    def calculate_boost(
        self, doc_metadata: Dict[str, Any], user_features: Dict[str, Any]
    ) -> float:
        """
        计算个性化加权系数

        Args:
            doc_metadata: 文档元数据（包含标签、类别、时间等）
            user_features: 用户画像（包含兴趣、历史行为等）

        Returns:
            加权系数（1.0 表示无加权，>1.0 表示提升）
        """
        boost = 1.0

        # 1. 兴趣匹配加权
        boost += self._interest_match_boost(doc_metadata, user_features)

        # 2. 历史行为加权
        boost += self._history_match_boost(doc_metadata, user_features)

        # 3. 时效性加权
        boost += self._recency_boost(doc_metadata)

        return boost

    def _interest_match_boost(
        self, doc_metadata: Dict[str, Any], user_features: Dict[str, Any]
    ) -> float:
        """
        计算兴趣匹配度加权

        如果文档标签与用户兴趣标签有交集，则提升分数
        """
        doc_tags = set(doc_metadata.get("tags", []))
        user_interests = set(user_features.get("interest", []))

        if not doc_tags or not user_interests:
            return 0.0

        # 计算交集比例
        intersection = doc_tags.intersection(user_interests)
        if intersection:
            match_ratio = len(intersection) / len(user_interests)
            boost = self.interest_boost * match_ratio
            logger.debug(
                f"[PersonalizationPolicy] 兴趣匹配: tags={intersection}, boost={boost:.3f}"
            )
            return boost

        return 0.0

    def _history_match_boost(
        self, doc_metadata: Dict[str, Any], user_features: Dict[str, Any]
    ) -> float:
        """
        计算历史行为加权

        如果文档类别与用户历史点击类别匹配，则提升分数
        """
        doc_category = doc_metadata.get("category")
        user_history = user_features.get("history", [])

        if doc_category and doc_category in user_history:
            logger.debug(
                f"[PersonalizationPolicy] 历史匹配: category={doc_category}, boost={self.history_boost}"
            )
            return self.history_boost

        return 0.0

    def _recency_boost(self, doc_metadata: Dict[str, Any]) -> float:
        """
        计算时效性加权

        如果文档是最近更新的，则提升分数
        """
        from datetime import datetime

        doc_date_str = doc_metadata.get("date")
        if not doc_date_str:
            return 0.0

        try:
            # 假设日期格式为 ISO 8601
            doc_date = datetime.fromisoformat(doc_date_str)
            now = datetime.now()
            days_ago = (now - doc_date).days

            # 7天内的文档加权
            if days_ago <= 7:
                boost = self.recency_boost * (1 - days_ago / 7)
                logger.debug(
                    f"[PersonalizationPolicy] 时效性加权: days_ago={days_ago}, boost={boost:.3f}"
                )
                return boost

        except (ValueError, TypeError) as e:
            logger.debug(f"[PersonalizationPolicy] 解析日期失败: {e}")

        return 0.0


class PolicyEngine:
    """
    策略引擎

    负责应用个性化策略和业务规则
    """

    def __init__(self, personalization_policy: Optional[PersonalizationPolicy] = None):
        """
        初始化策略引擎

        Args:
            personalization_policy: 个性化策略（可选）
        """
        self.personalization_policy = (
            personalization_policy or PersonalizationPolicy()
        )
        logger.info("[PolicyEngine] 初始化完成")

    def apply_policies(
        self,
        doc_ids: List[str],
        semantic_scores: List[float],
        doc_metadata_list: List[Dict[str, Any]],
        user_features: Optional[Dict[str, Any]] = None,
    ) -> List[float]:
        """
        应用个性化策略和业务规则

        Args:
            doc_ids: 文档ID列表
            semantic_scores: 语义相关性分数列表
            doc_metadata_list: 文档元数据列表
            user_features: 用户画像（可选）

        Returns:
            最终分数列表
        """
        final_scores = []

        for i, (doc_id, semantic_score, metadata) in enumerate(
            zip(doc_ids, semantic_scores, doc_metadata_list)
        ):
            # 基础分数 = 语义分数
            score = semantic_score

            # 如果有用户画像，应用个性化加权
            if user_features:
                boost = self.personalization_policy.calculate_boost(
                    metadata, user_features
                )
                score = semantic_score * boost

            # 业务规则：置顶特定来源
            if metadata.get("source") == "official":
                score += 0.1
                logger.debug(
                    f"[PolicyEngine] 官方来源加权: doc_id={doc_id}, boost=+0.1"
                )

            final_scores.append(score)

        return final_scores
