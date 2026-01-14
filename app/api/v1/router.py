# 路由汇总（把下面两个拼起来）
from fastapi import APIRouter
from app.api.v1.endpoints import viewer, chat

from app.intervention.routers import censor as intervention_censor
from app.intervention.routers import whitelist as intervention_whitelist

api_router = APIRouter()

# 挂载你的模块 (访问地址: /api/v1/viewer/...)
api_router.include_router(viewer.router, prefix="/viewer", tags=["数据查看模块"])

# 挂载干预模块 (访问地址: /api/v1/intervention/...)
api_router.include_router(intervention_whitelist.router, prefix="/intervention/whitelist", tags=["干预-白名单"])
api_router.include_router(intervention_censor.router, prefix="/intervention/censor", tags=["干预-敏感词"])

# # 挂载同事的模块 (访问地址: /api/v1/chat/...)
# api_router.include_router(chat.router, prefix="/chat", tags=["RAG对话模块"])