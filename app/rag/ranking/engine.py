"""
排序引擎核心模块

集成黑名单过滤、MMR多样性控制、位置插入规则。
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.core.redis_client import RedisClient
from app.rag.ranking.mmr import mmr_rerank


class RankingEngine:
    """
    排序引擎
    
    执行流程:
        1. 黑名单过滤
        2. MMR多样性控制
        3. 位置插入规则
    """

    def __init__(self, redis_client: RedisClient, db_session: Session):
        self.redis = redis_client
        self.db = db_session
        self._lambda_param: Optional[float] = None  # 内存缓存

    async def get_lambda_param(self) -> float:
        """获取 lambda 参数（带缓存）"""
        if self._lambda_param is not None:
            return self._lambda_param

        # 从数据库读取
        try:
            from sqlalchemy import text
            result = self.db.execute(
                text("SELECT lambda_param FROM diversity_config WHERE id = 1")
            ).fetchone()
            if result:
                self._lambda_param = float(result[0])
            else:
                self._lambda_param = 0.5  # 默认值
        except Exception as e:
            logger.warning(f"读取 lambda 参数失败: {e}，使用默认值 0.5")
            self._lambda_param = 0.5

        return self._lambda_param

    def invalidate_lambda_cache(self):
        """使缓存失效（修改配置时调用）"""
        self._lambda_param = None

    async def apply(
        self,
        query: str,
        items: List,
        top_n: int = 10,
        enable_diversity: bool = True,
        enable_position_rules: bool = True,
    ) -> List:
        """
        应用完整排序流程
        
        Args:
            query: 用户查询
            items: 搜索结果列表（需要有 doc_id, final_score, metadata 属性）
            top_n: 返回前N个结果
            enable_diversity: 是否启用多样性控制
            enable_position_rules: 是否启用位置插入
        
        Returns:
            处理后的搜索结果列表
        """
        if not items:
            return []

        logger.info(f"🔧 排序引擎开始处理: 输入={len(items)}条, query='{query}'")

        # Step 1: 黑名单过滤
        items = await self._filter_blacklist(items)

        # Step 2: MMR 多样性控制
        if enable_diversity:
            items = await self._apply_mmr(items, top_n)
        else:
            items = items[:top_n]

        # Step 3: 位置插入规则
        if enable_position_rules:
            items = await self._apply_position_rules(query, items)

        logger.info(f"✅ 排序引擎完成: 输出={len(items)}条")
        return items

    async def _filter_blacklist(self, items: List) -> List:
        """黑名单过滤"""
        try:
            blacklist = await self.redis.get_blacklist()
            if not blacklist:
                logger.debug("黑名单为空，跳过过滤")
                return items

            original_count = len(items)
            filtered = [
                item for item in items if getattr(item, "doc_id", None) not in blacklist
            ]
            filtered_count = original_count - len(filtered)

            if filtered_count > 0:
                logger.info(f"🚫 黑名单过滤: 移除 {filtered_count} 条")

            return filtered

        except Exception as e:
            logger.error(f"黑名单过滤失败: {e}")
            return items

    async def _apply_mmr(self, items: List, top_n: int) -> List:
        """应用 MMR 多样性控制"""
        try:
            lambda_param = await self.get_lambda_param()
            logger.debug(f"应用 MMR: lambda={lambda_param}, top_n={top_n}")

            return mmr_rerank(items, lambda_param=lambda_param, top_n=top_n)

        except Exception as e:
            logger.error(f"MMR 重排失败: {e}")
            return items[:top_n]

    async def _apply_position_rules(self, query: str, items: List) -> List:
        """应用位置插入规则"""
        try:
            rule = await self.redis.get_position_rule(query)
            if not rule:
                logger.debug(f"查询 '{query}' 无位置规则")
                return items

            target_doc_id, target_position = rule
            logger.info(f"📍 应用位置规则: doc={target_doc_id} -> position {target_position}")

            # 检查目标文档是否在结果中
            target_item = None
            for item in items:
                if getattr(item, "doc_id", None) == target_doc_id:
                    target_item = item
                    items.remove(item)
                    break

            if not target_item:
                logger.warning(f"目标文档 {target_doc_id} 不在结果中，无法插入")
                return items

            # 插入到指定位置
            target_position = min(target_position, len(items))  # 防止越界
            items.insert(target_position, target_item)

            return items

        except Exception as e:
            logger.error(f"位置插入规则失败: {e}")
            return items
