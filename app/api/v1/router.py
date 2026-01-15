# 路由汇总（把下面两个拼起来）
from fastapi import APIRouter
from app.api.v1.endpoints import viewer, chat
from app.api.v1.endpoints import abtest

api_router = APIRouter()

# 挂载你的模块 (访问地址: /api/v1/viewer/...)
api_router.include_router(viewer.router, prefix="/viewer", tags=["数据查看模块"])

# 挂载 AB 实验模块 (访问地址: /api/v1/abtest/...)
api_router.include_router(abtest.router, prefix="/abtest", tags=["运营管理-AB实验"])

# 挂载 RAG 对话模块 (访问地址: /api/v1/chat/...)
api_router.include_router(chat.router, prefix="/chat", tags=["RAG对话模块"])