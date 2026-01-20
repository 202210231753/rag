"""
服务模块入口。

注意：这里不要做“强导入”，否则会在导入任意子模块（如 `app.services.tokenizer_admin_service`）
时连带加载一堆无关依赖/模型，给测试与轻量脚本带来副作用。
"""

from __future__ import annotations

from typing import Any

__all__ = ["ContentRecommenderService", "QueryRecommenderService", "FeedbackService", "ViewerService"]


_LAZY_IMPORTS = {
    "ContentRecommenderService": (".recommender_service", "ContentRecommenderService"),
    "QueryRecommenderService": (".recommender_service", "QueryRecommenderService"),
    "FeedbackService": (".feedback_service", "FeedbackService"),
    "ViewerService": (".viewer_service", "ViewerService"),
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_IMPORTS:
        raise AttributeError(name)
    module_path, attr = _LAZY_IMPORTS[name]
    from importlib import import_module

    module = import_module(module_path, __name__)
    return getattr(module, attr)
