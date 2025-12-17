# 【入口】整个程序的启动点
from fastapi import FastAPI
from app.api.v1.router import api_router

app = FastAPI(
    title="RAG Knowledge System",
    description="后端 API 接口文档",
    version="1.0.0"
)

# 注册所有路由，统一加前缀 /api/v1
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "RAG System is running!"}