"""
Embedding 向量化服务

封装 OpenAI Embedding API 调用
"""

from typing import List
from openai import AsyncOpenAI
from loguru import logger

from app.core.config import settings


class EmbeddingService:
    """
    OpenAI Embedding 服务

    负责将文本转换为向量表示
    """

    def __init__(self):
        """初始化 OpenAI 客户端"""
        client_params = {"api_key": settings.OPENAI_API_KEY}

        # 如果配置了自定义 API 端点
        if settings.OPENAI_API_BASE:
            client_params["base_url"] = settings.OPENAI_API_BASE
            logger.info(f"使用自定义 OpenAI API 端点: {settings.OPENAI_API_BASE}")

        self.client = AsyncOpenAI(**client_params)
        self.model = settings.OPENAI_EMBEDDING_MODEL
        logger.info(f"Embedding 服务初始化完成，使用模型: {self.model}")

    async def embed(self, text: str) -> List[float]:
        """
        文本向量化

        Args:
            text: 输入文本

        Returns:
            向量表示（1536维，针对 text-embedding-ada-002）
        """
        try:
            logger.debug(f"执行文本向量化: text_length={len(text)}")

            response = await self.client.embeddings.create(
                input=text, model=self.model
            )

            vector = response.data[0].embedding
            logger.info(f"向量化完成: vector_dim={len(vector)}")

            return vector

        except Exception as e:
            logger.error(f"文本向量化失败: {e}")
            raise

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本向量化

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        try:
            logger.debug(f"批量向量化: batch_size={len(texts)}")

            response = await self.client.embeddings.create(
                input=texts, model=self.model
            )

            vectors = [data.embedding for data in response.data]
            logger.info(f"批量向量化完成: count={len(vectors)}")

            return vectors

        except Exception as e:
            logger.error(f"批量向量化失败: {e}")
            raise
