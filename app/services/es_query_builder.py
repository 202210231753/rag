"""Elasticsearch 查询构造器（支持同义词扩展）。"""
from __future__ import annotations

import logging
from typing import List, Dict, Any

from app.schemas.synonym_schema import RewritePlan

logger = logging.getLogger(__name__)


class ESQueryBuilder:
    """ES 查询构造器，支持同义词扩展。"""

    def __init__(self, original_boost: float = 1.0, synonym_boost: float = 0.6):
        """
        Args:
            original_boost: 原查询的 boost 值
            synonym_boost: 同义词扩展的 boost 值（应 < original_boost）
        """
        self.original_boost = original_boost
        self.synonym_boost = synonym_boost

    def build_query(self, rewrite_plan: RewritePlan, field: str = "content") -> Dict[str, Any]:
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

        logger.debug(f"ES 查询构造: original={original_query}, expanded={expanded_terms}, DSL={query_dsl}")
        return query_dsl

    def build_multi_match_query(
        self,
        rewrite_plan: RewritePlan,
        fields: List[str] = None,
        type: str = "best_fields",
    ) -> Dict[str, Any]:
        """
        构建 ES multi_match 查询（支持多字段）。
        
        Args:
            rewrite_plan: 改写计划
            fields: 查询字段列表，如 ["title^2", "content"]
            type: 匹配类型（best_fields/cross_fields/phrase等）
        
        Returns:
            ES 查询 DSL
        """
        if fields is None:
            fields = ["content"]

        original_query = rewrite_plan.original_query
        expanded_terms = rewrite_plan.expanded_terms

        # 构建 must 子句（原查询）
        must_clauses = [
            {
                "multi_match": {
                    "query": original_query,
                    "fields": fields,
                    "type": type,
                    "boost": self.original_boost,
                }
            }
        ]

        # 构建 should 子句（同义词扩展）
        should_clauses = []
        if expanded_terms:
            for term in expanded_terms:
                should_clauses.append(
                    {
                        "multi_match": {
                            "query": term,
                            "fields": fields,
                            "type": type,
                            "boost": self.synonym_boost,
                        }
                    }
                )

        bool_query: Dict[str, Any] = {
            "bool": {
                "must": must_clauses,
            }
        }

        if should_clauses:
            bool_query["bool"]["should"] = should_clauses
            bool_query["bool"]["minimum_should_match"] = 0

        query_dsl = {"query": bool_query}
        return query_dsl


















