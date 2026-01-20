"""
Redis 客户端工具模块

提供统一的 Redis 连接和基础操作封装。
"""

from __future__ import annotations

from typing import List, Optional, Set

try:
    import redis.asyncio as redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore[assignment]

try:
    from loguru import logger  # type: ignore
except Exception:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)

from app.core.config import settings


class RedisClient:
    """Redis 异步客户端封装"""

    def __init__(self):
        self._client: Optional[object] = None

    async def connect(self):
        """建立 Redis 连接"""
        if redis is None:
            logger.warning("未安装 redis 依赖，跳过 Redis 连接初始化")
            self._client = None
            return
        try:
            if settings.REDIS_UNIX_SOCKET:
                self._client = redis.Redis(
                    unix_socket_path=settings.REDIS_UNIX_SOCKET,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD,
                    decode_responses=True,  # 自动解码为字符串
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                )
            else:
                self._client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD,
                    decode_responses=True,  # 自动解码为字符串
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                )
            # 测试连接
            await self._client.ping()
            target = (
                settings.REDIS_UNIX_SOCKET
                if settings.REDIS_UNIX_SOCKET
                else f"{settings.REDIS_HOST}:{settings.REDIS_PORT}"
            )
            logger.info(f"✅ Redis 连接成功: {target}")
        except Exception as e:
            logger.error(f"❌ Redis 连接失败: {e}")
            self._client = None

    async def close(self):
        """关闭 Redis 连接"""
        if self._client:
            await self._client.close()
            logger.info("Redis 连接已关闭")

    @property
    def client(self):
        """获取 Redis 客户端实例"""
        if not self._client:
            raise RuntimeError("Redis 客户端未初始化，请先调用 connect()")
        return self._client

    # ========================================
    # 黑名单操作（Set 类型）
    # ========================================
    async def add_to_blacklist(self, doc_ids: List[str]) -> int:
        """添加文档到黑名单"""
        if not doc_ids:
            return 0
        return await self.client.sadd("blacklist", *doc_ids)

    async def remove_from_blacklist(self, doc_ids: List[str]) -> int:
        """从黑名单移除文档"""
        if not doc_ids:
            return 0
        return await self.client.srem("blacklist", *doc_ids)

    async def is_blacklisted(self, doc_id: str) -> bool:
        """检查文档是否在黑名单"""
        return await self.client.sismember("blacklist", doc_id)

    async def get_blacklist(self) -> Set[str]:
        """获取所有黑名单文档ID"""
        return await self.client.smembers("blacklist")

    # ========================================
    # 位置插入规则（Hash 类型）
    # ========================================
    async def set_position_rule(self, query: str, doc_id: str, position: int):
        """
        设置位置插入规则
        
        Args:
            query: 查询关键词（会转为小写）
            doc_id: 要插入的文档ID
            position: 目标位置（0-based）
        """
        key = f"position_rules:{query.lower()}"
        value = f"{doc_id}:{position}"
        await self.client.set(key, value)
        logger.info(f"✅ 位置规则已设置: query='{query}' -> doc={doc_id} at position {position}")

    async def get_position_rule(self, query: str) -> Optional[tuple[str, int]]:
        """
        获取位置插入规则
        
        Returns:
            (doc_id, position) 或 None
        """
        key = f"position_rules:{query.lower()}"
        value = await self.client.get(key)
        if not value:
            return None

        try:
            doc_id, position = value.split(":")
            return (doc_id, int(position))
        except (ValueError, AttributeError):
            logger.warning(f"位置规则格式错误: {value}")
            return None

    async def delete_position_rule(self, query: str) -> bool:
        """删除位置插入规则"""
        key = f"position_rules:{query.lower()}"
        result = await self.client.delete(key)
        return result > 0

    async def get_all_position_rules(self) -> dict[str, tuple[str, int]]:
        """获取所有位置规则"""
        rules = {}
        cursor = 0
        while True:
            cursor, keys = await self.client.scan(cursor, match="position_rules:*", count=100)
            for key in keys:
                query = key.replace("position_rules:", "")
                rule = await self.get_position_rule(query)
                if rule:
                    rules[query] = rule
            if cursor == 0:
                break
        return rules


# 全局 Redis 客户端实例
redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    """FastAPI 依赖注入"""
    return redis_client
