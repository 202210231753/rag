from __future__ import annotations

import asyncio
import unittest

from app.api.v1.endpoints import hot_search as hot_search_endpoints
from app.api.v1.endpoints import search as search_endpoints
from app.hot_search.repository import HotSearchRepository
from app.hot_search.service import GovernanceService, HotSearchService
from app.rag.models.search_result import SearchResult
from app.schemas.search_schema import SearchRequest
from tests.fake_redis import FakeRedis, FakeRedisClient


class _StubSearchGateway:
    async def search(self, query: str, **kwargs) -> SearchResult:
        return SearchResult(query=query, results=[], total=0, took_ms=1.0, recall_stats={"merged": 0})


class _NoopSuggestService:
    async def record_search(self, user_id: str | None, query: str) -> None:
        return None


class HotSearchApiIntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._redis = FakeRedis()
        self._redis_client = FakeRedisClient(self._redis)

        repo = HotSearchRepository(self._redis_client)  # type: ignore[arg-type]
        governance = GovernanceService(repo)
        self._service = HotSearchService(
            repo=repo,
            governance=governance,
            base_increment=1.0,
            base_decay_factor=0.9,
            candidate_multiplier=3,
        )

        asyncio.run(self._redis.flushdb())

    def tearDown(self) -> None:
        return None

    def test_search_success_increments_and_normalizes(self) -> None:
        request = SearchRequest(
            query="  TOPWORD  ",
            top_n=5,
            recall_top_k=10,
            enable_rerank=False,
            enable_ranking=False,
        )
        result = asyncio.run(
            search_endpoints.multi_recall_search(
                request,
                gateway=_StubSearchGateway(),
                hot_search=self._service,
                suggest=_NoopSuggestService(),  # type: ignore[arg-type]
            )
        )
        self.assertEqual(result.query.strip(), "TOPWORD")

        trending = asyncio.run(hot_search_endpoints.get_trending_list(limit=20, service=self._service))
        self.assertTrue(trending.items)
        self.assertEqual(trending.items[0].keyword, "topword")
        self.assertAlmostEqual(trending.items[0].heat_score, 1.0, places=6)

    def test_blocked_filters_trending_even_if_counted(self) -> None:
        resp = asyncio.run(
            hot_search_endpoints.manage_blocked_words(
                hot_search_endpoints.BlockedWordsRequest(action="add", words=["bad"]),
                service=self._service,
            )
        )
        self.assertEqual(resp.action, "add")

        request = SearchRequest(
            query="BAD",
            top_n=5,
            recall_top_k=10,
            enable_rerank=False,
            enable_ranking=False,
        )
        asyncio.run(
            search_endpoints.multi_recall_search(
                request,
                gateway=_StubSearchGateway(),
                hot_search=self._service,
                suggest=_NoopSuggestService(),  # type: ignore[arg-type]
            )
        )

        trending = asyncio.run(hot_search_endpoints.get_trending_list(limit=20, service=self._service))
        self.assertTrue(all(x.keyword != "bad" for x in trending.items))

    def test_pinned_boost_and_decay_factor(self) -> None:
        # 置顶 + 加权
        pinned = asyncio.run(
            hot_search_endpoints.pin_word(
                rank=1,
                request=hot_search_endpoints.PinWordRequest(keyword="TopWord"),
                service=self._service,
            )
        )
        self.assertEqual(pinned.keyword, "topword")

        boost = asyncio.run(
            hot_search_endpoints.upsert_boost(
                keyword="TOPWORD",
                request=hot_search_endpoints.BoostUpsertRequest(search_boost=2.0, decay_factor=1.0),
                service=self._service,
            )
        )
        self.assertEqual(boost.keyword, "topword")

        # 计数两次：2 * 2.0 = 4.0
        for _ in range(2):
            request = SearchRequest(
                query="topword",
                top_n=5,
                recall_top_k=10,
                enable_rerank=False,
                enable_ranking=False,
            )
            asyncio.run(
                search_endpoints.multi_recall_search(
                    request,
                    gateway=_StubSearchGateway(),
                    hot_search=self._service,
                    suggest=_NoopSuggestService(),  # type: ignore[arg-type]
                )
            )

        # 普通词 other：1.0
        request = SearchRequest(
            query="Other",
            top_n=5,
            recall_top_k=10,
            enable_rerank=False,
            enable_ranking=False,
        )
        asyncio.run(
            search_endpoints.multi_recall_search(
                request,
                gateway=_StubSearchGateway(),
                hot_search=self._service,
                suggest=_NoopSuggestService(),  # type: ignore[arg-type]
            )
        )

        trending = asyncio.run(hot_search_endpoints.get_trending_list(limit=20, service=self._service))
        items = trending.items
        self.assertEqual(items[0].keyword, "topword")
        self.assertAlmostEqual(items[0].heat_score, 4.0, places=6)

        # 衰减：topword 豁免；other 乘以 0.9
        executed = asyncio.run(self._service.decay_once(lock_ttl_seconds=1))
        self.assertTrue(executed)

        trending = asyncio.run(hot_search_endpoints.get_trending_list(limit=20, service=self._service))
        topword = next(x for x in trending.items if x.keyword == "topword")
        other = next(x for x in trending.items if x.keyword == "other")

        self.assertAlmostEqual(topword.heat_score, 4.0, places=6)
        self.assertAlmostEqual(other.heat_score, 0.9, places=6)


if __name__ == "__main__":
    unittest.main()
