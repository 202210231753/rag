# 路由汇总（把下面两个拼起来）
from fastapi import APIRouter
from app.api.v1.endpoints import viewer, chat, search

api_router = APIRouter()

# 挂载你的模块 (访问地址: /api/v1/viewer/...)
api_router.include_router(viewer.router, prefix="/viewer", tags=["数据查看模块"])

# 挂载同事的模块 (访问地址: /api/v1/chat/...)
# api_router.include_router(chat.router, prefix="/chat", tags=["RAG对话模块"])

# 挂载多路召回搜索模块 (访问地址: /api/v1/search/...)
api_router.include_router(search.router, prefix="/search", tags=["多路召回搜索"])