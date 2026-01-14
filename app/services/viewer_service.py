from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import BehaviorLog, SearchLog, UserProfile
from app.schemas.stats_schema import (
    BehaviorRetention,
    BehaviorSummary,
    BehaviorTrend,
    LabelValue,
    LabelValueRatio,
    SearchStats,
    SearchSummary,
    SearchTrendPoint,
    UserBehaviorStats,
    UserProfileStats,
)


class ViewerService:
    """数据查看服务：提供用户基础、行为和搜索统计。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_profile_stats(
        self,
        start_time: datetime,
        end_time: datetime,
        dimensions: List[str] | None = None,
    ) -> UserProfileStats:
        """用户基础数据统计。"""
        dimensions_set = set(dimensions or [])
        total_users = self.db.query(func.count(UserProfile.id)).scalar() or 0

        new_users = (
            self.db.query(func.count(UserProfile.id))
            .filter(UserProfile.signup_ts.between(start_time, end_time))
            .scalar()
            or 0
        )

        gender_dist: List[LabelValueRatio] = []
        if not dimensions_set or "gender" in dimensions_set:
            gender_rows = (
                self.db.query(UserProfile.gender, func.count(UserProfile.id))
                .group_by(UserProfile.gender)
                .all()
            )
            gender_dist = [
                LabelValueRatio(
                    label=gender,
                    value=count,
                    ratio=round(count / total_users, 2) if total_users else 0.0,
                )
                for gender, count in gender_rows
            ]

        age_dist: List[LabelValue] = []
        if not dimensions_set or "age" in dimensions_set:
            age_buckets: Dict[str, int] = {
                "18岁以下": 0,
                "18-25岁": 0,
                "26-35岁": 0,
                "35岁以上": 0,
            }
            for age, in self.db.query(UserProfile.age).all():
                if age < 18:
                    age_buckets["18岁以下"] += 1
                elif age <= 25:
                    age_buckets["18-25岁"] += 1
                elif age <= 35:
                    age_buckets["26-35岁"] += 1
                else:
                    age_buckets["35岁以上"] += 1
            age_dist = [LabelValue(label=label, value=value) for label, value in age_buckets.items()]

        city_dist: List[LabelValueRatio] = []
        if not dimensions_set or "city" in dimensions_set:
            city_rows = (
                self.db.query(UserProfile.city, func.count(UserProfile.id))
                .group_by(UserProfile.city)
                .order_by(func.count(UserProfile.id).desc())
                .all()
            )
            city_dist = [
                LabelValueRatio(
                    label=city or "未知",
                    value=count,
                    ratio=round(count / total_users, 2) if total_users else 0.0,
                )
                for city, count in city_rows
            ]

        return UserProfileStats(
            total_users=total_users,
            new_users=new_users,
            gender_dist=gender_dist,
            age_dist=age_dist,
            city_dist=city_dist,
        )

    def get_user_behavior_stats(
        self,
        start_time: datetime,
        end_time: datetime,
        granularity: str,
    ) -> UserBehaviorStats:
        """用户行为数据统计。"""
        filtered_logs = (
            self.db.query(BehaviorLog)
            .filter(BehaviorLog.timestamp.between(start_time, end_time))
            .all()
        )

        if not filtered_logs:
            empty_trend = BehaviorTrend(dates=[], pv_values=[], uv_values=[])
            empty_summary = BehaviorSummary(total_pv=0, total_uv=0, avg_duration=0.0)
            retention = BehaviorRetention(day1=0.0, day7=0.0)
            return UserBehaviorStats(summary=empty_summary, trend=empty_trend, retention=retention)

        total_pv = sum(log.pv for log in filtered_logs)
        total_uv = sum(log.uv for log in filtered_logs)
        avg_duration = round(
            sum(log.duration for log in filtered_logs) / len(filtered_logs), 2
        )

        trend_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"pv": 0, "uv": 0})
        for log in filtered_logs:
            label = self._format_time_label(log.timestamp, granularity)
            trend_map[label]["pv"] += log.pv
            trend_map[label]["uv"] += log.uv

        sorted_labels = sorted(trend_map.keys())
        trend = BehaviorTrend(
            dates=sorted_labels,
            pv_values=[trend_map[label]["pv"] for label in sorted_labels],
            uv_values=[trend_map[label]["uv"] for label in sorted_labels],
        )

        retention = self._calc_retention(trend)

        summary = BehaviorSummary(total_pv=total_pv, total_uv=total_uv, avg_duration=avg_duration)
        return UserBehaviorStats(summary=summary, trend=trend, retention=retention)

    def get_search_stats(
        self,
        start_time: datetime,
        end_time: datetime,
        granularity: str,
    ) -> SearchStats:
        """用户搜索数据统计。"""
        filtered_logs = (
            self.db.query(SearchLog)
            .filter(SearchLog.timestamp.between(start_time, end_time))
            .all()
        )

        if not filtered_logs:
            summary = SearchSummary(total_search_pv=0, total_search_uv=0, avg_search_per_user=0.0)
            return SearchStats(summary=summary, trend_list=[])

        total_search_pv = len(filtered_logs)
        unique_users = {log.user_id for log in filtered_logs}
        total_search_uv = len(unique_users)
        avg_per_user = round(total_search_pv / total_search_uv, 2) if total_search_uv else 0.0

        trend_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "users": set()})
        for log in filtered_logs:
            label = self._format_time_label(log.timestamp, granularity)
            trend_map[label]["count"] += 1
            trend_map[label]["users"].add(log.user_id)

        sorted_labels = sorted(trend_map.keys())
        trend_list = [
            SearchTrendPoint(
                datetime=label,
                count=trend_map[label]["count"],
                user_count=len(trend_map[label]["users"]),
            )
            for label in sorted_labels
        ]

        summary = SearchSummary(
            total_search_pv=total_search_pv,
            total_search_uv=total_search_uv,
            avg_search_per_user=avg_per_user,
        )
        return SearchStats(summary=summary, trend_list=trend_list)

    def _format_time_label(self, dt: datetime, granularity: str) -> str:
        """根据粒度格式化时间标签。"""
        granularity = granularity.lower()
        if granularity == "hour":
            return dt.strftime("%Y-%m-%d %H:00")
        if granularity == "week":
            year, week_num, _ = dt.isocalendar()
            return f"{year}-W{week_num:02d}"
        return dt.strftime("%Y-%m-%d")

    def _calc_retention(self, trend: BehaviorTrend) -> BehaviorRetention:
        """根据趋势数据粗略估算 day1/day7 留存。"""
        if not trend.dates:
            return BehaviorRetention(day1=0.0, day7=0.0)
        base_uv = trend.uv_values[0] if trend.uv_values else 0
        if base_uv == 0:
            return BehaviorRetention(day1=0.0, day7=0.0)

        day1_uv = trend.uv_values[1] if len(trend.uv_values) > 1 else 0
        day7_uv = trend.uv_values[6] if len(trend.uv_values) > 6 else trend.uv_values[-1]

        day1_ratio = round(min(day1_uv / base_uv, 1), 2) if base_uv else 0.0
        day7_ratio = round(min(day7_uv / base_uv, 1), 2) if base_uv else 0.0
        return BehaviorRetention(day1=day1_ratio, day7=day7_ratio)
