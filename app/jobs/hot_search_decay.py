"""
热搜衰减任务（建议由 CronJob 定时触发）

示例（每小时一次）：
  0 * * * *  cd <project> && python -m app.jobs.hot_search_decay
"""

from __future__ import annotations

import asyncio

from loguru import logger

from app.core.redis_client import redis_client
from app.core.config import settings
from app.hot_search.repository import HotSearchRepository, HotSearchKeys
from app.hot_search.service import GovernanceService, HotSearchService


async def run_once() -> None:
    await redis_client.connect()
    try:
        repo = HotSearchRepository(redis_client, keys=HotSearchKeys.with_prefix(settings.HOT_SEARCH_KEY_PREFIX))
        governance = GovernanceService(repo)
        service = HotSearchService(
            repo=repo,
            governance=governance,
            base_increment=1.0,
            base_decay_factor=0.9,
            candidate_multiplier=3,
        )
        executed = await service.decay_once(lock_ttl_seconds=3300)
        logger.info(f"热搜衰减任务执行结果: executed={executed}")
    finally:
        await redis_client.close()


def main() -> None:
    asyncio.run(run_once())


if __name__ == "__main__":
    main()
