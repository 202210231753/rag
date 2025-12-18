"""
API 端点模块

包含所有 v1 版本的 API 端点定义
"""

from app.api.v1.endpoints import viewer, search

# chat 模块待开发
# from app.api.v1.endpoints import chat

__all__ = ["viewer", "search"]
