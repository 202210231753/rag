# 路由汇总（支持可选依赖的懒加载）
from __future__ import annotations

import logging
from importlib import import_module
from typing import Iterable

from fastapi import APIRouter

logger = logging.getLogger(__name__)

api_router = APIRouter()


def _include_router(module_path: str, prefix: str, tags: Iterable[str]) -> None:
    """
    以“尽量启动”为目标的路由注册：
    - 依赖未安装/外部服务不可用时，跳过对应模块，避免应用启动失败
    - 需要该功能时，再补齐依赖并重启服务
    """
    try:
        module = import_module(module_path)
        router = getattr(module, "router", None)
        if router is None:
            raise AttributeError(f"{module_path}.router 不存在")
        api_router.include_router(router, prefix=prefix, tags=list(tags))
    except Exception as exc:
        logger.warning(f"跳过路由模块: {module_path}（原因：{exc}）") 


# ========= 核心/轻依赖模块（优先保证可用） =========
_include_router("app.api.v1.endpoints.tokenizer", "/tokenizer", ["中文分词模块"])
_include_router("app.api.v1.endpoints.term_weight", "/term-weight", ["词权重模块"])


# ========= 其他模块（可能依赖外部服务/重依赖） =========
_include_router("app.api.v1.endpoints.knowledge", "/knowledge", ["知识库管理模块"])
_include_router("app.api.v1.endpoints.intervention", "/intervention", ["数据干预模块"])
_include_router("app.api.v1.endpoints.ingest", "/ingest", ["数据摄入模块"])
_include_router("app.api.v1.endpoints.files", "/files", ["文件代理模块"])
_include_router("app.api.v1.endpoints.viewer", "/viewer", ["数据查看模块"])
_include_router("app.api.v1.endpoints.synonym", "/synonyms", ["同义词模块"])
_include_router("app.api.v1.endpoints.synonym_mining", "/synonyms/mining", ["同义词挖掘模块"])
_include_router("app.api.v1.endpoints.search", "/search", ["多路召回搜索"])
_include_router("app.api.v1.endpoints.ranking", "/ranking", ["排序引擎管理"])
_include_router("app.api.v1.endpoints.hot_search", "/hot-search", ["热搜服务"])
_include_router("app.api.v1.endpoints.suggest", "/suggest", ["输入提示"])
_include_router("app.api.v1.endpoints.recommender", "/recommender", ["智能推荐模块"])
_include_router("app.api.v1.endpoints.abtest", "/abtest", ["运营管理-AB实验"])
_include_router("app.api.v1.endpoints.scene", "/scene", ["业务管控-场景管理"])
_include_router("app.api.v1.endpoints.chat", "/chat", ["RAG对话模块"])


# ========= 干预子模块（按需） =========
try:
    from app.intervention.routers import censor as intervention_censor
    from app.intervention.routers import whitelist as intervention_whitelist

    api_router.include_router(
        intervention_whitelist.router, prefix="/intervention/whitelist", tags=["干预-白名单"]
    )
    api_router.include_router(
        intervention_censor.router, prefix="/intervention/censor", tags=["干预-敏感词"]
    )
except Exception as exc:
    logger.warning(f"跳过干预子路由（原因：{exc}）")

