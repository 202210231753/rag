"""
输入提示（Suggest）API 端点

- 零查询推荐：onFocus 时返回历史/上下文/热搜的合并列表
- 输入中补全：前缀匹配不足时触发纠错（编辑距离）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from app.api.deps import get_suggestion_service
from app.schemas.suggest_schema import CompletionListResponse, SuggestionListResponse
from app.suggest.service import SuggestService


router = APIRouter()


@router.get("/zero-query", response_model=SuggestionListResponse, summary="零查询推荐（焦点推荐）")
async def get_zero_query_recs(
    user_id: str = Query(..., min_length=1, description="用户ID"),
    limit: int = Query(20, ge=1, le=100, description="返回条数（默认20）"),
    context: list[str] | None = Query(default=None, description="上下文标签（可重复传参）"),
    service: SuggestService = Depends(get_suggestion_service),
) -> SuggestionListResponse:
    try:
        items = await service.get_zero_query_recs(user_id=user_id, limit=limit, context=context or [])
        return SuggestionListResponse(limit=limit, items=items)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"零查询推荐失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/complete", response_model=CompletionListResponse, summary="输入提示：前缀补全 + 拼写纠错")
async def auto_complete(
    user_id: str = Query(..., min_length=1, description="用户ID"),
    query: str = Query(..., min_length=1, description="当前输入（将被规范化）"),
    limit: int = Query(10, ge=1, le=50, description="返回条数（默认10）"),
    max_edit_dist: int = Query(1, ge=1, le=2, description="最大编辑距离（1-2）"),
    service: SuggestService = Depends(get_suggestion_service),
) -> CompletionListResponse:
    try:
        items = await service.auto_complete(
            user_id=user_id,
            query=query,
            limit=limit,
            max_edit_dist=max_edit_dist,
        )
        return CompletionListResponse(limit=limit, items=items)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"输入提示失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

