from __future__ import annotations

import asyncio
import time
import unittest
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_hot_search_service, get_search_gateway
from app.api.v1.endpoints import hot_search as hot_search_endpoints
from app.api.v1.endpoints import search as search_endpoints
from app.hot_search.repository import HotSearchRepository
from app.hot_search.service import GovernanceService, HotSearchService
from app.rag.models.search_result import SearchResult


class _FakePipeline:
    def __init__(self, redis: "_FakeRedis"):
        self._redis = redis
        self._ops: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def smembers(self, key: str) -> "_FakePipeline":
        self._ops.append(("smembers", (key,), {}))
        return self

    def hgetall(self, key: str) -> "_FakePipeline":
        self._ops.append(("hgetall", (key,), {}))
        return self

    def hmget(self, key: str, keys: list[str]) -> "_FakePipeline":
        self._ops.append(("hmget", (key, keys), {}))
        return self

    def hdel(self, key: str, field: str) -> "_FakePipeline":
        self._ops.append(("hdel", (key, field), {}))
        return self

    def zscore(self, key: str, member: str) -> "_FakePipeline":
        self._ops.append(("zscore", (key, member), {}))
        return self

    def zincrby(self, key: str, amount: float, member: str) -> "_FakePipeline":
        self._ops.append(("zincrby", (key, amount, member), {}))
        return self

    async def execute(self) -> list[Any]:
        results: list[Any] = []
        for name, args, kwargs in self._ops:
            func = getattr(self._redis, name)
            results.append(await func(*args, **kwargs))
        self._ops.clear()
        return results


class _FakeRedis:
    """
    进程内 Redis 最小实现（仅覆盖热搜模块用到的命令）

    目的：在无法建立 socket 的环境中做集成级验证，不依赖真实 Redis。
    """

    def __init__(self):
        self._strings: dict[str, tuple[str, Optional[float]]] = {}
        self._sets: dict[str, set[str]] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._zsets: dict[str, dict[str, float]] = {}

    def pipeline(self) -> _FakePipeline:
        return _FakePipeline(self)

    async def ping(self) -> str:
        return "PONG"

    async def flushdb(self) -> bool:
        self._strings.clear()
        self._sets.clear()
        self._hashes.clear()
        self._zsets.clear()
        return True

    async def set(self, key: str, value: str, *, nx: bool = False, ex: Optional[int] = None):
        now = time.time()
        if nx:
            existing = self._strings.get(key)
            if existing is not None:
                _, expire_at = existing
                if expire_at is None or expire_at > now:
                    return None
        expire_at = (now + ex) if ex else None
        self._strings[key] = (str(value), expire_at)
        return True

    async def sadd(self, key: str, *members: str) -> int:
        s = self._sets.setdefault(key, set())
        before = len(s)
        for m in members:
            if m:
                s.add(str(m))
        return len(s) - before

    async def srem(self, key: str, *members: str) -> int:
        s = self._sets.setdefault(key, set())
        removed = 0
        for m in members:
            if m in s:
                s.remove(m)
                removed += 1
        return removed

    async def smembers(self, key: str) -> set[str]:
        return set(self._sets.get(key, set()))

    async def hset(self, key: str, field: str, value: str) -> int:
        h = self._hashes.setdefault(key, {})
        existed = 1 if field in h else 0
        h[str(field)] = str(value)
        return 0 if existed else 1

    async def hget(self, key: str, field: str) -> Optional[str]:
        return self._hashes.get(key, {}).get(field)

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._hashes.get(key, {}))

    async def hmget(self, key: str, keys: list[str]) -> list[Optional[str]]:
        h = self._hashes.get(key, {})
        return [h.get(k) for k in keys]

    async def hdel(self, key: str, field: str) -> int:
        h = self._hashes.get(key, {})
        if field in h:
            del h[field]
            return 1
        return 0

    async def zscore(self, key: str, member: str) -> Optional[float]:
        return self._zsets.get(key, {}).get(member)

    async def zincrby(self, key: str, amount: float, member: str) -> float:
        z = self._zsets.setdefault(key, {})
        z[member] = float(z.get(member, 0.0)) + float(amount)
        return float(z[member])

    async def zrevrange(self, key: str, start: int, end: int, *, withscores: bool = False):
        z = self._zsets.get(key, {})
        items = sorted(z.items(), key=lambda x: (-x[1], x[0]))

        if end < 0:
            sliced = items[start:]
        else:
            sliced = items[start : end + 1]

        if withscores:
            return [(k, float(v)) for k, v in sliced]
        return [k for k, _ in sliced]

    async def zunionstore(self, dest: str, keys, aggregate: str | None = None):
        # 兼容 redis-py 新旧签名：keys 可能是 list[str] 或 {key: weight}
        if aggregate not in (None, "sum"):
            raise NotImplementedError("当前仅支持默认 sum 聚合")

        if isinstance(keys, dict):
            if len(keys) != 1:
                raise NotImplementedError("当前仅支持单个 zset 的 zunionstore")
            (src, weight), = list(keys.items())
        else:
            if len(keys) != 1:
                raise NotImplementedError("当前仅支持单个 zset 的 zunionstore")
            src = keys[0]
            weight = 1.0

        weight = float(weight)
        src_z = self._zsets.get(src, {})
        self._zsets[dest] = {k: float(v) * weight for k, v in src_z.items()}
        return len(self._zsets[dest])

    async def rename(self, src: str, dest: str) -> bool:
        if src in self._zsets:
            self._zsets[dest] = self._zsets[src]
            del self._zsets[src]
            return True
        raise KeyError(src)

    async def eval(self, script: str, numkeys: int, *args):
        """
        仅实现 hot_search incr 脚本：HGET boost -> ZINCRBY hot_list
        """
        if numkeys != 2:
            raise NotImplementedError("仅支持 2 个 key 的 eval")
        boost_key, hot_key, keyword, base_increment = args
        boost = await self.hget(str(boost_key), str(keyword))
        if boost is None:
            boost = "1"
        delta = float(base_increment) * float(boost)
        return await self.zincrby(str(hot_key), delta, str(keyword))


