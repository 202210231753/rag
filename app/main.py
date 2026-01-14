# 【入口】整个程序的启动点
from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html

from app.api.v1.router import api_router


app = FastAPI(
    title="RAG Knowledge System",
    description="后端 API 接口文档",
    version="1.0.0",
    # 默认 ReDoc 会引用 jsdelivr 的 redoc@next 链接；在部分网络环境下该链接会 404 导致页面空白。
    # 这里关闭内置 redoc_url，改用自定义路由指定一个可用的 redoc_js_url。
    redoc_url=None,
)

# 注册所有路由，统一加前缀 /api/v1
app.include_router(api_router, prefix="/api/v1")


@app.get("/redoc", include_in_schema=False)
def redoc() -> object:
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://unpkg.com/redoc@3.0.0-rc.0/bundles/redoc.standalone.js",
    )


@app.get("/")
def health_check():
    return {"status": "ok", "message": "RAG System is running!"}