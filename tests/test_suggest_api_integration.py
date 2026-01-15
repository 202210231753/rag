from __future__ import annotations

import asyncio
import unittest

from app.api.v1.endpoints import search as search_endpoints
from app.api.v1.endpoints import suggest as suggest_endpoints
from app.hot_search.repository import HotSearchRepository
from app.hot_search.service import GovernanceService, HotSearchService
from app.rag.models.search_result import SearchResult
from app.schemas.search_schema import SearchRequest
from app.suggest.keys import SuggestKeys
from app.suggest.repository import SuggestRepository
from app.suggest.service import SuggestConfig, SuggestService
from tests.fake_redis import FakeRedis, FakeRedisClient


class _StubSearchGateway:
    async def search(self, query: str, **kwargs) -> SearchResult:
        return SearchResult(query=query, results=[], total=0, took_ms=1.0, recall_stats={"merged": 0})


class SuggestApiIntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._redis = FakeRedis()
        self._redis_client = FakeRedisClient(self._redis)

        hot_repo = HotSearchRepository(self._redis_client)  # type: ignore[arg-type]
        hot_governance = GovernanceService(hot_repo)
        self._hot_service = HotSearchService(
            repo=hot_repo,
            governance=hot_governance,
            base_increment=1.0,
            base_decay_factor=0.9,
            candidate_multiplier=3,
        )

        suggest_keys = SuggestKeys.with_prefix("")
        suggest_repo = SuggestRepository(self._redis_client, keys=suggest_keys)  # type: ignore[arg-type]
        self._suggest_service = SuggestService(
            repo=suggest_repo,
            hot_search=self._hot_service,
            config=SuggestConfig(history_max=50, trending_candidate_limit=50, fuzzy_candidate_limit=200),
        )

        asyncio.run(self._redis.flushdb())

    def tearDown(self) -> None:
        return None

    def _search(self, *, user_id: str | None, query: str) -> None:
        request = SearchRequest(
            user_id=user_id,
            query=query,
            top_n=5,
            recall_top_k=10,
            enable_rerank=False,
            enable_ranking=False,
        )
        asyncio.run(
            search_endpoints.multi_recall_search(
                request,
                gateway=_StubSearchGateway(),
                hot_search=self._hot_service,
                suggest=self._suggest_service,
            )
        )

    def test_zero_query_merges_and_dedupes(self) -> None:
        user_id = "u1"
        self._search(user_id=user_id, query="Vector DB")
        self._search(user_id=user_id, query="RAG")

        self._search(user_id=None, query="Global")
        self._search(user_id=None, query="RAG")  # 重复词：会同时出现在历史与热搜

        resp = asyncio.run(
            suggest_endpoints.get_zero_query_recs(
                user_id=user_id,
                limit=10,
                context=["API 参考", "RAG"],
                service=self._suggest_service,
            )
        )
        contents = [x.content for x in resp.items]

        self.assertTrue(contents[0] in {"rag", "vector db"})
        self.assertTrue(contents[1] in {"rag", "vector db"})
        self.assertEqual(len(contents), len(set(contents)))
        self.assertIn("api 参考", contents)

    def test_complete_prefix_and_fuzzy(self) -> None:
        user_id = "u2"
        self._search(user_id=user_id, query="retrieval")
        self._search(user_id=user_id, query="遥遥领先")
        self._search(user_id=None, query="vector db")

        resp = asyncio.run(
            suggest_endpoints.auto_complete(
                user_id=user_id,
                query="re",
                limit=10,
                max_edit_dist=1,
                service=self._suggest_service,
            )
        )
        contents = [x.content for x in resp.items]
        self.assertIn("retrieval", contents)

        resp = asyncio.run(
            suggest_endpoints.auto_complete(
                user_id=user_id,
                query="retreival",
                limit=10,
                max_edit_dist=2,
                service=self._suggest_service,
            )
        )
        contents = [x.content for x in resp.items]
        self.assertIn("retrieval", contents)

        resp = asyncio.run(
            suggest_endpoints.auto_complete(
                user_id=user_id,
                query="遥遥",
                limit=10,
                max_edit_dist=1,
                service=self._suggest_service,
            )
        )
        contents = [x.content for x in resp.items]
        self.assertIn("遥遥领先", contents)


if __name__ == "__main__":
    unittest.main()