class _FakeRedisClient:
    def __init__(self, client: _FakeRedis):
        self._client = client

    @property
    def client(self) -> _FakeRedis:
        return self._client


class _StubSearchGateway:
    async def search(self, query: str, **kwargs) -> SearchResult:
        return SearchResult(query=query, results=[], total=0, took_ms=1.0, recall_stats={"merged": 0})


class HotSearchApiIntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._redis = _FakeRedis()
        self._redis_client = _FakeRedisClient(self._redis)

        repo = HotSearchRepository(self._redis_client)  # type: ignore[arg-type]
        governance = GovernanceService(repo)
        self._service = HotSearchService(
            repo=repo,
            governance=governance,
            base_increment=1.0,
            base_decay_factor=0.9,
            candidate_multiplier=3,
        )

        app = FastAPI()
        app.include_router(hot_search_endpoints.router, prefix="/api/v1/hot-search")
        app.include_router(search_endpoints.router, prefix="/api/v1/search")
        app.dependency_overrides[get_hot_search_service] = lambda: self._service
        app.dependency_overrides[get_search_gateway] = lambda: _StubSearchGateway()
        self._client = TestClient(app)

        asyncio.run(self._redis.flushdb())

    def tearDown(self) -> None:
        self._client.close()

    def test_search_success_increments_and_normalizes(self) -> None:
        r = self._client.post(
            "/api/v1/search/multi-recall",
            json={
                "query": "  TOPWORD  ",
                "top_n": 5,
                "recall_top_k": 10,
                "enable_rerank": False,
                "enable_ranking": False,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)

        r = self._client.get("/api/v1/hot-search/trending?limit=20")
        self.assertEqual(r.status_code, 200, r.text)
        items = r.json()["items"]
        self.assertEqual(items[0]["keyword"], "topword")
        self.assertAlmostEqual(items[0]["heat_score"], 1.0, places=6)

    def test_blocked_filters_trending_even_if_counted(self) -> None:
        r = self._client.post(
            "/api/v1/hot-search/blocked", json={"action": "add", "words": ["bad"]}
        )
        self.assertEqual(r.status_code, 200, r.text)

        r = self._client.post(
            "/api/v1/search/multi-recall",
            json={
                "query": "BAD",
                "top_n": 5,
                "recall_top_k": 10,
                "enable_rerank": False,
                "enable_ranking": False,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)

        r = self._client.get("/api/v1/hot-search/trending?limit=20")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(all(x["keyword"] != "bad" for x in r.json()["items"]))

    def test_pinned_boost_and_decay_factor(self) -> None:
        # 置顶 + 加权
        r = self._client.put("/api/v1/hot-search/pinned/1", json={"keyword": "TopWord"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["keyword"], "topword")

        r = self._client.put(
            "/api/v1/hot-search/boost/TOPWORD", json={"search_boost": 2.0, "decay_factor": 1.0}
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["keyword"], "topword")

        # 计数两次：2 * 2.0 = 4.0
        for _ in range(2):
            r = self._client.post(
                "/api/v1/search/multi-recall",
                json={
                    "query": "topword",
                    "top_n": 5,
                    "recall_top_k": 10,
                    "enable_rerank": False,
                    "enable_ranking": False,
                },
            )
            self.assertEqual(r.status_code, 200, r.text)

        # 普通词 other：1.0
        r = self._client.post(
            "/api/v1/search/multi-recall",
            json={
                "query": "Other",
                "top_n": 5,
                "recall_top_k": 10,
                "enable_rerank": False,
                "enable_ranking": False,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)

        r = self._client.get("/api/v1/hot-search/trending?limit=20")
        self.assertEqual(r.status_code, 200, r.text)
        items = r.json()["items"]
        self.assertEqual(items[0]["keyword"], "topword")
        self.assertAlmostEqual(items[0]["heat_score"], 4.0, places=6)

        # 衰减：topword 豁免；other 乘以 0.9
        executed = asyncio.run(self._service.decay_once(lock_ttl_seconds=1))
        self.assertTrue(executed)

        r = self._client.get("/api/v1/hot-search/trending?limit=20")
        self.assertEqual(r.status_code, 200, r.text)
        items = r.json()["items"]
        topword = next(x for x in items if x["keyword"] == "topword")
        other = next(x for x in items if x["keyword"] == "other")

        self.assertAlmostEqual(topword["heat_score"], 4.0, places=6)
        self.assertAlmostEqual(other["heat_score"], 0.9, places=6)


if __name__ == "__main__":
    unittest.main()
