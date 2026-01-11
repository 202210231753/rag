from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.abtest_schema import (
    AdjustTrafficStageRequest,
    CollectMetricRequest,
    CreateExperimentRequest,
    RunStatsRequest,
)
from app.schemas.stats_schema import ApiResponse
from app.services.abtest_service import ABTestService


router = APIRouter()


@router.post("/experiments", response_model=ApiResponse[dict])
def create_experiment(
    req: CreateExperimentRequest,
    db: Session = Depends(deps.get_db),
) -> ApiResponse[dict]:
    service = ABTestService(db)
    data = service.create_experiment(
        experiment_id=req.experiment_id,
        name=req.name,
        observed_metrics=req.observed_metrics,
        routing_variables=req.routing_variables,
        staged_weights=req.staged_weights,
    )
    return ApiResponse(data=data)


@router.post("/experiments/{experiment_id}/start", response_model=ApiResponse[dict])
def start_experiment(
    experiment_id: str,
    db: Session = Depends(deps.get_db),
) -> ApiResponse[dict]:
    service = ABTestService(db)
    data = service.start_experiment(experiment_id)
    return ApiResponse(data=data)


@router.post("/experiments/adjust-stage", response_model=ApiResponse[dict])
def adjust_stage(
    req: AdjustTrafficStageRequest,
    db: Session = Depends(deps.get_db),
) -> ApiResponse[dict]:
    service = ABTestService(db)
    data = service.adjust_stage(
        experiment_id=req.experiment_id,
        target_stage_index=req.target_stage_index,
        new_weights=req.new_weights,
    )
    return ApiResponse(data=data)


@router.get("/route", response_model=ApiResponse[dict])
def route(
    experiment_id: str = Query(..., alias="experimentId"),
    user_id: str = Query(..., alias="userId"),
    vars: Optional[str] = Query(default=None, description="分流变量串，例如 a=1&b=2 或任意自定义字符串"),
    db: Session = Depends(deps.get_db),
) -> ApiResponse[dict]:
    service = ABTestService(db)
    data = service.route(experiment_id, user_id, vars or "")
    return ApiResponse(data=data)


@router.post("/metrics/collect", response_model=ApiResponse[dict])
def collect_metric(
    req: CollectMetricRequest,
    db: Session = Depends(deps.get_db),
) -> ApiResponse[dict]:
    service = ABTestService(db)
    data = service.collect_metric(
        experiment_id=req.experiment_id,
        version=req.version,
        metric_name=req.metric_name,
        metric_value=req.metric_value,
        user_id=req.user_id,
    )
    return ApiResponse(data=data)


@router.post("/analysis/run", response_model=ApiResponse[dict])
def run_analysis(
    req: RunStatsRequest,
    db: Session = Depends(deps.get_db),
) -> ApiResponse[dict]:
    service = ABTestService(db)
    data = service.run_analysis(
        experiment_id=req.experiment_id,
        metric_name=req.metric_name,
        version_a=req.version_a,
        version_b=req.version_b,
        discrete=req.discrete,
    )
    return ApiResponse(data=data)


@router.get("/monitor/anomalies", response_model=ApiResponse[list])
def monitor_anomalies(
    experiment_id: str = Query(..., alias="experimentId"),
    metric_name: str = Query(..., alias="metricName"),
    window_size: int = Query(50, alias="windowSize"),
    z_threshold: float = Query(3.0, alias="zThreshold"),
    db: Session = Depends(deps.get_db),
) -> ApiResponse[list]:
    service = ABTestService(db)
    data = service.monitor_anomalies(
        experiment_id=experiment_id,
        metric_name=metric_name,
        window_size=window_size,
        z_threshold=z_threshold,
    )
    return ApiResponse(data=data)


@router.post("/reports/{experiment_id}/generate", response_model=ApiResponse[dict])
def generate_report(
    experiment_id: str,
    db: Session = Depends(deps.get_db),
) -> ApiResponse[dict]:
    service = ABTestService(db)
    data = service.generate_report(experiment_id)
    return ApiResponse(data=data)


@router.get("/reports/{experiment_id}", response_model=ApiResponse[dict])
def get_report(
    experiment_id: str,
    db: Session = Depends(deps.get_db),
) -> ApiResponse[dict]:
    service = ABTestService(db)
    data = service.get_report(experiment_id) or {}
    return ApiResponse(data=data)
