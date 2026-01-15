"""
热搜服务 API 端点

- 热度计数：由搜索接口在“检索成功(HTTP 200)”后写入（不直接暴露写接口）
- 榜单读取：获取 TopN 热搜词
- 治理规则：屏蔽、置顶、加权（与 ranking 管理接口保持一致：不额外引入鉴权）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from app.api.deps import get_hot_search_service
from app.hot_search.normalization import normalize_keyword
from app.hot_search.service import HotSearchService
from app.schemas.hot_search_schema import (
    BlockedWordsRequest,
    BlockedWordsResponse,
    BoostEntry,
    BoostResponse,
    BoostUpsertRequest,
    MessageResponse,
    PinWordRequest,
    PinWordResponse,
    TrendingListResponse,
)

router = APIRouter()


@router.get("/trending", response_model=TrendingListResponse, summary="获取热搜榜单")
async def get_trending_list(
    limit: int = Query(20, ge=1, le=100, description="返回条数（默认20）"),
    service: HotSearchService = Depends(get_hot_search_service),
) -> TrendingListResponse:
    try:
        payload = await service.get_trending_list(limit)
        return TrendingListResponse(**payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"获取热搜榜单失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ========================================
# 屏蔽词管理
# ========================================
@router.post("/blocked", response_model=BlockedWordsResponse, summary="屏蔽词 add/remove")
async def manage_blocked_words(
    request: BlockedWordsRequest,
    service: HotSearchService = Depends(get_hot_search_service),
) -> BlockedWordsResponse:
    try:
        action = request.action.strip().lower()
        if action == "add":
            affected = await service.governance.add_blocked_words(request.words)
        elif action == "remove":
            affected = await service.governance.remove_blocked_words(request.words)
        else:
            raise HTTPException(status_code=400, detail="action 必须是 'add' 或 'remove'")

        total = len(await service.governance.get_blocked_words())
        return BlockedWordsResponse(action=action, affected_count=affected, total_count=total)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"屏蔽词管理失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/blocked", response_model=list[str], summary="获取屏蔽词列表")
async def list_blocked_words(
    service: HotSearchService = Depends(get_hot_search_service),
) -> list[str]:
    try:
        words = await service.governance.get_blocked_words()
        return sorted(list(words))
    except Exception as exc:
        logger.error(f"获取屏蔽词失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ========================================
# 置顶管理
# ========================================
@router.put("/pinned/{rank}", response_model=PinWordResponse, summary="设置置顶词（按 rank）")
async def pin_word(
    rank: int,
    request: PinWordRequest,
    service: HotSearchService = Depends(get_hot_search_service),
) -> PinWordResponse:
    try:
        await service.governance.pin_word(rank, request.keyword)
        return PinWordResponse(rank=rank, keyword=normalize_keyword(request.keyword))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"设置置顶失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/pinned/{rank}", response_model=MessageResponse, summary="删除置顶（按 rank）")
async def unpin_rank(
    rank: int,
    service: HotSearchService = Depends(get_hot_search_service),
) -> MessageResponse:
    try:
        deleted = await service.governance.unpin_rank(rank)
        if not deleted:
            raise HTTPException(status_code=404, detail="指定 rank 不存在置顶配置")
        return MessageResponse(message=f"rank_{rank} 已删除", success=True)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"删除置顶失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/pinned", response_model=dict[int, str], summary="获取全部置顶配置")
async def get_pinned_positions(
    service: HotSearchService = Depends(get_hot_search_service),
) -> dict[int, str]:
    try:
        return await service.governance.get_pinned_positions()
    except Exception as exc:
        logger.error(f"获取置顶配置失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ========================================
# 加权（Boost）管理
# ========================================
@router.put("/boost/{keyword}", response_model=BoostResponse, summary="设置/更新加权配置")
async def upsert_boost(
    keyword: str,
    request: BoostUpsertRequest,
    service: HotSearchService = Depends(get_hot_search_service),
) -> BoostResponse:
    try:
        await service.governance.set_boosts(
            keyword,
            search_boost=request.search_boost,
            decay_factor=request.decay_factor,
            base_decay_factor=service.base_decay_factor,
        )
        normalized = normalize_keyword(keyword)
        search_boost, decay_factor = await service.governance.get_boost(keyword)
        return BoostResponse(keyword=normalized, search_boost=search_boost, decay_factor=decay_factor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"设置加权失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/boost/{keyword}", response_model=MessageResponse, summary="删除加权配置（同时删除搜索倍率与衰减系数）")
async def delete_boost(
    keyword: str,
    service: HotSearchService = Depends(get_hot_search_service),
) -> MessageResponse:
    try:
        deleted_search, deleted_decay = await service.governance.delete_boosts(keyword)
        if not deleted_search and not deleted_decay:
            raise HTTPException(status_code=404, detail="加权配置不存在")
        return MessageResponse(message="已删除", success=True)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"删除加权失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/boost", response_model=list[BoostEntry], summary="获取全部加权配置")
async def list_boosts(
    service: HotSearchService = Depends(get_hot_search_service),
) -> list[BoostEntry]:
    try:
        data = await service.governance.get_all_boosts()
        result: list[BoostEntry] = []
        for keyword, (search_boost, decay_factor) in sorted(data.items(), key=lambda x: x[0]):
            result.append(
                BoostEntry(keyword=keyword, search_boost=search_boost, decay_factor=decay_factor)
            )
        return result
    except Exception as exc:
        logger.error(f"获取加权配置失败: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
