# 服务模块 - 扁平结构
from .recommender_service import ContentRecommenderService, QueryRecommenderService
from .feedback_service import FeedbackService
from .viewer_service import ViewerService

__all__ = [
    'ContentRecommenderService',
    'QueryRecommenderService',
    'FeedbackService',
    'ViewerService'
]
