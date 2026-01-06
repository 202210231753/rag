# 【入口】整个程序的启动点
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理（启动和关闭）。"""
    # 启动时执行
    _init_on_startup()
    
    yield
    
    # 关闭时执行（如果需要）
    # _cleanup_on_shutdown()


def _init_on_startup():
    """应用启动时执行初始化。"""
    # 检查是否启用自动初始化（可通过环境变量控制）
    auto_init = os.getenv("SYNONYM_AUTO_INIT", "true").lower() == "true"
    
    if not auto_init:
        logger.info("同义词自动初始化已禁用（SYNONYM_AUTO_INIT=false）")
        return
    
    # 初始化默认同义词数据（如果数据库为空）
    try:
        from app.services.synonym_service import init_synonyms_on_startup
        
        db = SessionLocal()
        try:
            init_synonyms_on_startup(db, domain="default")
        finally:
            db.close()
    except Exception as e:
        # 记录警告但不影响应用启动
        logger.warning(
            f"启动时初始化同义词数据失败（可忽略）: {e}",
            exc_info=logger.isEnabledFor(logging.DEBUG)
        )


app = FastAPI(
    title="RAG Knowledge System",
    description="后端 API 接口文档",
    version="1.0.0",
    lifespan=lifespan,  # 使用 lifespan 替代已废弃的 on_event
)

# 注册所有路由，统一加前缀 /api/v1
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "RAG System is running!"}