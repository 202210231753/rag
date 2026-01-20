# 【入口】整个程序的启动点
from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html

try:
    from loguru import logger  # type: ignore
except Exception:  # pragma: no cover
    logger = logging.getLogger(__name__)

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.redis_client import redis_client


# ========================================
# Loguru 日志配置
# ========================================
def setup_logger():
    """配置日志系统（优先 loguru，缺失时回退标准 logging）。"""
    if not hasattr(logger, "remove"):
        logging.basicConfig(
            level=getattr(logging, str(settings.LOG_LEVEL).upper(), logging.INFO),
            stream=sys.stdout,
            format="%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        )
        logger.info("标准 logging 初始化完成")
        return

    # loguru 路径
    # 移除默认的 handler
    logger.remove()

    # 添加控制台输出（彩色）
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # 如果配置了日志文件，添加文件输出
    if settings.LOG_FILE:
        logger.add(
            settings.LOG_FILE,
            rotation="100 MB",  # 日志文件达到 100MB 时轮转
            retention="10 days",  # 保留最近 10 天的日志
            compression="zip",  # 压缩旧日志
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=settings.LOG_LEVEL,
        )

    logger.info("Loguru 日志系统初始化完成")


# 初始化日志
setup_logger()


# ========================================
# FastAPI 应用配置
# ========================================
app = FastAPI(
    title="RAG Knowledge System - 多路召回搜索",
    description="基于向量检索 + 关键词检索的多路召回系统，使用 RRF 融合算法",
    version="2.0.0",
    docs_url="/docs",
    # 默认 ReDoc 可能引用外部资源导致部分网络环境下空白；这里关闭内置 redoc_url，改用自定义路由。
    redoc_url=None,
)

# 注册所有路由，统一加前缀 /api/v1
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("=" * 60)
    logger.info("RAG 多路召回系统正在启动...")
    logger.info(f"调试模式: {settings.DEBUG}")
    logger.info(f"日志级别: {settings.LOG_LEVEL}")
    logger.info("=" * 60)
    
    # 初始化 Redis 连接
    await redis_client.connect()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("RAG 多路召回系统正在关闭...")
    
    # 关闭 Redis 连接
    await redis_client.close()


@app.get("/redoc", include_in_schema=False)
def redoc() -> object:
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://unpkg.com/redoc@3.0.0-rc.0/bundles/redoc.standalone.js",
    )


@app.get("/")
def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "message": "RAG Multi-Recall System is running!",
        "version": "2.0.0",
    }
