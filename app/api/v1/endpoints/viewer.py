# ✅【你的地盘】：数据查看接口
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.stats_schema import (
    ApiResponse,
    SearchStats,
    UserBehaviorStats,
    UserProfileStats,
)
from app.services.viewer_service import ViewerService

router = APIRouter()


@router.get("/user-profile", response_model=ApiResponse[UserProfileStats])
def get_user_profile_stats(
    start_time: int = Query(..., alias="startTime", description="统计开始时间戳 (ms)"),
    end_time: int = Query(..., alias="endTime", description="统计结束时间戳 (ms)"),
    dimensions: Optional[str] = Query(
        None, description="逗号分隔的维度列表，例如 gender,age,city"
    ),
    db: Session = Depends(deps.get_db),
) -> ApiResponse[UserProfileStats]:
    """
    用户基础数据统计。
    """
    start_dt, end_dt = _ensure_time_range(start_time, end_time)
    dimension_list = _parse_dimensions(dimensions)

    service = ViewerService(db)
    data = service.get_user_profile_stats(start_dt, end_dt, dimension_list)
    return ApiResponse(data=data)


@router.get("/user-behavior", response_model=ApiResponse[UserBehaviorStats])
def get_user_behavior_stats(
    start_time: int = Query(..., alias="startTime", description="统计开始时间戳 (ms)"),
    end_time: int = Query(..., alias="endTime", description="统计结束时间戳 (ms)"),
    granularity: str = Query(
        ...,
        description="时间粒度：hour、day、week",
    ),
    db: Session = Depends(deps.get_db),
) -> ApiResponse[UserBehaviorStats]:
    """
    用户行为数据统计。
    """
    start_dt, end_dt = _ensure_time_range(start_time, end_time)
    granularity = granularity.lower()
    if granularity not in {"hour", "day", "week"}:
        raise HTTPException(status_code=400, detail="granularity 仅支持 hour/day/week")

    service = ViewerService(db)
    data = service.get_user_behavior_stats(start_dt, end_dt, granularity)
    return ApiResponse(data=data)


@router.get("/search-summary", response_model=ApiResponse[SearchStats])
def get_search_stats(
    start_time: int = Query(..., alias="startTime", description="统计开始时间戳 (ms)"),
    end_time: int = Query(..., alias="endTime", description="统计结束时间戳 (ms)"),
    granularity: str = Query(
        "day",
        description="时间粒度：day（默认）或 hour",
    ),
    db: Session = Depends(deps.get_db),
) -> ApiResponse[SearchStats]:
    """
    用户搜索数据统计。
    """
    start_dt, end_dt = _ensure_time_range(start_time, end_time)
    granularity = granularity.lower()
    if granularity not in {"hour", "day", "week"}:
        raise HTTPException(status_code=400, detail="granularity 仅支持 hour/day/week")

    service = ViewerService(db)
    data = service.get_search_stats(start_dt, end_dt, granularity)
    return ApiResponse(data=data)


def _ensure_time_range(start_ms: int, end_ms: int) -> tuple[datetime, datetime]:
    """校验并转换毫秒时间戳为 datetime。"""
    if start_ms > end_ms:
        raise HTTPException(status_code=400, detail="startTime 不能晚于 endTime")
    start_dt = datetime.fromtimestamp(start_ms / 1000)
    end_dt = datetime.fromtimestamp(end_ms / 1000)
    return start_dt, end_dt


def _parse_dimensions(dimensions: Optional[str]) -> List[str]:
    if not dimensions:
        return []
    return [item.strip() for item in dimensions.split(",") if item.strip()]
