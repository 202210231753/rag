# 路由汇总
from fastapi import APIRouter

from app.api.v1.endpoints import (
    files,
    ingest,
    intervention,
    knowledge,
    ranking,
    search,
    term_weight,
    tokenizer,
    viewer,
)

api_router = APIRouter()

# 知识库/文件/摄入/干预
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库管理模块"])
api_router.include_router(intervention.router, prefix="/intervention", tags=["数据干预模块"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["数据摄入模块"])
api_router.include_router(files.router, prefix="/files", tags=["文件代理模块"])

# 原有模块
api_router.include_router(viewer.router, prefix="/viewer", tags=["数据查看模块"])
api_router.include_router(tokenizer.router, prefix="/tokenizer", tags=["中文分词模块"])
api_router.include_router(term_weight.router, prefix="/term-weight", tags=["词权重模块"])
api_router.include_router(search.router, prefix="/search", tags=["多路召回搜索"])
api_router.include_router(ranking.router, prefix="/ranking", tags=["排序引擎管理"])
