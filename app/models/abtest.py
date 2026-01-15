from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ABTestExperiment(Base):
    __tablename__ = "abtest_experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    observed_metrics: Mapped[list] = mapped_column(JSON)
    routing_variables: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="CONFIGURED")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ABTestStage(Base):
    __tablename__ = "abtest_stages"
    __table_args__ = (
        UniqueConstraint("experiment_id", "stage_index", name="uq_abtest_stage_exp_idx"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(String(128), index=True)
    stage_index: Mapped[int] = mapped_column(Integer)
    weights: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ABTestAssignment(Base):
    """用户分流结果（sticky assignment）。

    用于“分阶段扩大流量”时保证用户不翻桶。
    key = (experiment_id, user_id, vars)
    """

    __tablename__ = "abtest_assignments"
    __table_args__ = (
        UniqueConstraint("experiment_id", "user_id", "vars", name="uq_abtest_assign_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(String(128), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    vars: Mapped[str] = mapped_column(String(255), default="")
    version: Mapped[str] = mapped_column(String(64))
    stage_index: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ABTestRoute(Base):
    __tablename__ = "abtest_routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(String(128), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    vars: Mapped[str] = mapped_column(String(255), default="")
    version: Mapped[str] = mapped_column(String(64), index=True)
    routed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ABTestMetric(Base):
    __tablename__ = "abtest_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    metric_name: Mapped[str] = mapped_column(String(128), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ABTestReport(Base):
    __tablename__ = "abtest_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    design_and_hypothesis: Mapped[str] = mapped_column(Text)
    execution_and_key_data: Mapped[str] = mapped_column(Text)
    analysis_and_statistics: Mapped[str] = mapped_column(Text)
    conclusions_and_recommendations: Mapped[str] = mapped_column(Text)
    # 可选：大模型生成的终版实验报告全文
    llm_final_report: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
