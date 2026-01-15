"""Elasticsearch 客户端初始化。"""
from __future__ import annotations

import os
import logging
from typing import Optional

from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# 全局 ES 客户端（单例）
_es_client: Optional[Elasticsearch] = None


def get_elasticsearch_client() -> Elasticsearch:
    """获取 Elasticsearch 客户端（单例）。"""
    global _es_client

    if _es_client is None:
        es_host = os.getenv("ES_HOST", "localhost")
        es_port = int(os.getenv("ES_PORT", "9200"))
        es_url = f"http://{es_host}:{es_port}"

        _es_client = Elasticsearch(
            [es_url],
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )

        # 测试连接
        try:
            if _es_client.ping():
                logger.info(f"Elasticsearch 连接成功: {es_url}")
            else:
                logger.warning(f"Elasticsearch 连接失败: {es_url}")
        except Exception as e:
            logger.error(f"Elasticsearch 连接异常: {e}")

    return _es_client


















