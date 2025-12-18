"""
Milvus 向量数据库客户端

封装 Milvus 向量检索操作，支持本地和远程部署
"""

from typing import List, Dict, Any
from pymilvus import connections, Collection
from loguru import logger

from app.core.config import settings


class VectorDBClient:
    """
    Milvus 向量数据库客户端

    负责向量检索操作，自动适配本地/远程Milvus部署
    """

    def __init__(
        self, collection_name: str = "documents", connect_alias: str = "default"
    ):
        """
        初始化 Milvus 客户端

        Args:
            collection_name: 集合名称
            connect_alias: 连接别名
        """
        self.collection_name = collection_name
        self.connect_alias = connect_alias
        self.collection = None
        self._connect()

    def _connect(self):
        """
        连接到 Milvus

        根据配置自动适配本地/远程部署，支持认证和TLS
        """
        try:
            # 构建连接参数
            connect_params = {
                "alias": self.connect_alias,
                "host": settings.MILVUS_HOST,
                "port": str(settings.MILVUS_PORT),
            }

            # 如果配置了认证信息
            if settings.MILVUS_USER and settings.MILVUS_PASSWORD:
                connect_params["user"] = settings.MILVUS_USER
                connect_params["password"] = settings.MILVUS_PASSWORD
                logger.info(
                    f"连接 Milvus 使用认证: user={settings.MILVUS_USER}"
                )

            # 如果启用 TLS
            if settings.MILVUS_SECURE:
                connect_params["secure"] = True
                logger.info("连接 Milvus 启用 TLS 加密")

            # 连接
            connections.connect(**connect_params)
            logger.info(
                f"成功连接到 Milvus: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}"
            )

            # 加载集合
            self.collection = Collection(self.collection_name)
            self.collection.load()
            logger.info(f"成功加载 Milvus 集合: {self.collection_name}")

        except Exception as e:
            logger.error(f"连接 Milvus 失败: {e}")
            raise

    async def search_vector(
        self, query_vector: List[float], top_k: int = 100
    ) -> List[Dict[str, Any]]:
        """
        向量检索

        Args:
            query_vector: 查询向量
            top_k: 返回结果数量

        Returns:
            检索结果列表，格式: [{"id": "doc_001", "score": 0.95, "entity": {...}}, ...]
        """
        try:
            logger.debug(
                f"执行向量检索: vector_dim={len(query_vector)}, top_k={top_k}"
            )

            # Milvus 搜索
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

            results = self.collection.search(
                data=[query_vector],
                anns_field="embedding",  # 向量字段名，根据实际情况调整
                param=search_params,
                limit=top_k,
                output_fields=["*"],  # 返回所有字段
            )

            # 解析结果
            items = []
            for hit in results[0]:
                items.append(
                    {
                        "id": str(hit.id),
                        "score": float(hit.distance),  # L2 距离，越小越相似
                        "entity": hit.entity,  # 实体数据
                    }
                )

            logger.info(f"向量检索完成，返回 {len(items)} 条结果")
            return items

        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            raise

    def close(self):
        """关闭连接"""
        try:
            connections.disconnect(self.connect_alias)
            logger.info("Milvus 连接已关闭")
        except Exception as e:
            logger.warning(f"关闭 Milvus 连接时出错: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
