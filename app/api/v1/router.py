# 路由汇总（把下面两个拼起来）
from fastapi import APIRouter
from app.api.v1.endpoints import viewer, chat, tokenizer, term_weight, search, ranking

api_router = APIRouter()

# 挂载你的模块 (访问地址: /api/v1/viewer/...)
api_router.include_router(viewer.router, prefix="/viewer", tags=["数据查看模块"])

# 挂载你的第二个模块：中文分词 (访问地址: /api/v1/tokenizer/...)
api_router.include_router(tokenizer.router, prefix="/tokenizer", tags=["中文分词模块"])

# 挂载你的第三个模块：词权重 (访问地址: /api/v1/term-weight/...)
api_router.include_router(term_weight.router, prefix="/term-weight", tags=["词权重模块"])

# 挂载同事的模块 (访问地址: /api/v1/chat/...)
# api_router.include_router(chat.router, prefix="/chat", tags=["RAG对话模块"])

# 挂载多路召回搜索模块 (访问地址: /api/v1/search/...)
api_router.include_router(search.router, prefix="/search", tags=["多路召回搜索"])

# 挂载排序引擎管理模块 (访问地址: /api/v1/ranking/...)
api_router.include_router(ranking.router, prefix="/ranking", tags=["排序引擎管理"])
