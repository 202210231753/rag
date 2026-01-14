from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """通用接口响应包装。"""

    code: int = 200
    msg: str = "success"
    data: T

    model_config = ConfigDict(populate_by_name=True)


class LabelValueRatio(BaseModel):
    label: str
    value: int
    ratio: float = Field(..., description="比例值，0-1 之间")

    model_config = ConfigDict(populate_by_name=True)


class LabelValue(BaseModel):
    label: str
    value: int

    model_config = ConfigDict(populate_by_name=True)


class UserProfileStats(BaseModel):
    total_users: int = Field(..., alias="totalUsers")
    new_users: int = Field(..., alias="newUsers")
    gender_dist: List[LabelValueRatio] = Field(default_factory=list, alias="genderDist")
    age_dist: List[LabelValue] = Field(default_factory=list, alias="ageDist")
    city_dist: List[LabelValueRatio] = Field(default_factory=list, alias="cityDist")

    model_config = ConfigDict(populate_by_name=True)


class BehaviorSummary(BaseModel):
    total_pv: int = Field(..., alias="totalPV")
    total_uv: int = Field(..., alias="totalUV")
    avg_duration: float = Field(..., alias="avgDuration")

    model_config = ConfigDict(populate_by_name=True)


class BehaviorTrend(BaseModel):
    dates: List[str]
    pv_values: List[int] = Field(..., alias="pvValues")
    uv_values: List[int] = Field(..., alias="uvValues")

    model_config = ConfigDict(populate_by_name=True)


class BehaviorRetention(BaseModel):
    day1: float
    day7: float

    model_config = ConfigDict(populate_by_name=True)


class UserBehaviorStats(BaseModel):
    summary: BehaviorSummary
    trend: BehaviorTrend
    retention: BehaviorRetention

    model_config = ConfigDict(populate_by_name=True)


class SearchTrendPoint(BaseModel):
    datetime: str
    count: int
    user_count: Optional[int] = Field(default=None, alias="userCount")

    model_config = ConfigDict(populate_by_name=True)


class SearchSummary(BaseModel):
    total_search_pv: int = Field(..., alias="totalSearchPv")
    total_search_uv: int = Field(..., alias="totalSearchUv")
    avg_search_per_user: float = Field(..., alias="avgSearchPerUser")

    model_config = ConfigDict(populate_by_name=True)


class SearchStats(BaseModel):
    summary: SearchSummary
    trend_list: List[SearchTrendPoint] = Field(..., alias="trendList")

    model_config = ConfigDict(populate_by_name=True)
