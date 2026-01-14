"""
项目配置管理模块

使用 Pydantic Settings 自动加载环境变量，支持本地和远程部署。
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类 - 支持本地和远程部署"""

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
    MILVUS_USER: Optional[str] = None  # 远程 Milvus 可能需要认证
    MILVUS_PASSWORD: Optional[str] = None
    MILVUS_SECURE: bool = False  # 是否使用 TLS

    # ========================================
    # ElasticSearch 配置
    # ========================================
    ES_HOST: str = "localhost"
    ES_PORT: int = 9200
    ES_SCHEME: str = "http"  # 远程可用 "https"
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
    # OpenAI API 配置
    # ========================================
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    OPENAI_API_BASE: Optional[str] = None  # 支持自定义 API 端点

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

    # 日志配置
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE: Optional[str] = None  # 日志文件路径（None 表示只输出到控制台）

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置实例（单例模式）

    使用 lru_cache 确保只创建一次配置对象
    """
    return Settings()


# 全局配置对象
settings = get_settings()
