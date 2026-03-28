"""基于 HTTP API 的评测引擎实现。"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

import httpx

from app.eval.core.interfaces import Engine


@dataclass
class CircuitBreakerConfig:
    enabled: bool = False
    failure_threshold: int = 5
    reset_seconds: int = 30


class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig) -> None:
        self._cfg = config
        self._failures = 0
        self._opened_at: Optional[float] = None

    def allow(self) -> bool:
        if not self._cfg.enabled:
            return True
        if self._opened_at is None:
            return True
        if (time.monotonic() - self._opened_at) >= self._cfg.reset_seconds:
            self._opened_at = None
            self._failures = 0
            return True
        return False

    def record_success(self) -> None:
        if not self._cfg.enabled:
            return
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        if not self._cfg.enabled:
            return
        self._failures += 1
        if self._failures >= self._cfg.failure_threshold:
            self._opened_at = time.monotonic()


class ApiEngine(Engine):
    """通过 FastAPI HTTP 接口执行评测动作。"""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: int = 30,
        max_concurrency: int = 10,
        retries: int = 2,
        retry_backoff_seconds: float = 0.2,
        retry_on_status: Optional[Iterable[int]] = None,
        verify_ssl: bool = True,
        circuit_breaker: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        endpoints: Optional[Dict[str, str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_concurrency = max(1, int(max_concurrency))
        self.retries = retries
        self.retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))
        self.retry_on_status = set(retry_on_status or [429, 500, 502, 503, 504])
        self.verify_ssl = bool(verify_ssl)
        self.headers = headers or {}
        self.endpoints = {
            "retrieve": "/api/v1/search/multi-recall",
            "rerank": "",
            "rewrite": "",
            "generate": "",
        }
        if endpoints:
            self.endpoints.update(endpoints)

        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        cb_config = CircuitBreakerConfig(**(circuit_breaker or {}))
        self._circuit_breaker = CircuitBreaker(cb_config)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout_seconds,
                verify=self.verify_ssl,
            )
        return self._client

    async def _request(self, method: str, url: str, json_body: Optional[Dict[str, Any]] = None) -> Mapping[str, Any]:
        if not url:
            raise NotImplementedError("未配置 API 路径")

        if not self._circuit_breaker.allow():
            raise RuntimeError("API circuit breaker is open")

        last_error: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            try:
                async with self._semaphore:
                    client = await self._get_client()
                    response = await client.request(method, url, json=json_body)
                    if response.status_code in self.retry_on_status:
                        raise httpx.HTTPStatusError(
                            f"retryable status: {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                    response.raise_for_status()
                    self._circuit_breaker.record_success()
                    data = response.json()
                    if isinstance(data, dict):
                        return data
                    return {"data": data}
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response is not None and exc.response.status_code not in self.retry_on_status:
                    self._circuit_breaker.record_failure()
                    raise
                self._circuit_breaker.record_failure()
                await asyncio.sleep(self.retry_backoff_seconds * (2 ** attempt))
                continue
            except Exception as exc:
                last_error = exc
                self._circuit_breaker.record_failure()
                await asyncio.sleep(self.retry_backoff_seconds * (2 ** attempt))
                continue
        raise RuntimeError(f"API 请求失败: {last_error}")

    async def retrieve(self, query: str, top_n: int, recall_top_k: int) -> Mapping[str, Any]:
        payload = {
            "query": query,
            "top_n": top_n,
            "recall_top_k": recall_top_k,
            "enable_rerank": False,
            "enable_ranking": True,
        }
        return await self._request("POST", self.endpoints["retrieve"], json_body=payload)

    async def rerank(self, query: str, candidates: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        if not self.endpoints.get("rerank"):
            raise NotImplementedError("未配置 rerank API")
        payload = {"query": query, "candidates": list(candidates)}
        return await self._request("POST", self.endpoints["rerank"], json_body=payload)

    async def rewrite(self, query: str) -> str:
        if not self.endpoints.get("rewrite"):
            raise NotImplementedError("未配置 rewrite API")
        payload = {"query": query}
        data = await self._request("POST", self.endpoints["rewrite"], json_body=payload)
        return str(data.get("rewrite") or data.get("query") or "")

    async def generate(self, query: str, contexts: Sequence[str]) -> Mapping[str, Any]:
        if not self.endpoints.get("generate"):
            raise NotImplementedError("未配置 generate API")
        payload = {"query": query, "contexts": list(contexts)}
        return await self._request("POST", self.endpoints["generate"], json_body=payload)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
