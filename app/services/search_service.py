"""检索服务（集成同义词改写）。"""
from __future__ import annotations

import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.core.elasticsearch_client import get_elasticsearch_client
from app.services.synonym_service import SynonymService
from app.schemas.synonym_schema import RewritePlan

logger = logging.getLogger(__name__)


class SearchService:
    """检索服务（集成同义词扩展）。"""

    def __init__(self, db: Session, original_boost: float = 1.0, synonym_boost: float = 0.6):
        """
        Args:
            db: 数据库会话
            original_boost: 原查询的 boost 值
            synonym_boost: 同义词扩展的 boost 值（应 < original_boost）
        """
        self.db = db
        self.es_client = get_elasticsearch_client()
        self.synonym_service = SynonymService(db)
        self.original_boost = original_boost
        self.synonym_boost = synonym_boost

    def _build_es_query(self, rewrite_plan: RewritePlan, field: str = "content") -> Dict[str, Any]:
        """
        构建 ES bool 查询（原查询 must，同义词 should）。
        
        Args:
            rewrite_plan: 改写计划
            field: 查询字段名
        
        Returns:
            ES 查询 DSL
        """
        original_query = rewrite_plan.original_query
        expanded_terms = rewrite_plan.expanded_terms

        # 构建 must 子句（原查询）
        must_clauses = [
            {
                "match": {
                    field: {
                        "query": original_query,
                        "boost": self.original_boost,
                    }
                }
            }
        ]

        # 构建 should 子句（同义词扩展）
        should_clauses = []
        if expanded_terms:
            for term in expanded_terms:
                should_clauses.append(
                    {
                        "match": {
                            field: {
                                "query": term,
                                "boost": self.synonym_boost,
                            }
                        }
                    }
                )

        # 组装 bool 查询
        bool_query: Dict[str, Any] = {
            "bool": {
                "must": must_clauses,
            }
        }

        if should_clauses:
            bool_query["bool"]["should"] = should_clauses
            bool_query["bool"]["minimum_should_match"] = 0  # should 是可选的

        query_dsl = {"query": bool_query}
        logger.debug(f"ES 查询构造: original={original_query}, expanded={expanded_terms}")
        return query_dsl

    def search(
        self,
        query: str,
        domain: str = "default",
        index: str = "documents",
        field: str = "content",
        size: int = 10,
        return_rewrite_plan: bool = False,
    ) -> Dict[str, Any]:
        """
        执行检索（带同义词扩展）。
        
        Args:
            query: 查询文本
            domain: 领域
            index: ES 索引名
            field: 查询字段
            size: 返回结果数量
            return_rewrite_plan: 是否返回改写计划（用于调试）
        
        Returns:
            检索结果，包含 hits 和可选的 rewrite_plan
        """
        # 1. 查询改写
        rewrite_plan = self.synonym_service.rewrite(domain, query)

        # 2. 构建 ES 查询
        query_dsl = self._build_es_query(rewrite_plan, field=field)
        query_dsl["size"] = size

        # 3. 执行 ES 查询
        try:
            response = self.es_client.search(index=index, body=query_dsl)
            hits = response.get("hits", {}).get("hits", [])
            total = response.get("hits", {}).get("total", {})

            result = {
                "hits": [
                    {
                        "id": hit.get("_id"),
                        "score": hit.get("_score"),
                        "source": hit.get("_source", {}),
                    }
                    for hit in hits
                ],
                "total": total.get("value", 0) if isinstance(total, dict) else total,
            }

            if return_rewrite_plan:
                result["rewrite_plan"] = rewrite_plan

            logger.info(
                f"检索完成: query={query}, domain={domain}, hits={len(hits)}, expanded={len(rewrite_plan.expanded_terms)}"
            )
            return result

        except Exception as e:
            logger.error(f"ES 检索失败: {e}", exc_info=True)
            # 降级：只使用原查询
            fallback_dsl = {
                "query": {
                    "match": {
                        field: {
                            "query": query,
                        }
                    }
                },
                "size": size,
            }
            try:
                response = self.es_client.search(index=index, body=fallback_dsl)
                hits = response.get("hits", {}).get("hits", [])
                total = response.get("hits", {}).get("total", {})
                return {
                    "hits": [
                        {
                            "id": hit.get("_id"),
                            "score": hit.get("_score"),
                            "source": hit.get("_source", {}),
                        }
                        for hit in hits
                    ],
                    "total": total.get("value", 0) if isinstance(total, dict) else total,
                    "error": "同义词扩展失败，已降级为原查询",
                }
            except Exception as e2:
                logger.error(f"降级检索也失败: {e2}", exc_info=True)
                raise







