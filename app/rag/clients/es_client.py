"""
ElasticSearch 搜索引擎客户端

封装 ElasticSearch BM25 关键词检索操作，支持本地和远程部署
"""

from typing import List, Dict, Any
from elasticsearch import AsyncElasticsearch
from loguru import logger

from app.core.config import settings


class SearchEngineClient:
    """
    ElasticSearch 客户端

    负责 BM25 关键词检索，自动适配本地/远程ES部署
    """

    def __init__(self):
        """初始化 ES 客户端"""
        self.client = None
        self._create_client()

    def _create_client(self):
        """
        创建 ES 客户端连接

        根据配置自动适配本地/远程部署，支持 HTTPS 和基础认证
        """
        try:
            # 构建连接配置
            es_config = {
                "hosts": [
                    f"{settings.ES_SCHEME}://{settings.ES_HOST}:{settings.ES_PORT}"
                ]
            }

            # 如果配置了认证
            if settings.ES_USERNAME and settings.ES_PASSWORD:
                es_config["basic_auth"] = (
                    settings.ES_USERNAME,
                    settings.ES_PASSWORD,
                )
                logger.info(f"连接 ES 使用认证: user={settings.ES_USERNAME}")

            # 如果是 HTTPS
            if settings.ES_SCHEME == "https":
                es_config["verify_certs"] = True  # 生产环境建议开启证书验证
                logger.info("连接 ES 启用 HTTPS")

            self.client = AsyncElasticsearch(**es_config)
            logger.info(
                f"成功创建 ES 客户端: {settings.ES_SCHEME}://{settings.ES_HOST}:{settings.ES_PORT}"
            )

        except Exception as e:
            logger.error(f"创建 ES 客户端失败: {e}")
            raise

    async def search_bm25(
        self, tokens: List[str], top_k: int = 100, index_name: str = None
    ) -> List[Dict[str, Any]]:
        """
        BM25 关键词检索

        Args:
            tokens: 分词后的 token 列表
            top_k: 返回结果数量
            index_name: 索引名称（默认使用配置中的索引）

        Returns:
            检索结果列表，格式: [{"id": "doc_001", "score": 15.3, "source": {...}}, ...]
        """
        try:
            if index_name is None:
                index_name = settings.ES_INDEX_NAME

            # 构建查询
            query_text = " ".join(tokens)
            logger.debug(f"执行 BM25 检索: query='{query_text}', top_k={top_k}")

            query_body = {
                "query": {
                    "match": {
                        "content": {  # 假设文档内容字段为 "content"
                            "query": query_text,
                            "operator": "or",  # 或逻辑（任意token匹配即可）
                        }
                    }
                },
                "size": top_k,
            }

            # 执行搜索
            response = await self.client.search(index=index_name, body=query_body)

            # 解析结果
            items = []
            for hit in response["hits"]["hits"]:
                items.append(
                    {
                        "id": hit["_id"],
                        "score": float(hit["_score"]),  # BM25 分数
                        "source": hit["_source"],  # 文档原始数据
                    }
                )

            logger.info(f"BM25 检索完成，返回 {len(items)} 条结果")
            return items

        except Exception as e:
            logger.error(f"BM25 检索失败: {e}")
            raise

    async def create_index_if_not_exists(self, index_name: str = None):
        """
        创建索引（如果不存在）

        Args:
            index_name: 索引名称
        """
        if index_name is None:
            index_name = settings.ES_INDEX_NAME

        try:
            exists = await self.client.indices.exists(index=index_name)
            if not exists:
                # 定义索引 mapping
                mapping = {
                    "mappings": {
                        "properties": {
                            "content": {"type": "text", "analyzer": "standard"},
                            "doc_id": {"type": "keyword"},
                            "metadata": {"type": "object"},
                        }
                    }
                }

                await self.client.indices.create(index=index_name, body=mapping)
                logger.info(f"成功创建 ES 索引: {index_name}")
            else:
                logger.debug(f"ES 索引已存在: {index_name}")

        except Exception as e:
            logger.error(f"创建 ES 索引失败: {e}")
            raise

    async def close(self):
        """关闭连接"""
        try:
            if self.client:
                await self.client.close()
                logger.info("ES 连接已关闭")
        except Exception as e:
            logger.warning(f"关闭 ES 连接时出错: {e}")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
