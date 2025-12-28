# 路由汇总（把下面两个拼起来）
from fastapi import APIRouter
from app.api.v1.endpoints import viewer, chat, intervention, ingest, files, knowledge

api_router = APIRouter()

# 挂载知识库管理模块 (访问地址: /api/v1/knowledge/...)
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库管理模块"])

# 挂载你的模块 (访问地址: /api/v1/viewer/...)
api_router.include_router(viewer.router, prefix="/viewer", tags=["数据查看模块"])

# 挂载数据干预模块 (访问地址: /api/v1/intervention/...)
api_router.include_router(intervention.router, prefix="/intervention", tags=["数据干预模块"])

# 挂载数据摄入模块 (访问地址: /api/v1/ingest/...)
api_router.include_router(ingest.router, prefix="/ingest", tags=["数据摄入模块"])

# 挂载文件代理模块 (访问地址: /api/v1/files/...)
api_router.include_router(files.router, prefix="/files", tags=["文件代理模块"])

# 挂载同事的模块 (访问地址: /api/v1/chat/...)
# api_router.include_router(chat.router, prefix="/chat", tags=["RAG对话模块"])