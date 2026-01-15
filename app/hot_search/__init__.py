"""
热搜服务模块

提供热度计数、榜单生成、治理规则（屏蔽/置顶/加权）与衰减任务的核心实现。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.hot_search.decay_scheduler import DecayScheduler
    from app.hot_search.repository import HotSearchRepository
    from app.hot_search.service import GovernanceService, HotSearchService

__all__ = [
    "DecayScheduler",
    "GovernanceService",
    "HotSearchRepository",
    "HotSearchService",
]
