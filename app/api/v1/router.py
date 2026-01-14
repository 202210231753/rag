# 路由汇总（把下面两个拼起来）
from fastapi import APIRouter
from app.api.v1.endpoints import synonym, synonym_mining
# from app.api.v1.endpoints import viewer, chat  # 暂时注释，模块未完成
# from app.api.v1.endpoints import search  # 暂时注释，避免elasticsearch依赖

api_router = APIRouter()

# 挂载你的模块 (访问地址: /api/v1/viewer/...)
# api_router.include_router(viewer.router, prefix="/viewer", tags=["数据查看模块"])  # 暂时注释，模块未完成

# 挂载同义词模块 (访问地址: /api/v1/synonyms/...)
# 包含：同义词管理、查询改写、候选审核
api_router.include_router(synonym.router, prefix="/synonyms", tags=["同义词模块"])

# 挂载挖掘模块 (访问地址: /api/v1/synonyms/mining/...)
api_router.include_router(synonym_mining.router, prefix="/synonyms/mining", tags=["同义词挖掘模块"])

# 挂载检索模块 (访问地址: /api/v1/search/...)
# api_router.include_router(search.router, prefix="/search", tags=["检索模块"])  # 暂时注释

# # 挂载同事的模块 (访问地址: /api/v1/chat/...)
# api_router.include_router(chat.router, prefix="/chat", tags=["RAG对话模块"])