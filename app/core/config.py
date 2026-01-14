"""
项目配置管理模块

统一管理环境变量（`.env`），兼容：
- 原有 RAG/排序/检索相关配置
- zsl-intervention 引入的摄入、MinIO、MinerU、Embedding 本地模型等配置
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    # ========================================
    # MySQL 数据库配置
    # ========================================
    DB_SERVER: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "rag_user"
    DB_PASSWORD: str = "rag_password"
    DB_NAME: str = "rag_data"
    DB_ROOT_PASSWORD: Optional[str] = None

    # ========================================
    # Milvus 向量数据库配置
    # ========================================
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_USER: Optional[str] = None
    MILVUS_PASSWORD: Optional[str] = None
    MILVUS_SECURE: bool = False

    # ========================================
    # MinIO 对象存储（文件上传/下载）
    # ========================================
    MINIO_ENDPOINT: str = "localhost:19000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "rag-documents"
    MINIO_SECURE: bool = False

    # ========================================
    # MinerU（文件解析服务）
    # ========================================
    MINERU_API_URL: str = "http://127.0.0.1:18000/file_parse"

    # ========================================
    # 本地模型/服务（zsl 摄入链路）
    # ========================================
    EMBEDDING_MODEL_PATH: str = ""
    LLM_MODEL_API: str = "http://localhost:8000/v1"

    # ========================================
    # ElasticSearch 配置
    # ========================================
    ES_HOST: str = "localhost"
    ES_PORT: int = 9200
    ES_SCHEME: str = "http"
    ES_USERNAME: Optional[str] = None
    ES_PASSWORD: Optional[str] = None
    ES_INDEX_NAME: str = "rag_documents"

    # ========================================
    # Redis 配置
    # ========================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # ========================================
    # OpenAI API 配置（可选）
    # ========================================
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    OPENAI_API_BASE: Optional[str] = None

    # ========================================
    # RAG 配置
    # ========================================
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 5

    # ========================================
    # 应用配置
    # ========================================
    APP_PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
