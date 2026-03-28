"""基于内部模块调用的评测引擎实现。"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Awaitable, Callable, Mapping, Optional, Sequence

from app.eval.core.interfaces import Engine


def _import_from_path(path: str) -> Any:
    """通过字符串路径导入对象。"""
    if not path or "." not in path:
        raise ValueError("无效的 import 路径")
    module_path, attr_name = path.rsplit(".", 1)
    module = import_module(module_path)
    return getattr(module, attr_name)


class InternalEngine(Engine):
    """直接调用内部 SearchGateway 的评测引擎。"""

    def __init__(
        self,
        search_gateway_path: Optional[str] = None,
        gateway: Any = None,
        *,
        lazy_init: bool = False,
        rerank_fn: Optional[Callable[[str, Sequence[Mapping[str, Any]]], Awaitable[Mapping[str, Any]]]] = None,
        rewrite_fn: Optional[Callable[[str], Awaitable[str]]] = None,
        generate_fn: Optional[Callable[[str, Sequence[str]], Awaitable[Mapping[str, Any]]]] = None,
    ) -> None:
        self._search_gateway_path = search_gateway_path or "app.api.deps.get_search_gateway"
        self._lazy_init = bool(lazy_init)
        self._gateway: Any = gateway
        self._rerank_fn = rerank_fn
        self._rewrite_fn = rewrite_fn
        self._generate_fn = generate_fn

        if self._gateway is None and not self._lazy_init:
            self._gateway = self._build_gateway()

    def _build_gateway(self) -> Any:
        get_gateway = _import_from_path(self._search_gateway_path)
        if callable(get_gateway):
            return get_gateway()
        return get_gateway

    def _get_gateway(self) -> Any:
        if self._gateway is None:
            self._gateway = self._build_gateway()
        return self._gateway

    async def retrieve(self, query: str, top_n: int, recall_top_k: int) -> Mapping[str, Any]:
        gateway = self._get_gateway()
        result = await gateway.search(
            query=query,
            top_n=top_n,
            recall_top_k=recall_top_k,
            enable_rerank=False,
            enable_ranking=True,
        )

        # SearchResult 为 Pydantic 模型，提供 model_dump 或 dict
        if hasattr(result, "model_dump"):
            return result.model_dump()
        if hasattr(result, "dict"):
            return result.dict()
        return result

    async def rerank(self, query: str, candidates: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        if self._rerank_fn is None:
            raise NotImplementedError("内部 rerank 引擎尚未实现")
        return await self._rerank_fn(query, candidates)

    async def rewrite(self, query: str) -> str:
        if self._rewrite_fn is None:
            raise NotImplementedError("内部 rewrite 引擎尚未实现")
        return await self._rewrite_fn(query)

    async def generate(self, query: str, contexts: Sequence[str]) -> Mapping[str, Any]:
        if self._generate_fn is None:
            raise NotImplementedError("内部 generate 引擎尚未实现")
        return await self._generate_fn(query, contexts)
