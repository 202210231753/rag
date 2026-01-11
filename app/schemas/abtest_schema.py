from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateExperimentRequest(BaseModel):
    experiment_id: str = Field(..., alias="experimentId")
    name: str
    observed_metrics: List[str] = Field(..., alias="observedMetrics")
    routing_variables: List[str] = Field(default_factory=list, alias="routingVariables")
    staged_weights: List[Dict[str, int]] = Field(default_factory=list, alias="stagedWeights")

    model_config = ConfigDict(populate_by_name=True)


class AdjustTrafficStageRequest(BaseModel):
    experiment_id: str = Field(..., alias="experimentId")
    target_stage_index: int = Field(..., alias="targetStageIndex")
    new_weights: Dict[str, int] = Field(..., alias="newWeights")

    model_config = ConfigDict(populate_by_name=True)


class CollectMetricRequest(BaseModel):
    experiment_id: str = Field(..., alias="experimentId")
    version: str
    metric_name: str = Field(..., alias="metricName")
    metric_value: float = Field(..., alias="metricValue")
    user_id: Optional[str] = Field(default=None, alias="userId")

    model_config = ConfigDict(populate_by_name=True)


class RunStatsRequest(BaseModel):
    experiment_id: str = Field(..., alias="experimentId")
    metric_name: str = Field(..., alias="metricName")
    version_a: str = Field(default="A", alias="versionA")
    version_b: str = Field(default="B", alias="versionB")
    discrete: bool = False

    model_config = ConfigDict(populate_by_name=True)


class StatsResult(BaseModel):
    experiment_id: str = Field(..., alias="experimentId")
    metric_name: str = Field(..., alias="metricName")
    test_type: str = Field(..., alias="testType")
    pvalue: float
    uplift: float

    model_config = ConfigDict(populate_by_name=True)


class RouteResult(BaseModel):
    experiment_id: str = Field(..., alias="experimentId")
    user_id: str = Field(..., alias="userId")
    version: str
    vars: str = ""
    routed_at: str = Field(..., alias="routedAt")

    model_config = ConfigDict(populate_by_name=True)


class ReportResult(BaseModel):
    experiment_id: str = Field(..., alias="experimentId")
    design_and_hypothesis: str = Field(..., alias="designAndHypothesis")
    execution_and_key_data: str = Field(..., alias="executionAndKeyData")
    analysis_and_statistics: str = Field(..., alias="analysisAndStatistics")
    conclusions_and_recommendations: str = Field(..., alias="conclusionsAndRecommendations")

    model_config = ConfigDict(populate_by_name=True)


class AnomalyPoint(BaseModel):
    version: str
    metric_name: str = Field(..., alias="metricName")
    window_mean: float = Field(..., alias="windowMean")
    baseline_mean: float = Field(..., alias="baselineMean")
    zscore: float
    is_anomaly: bool = Field(..., alias="isAnomaly")

    model_config = ConfigDict(populate_by_name=True)
