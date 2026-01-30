"""Report 工厂：根据配置创建报告输出器。"""

from __future__ import annotations

from typing import Any, Mapping

from app.eval.reports.reporter import EvalReporter, ReportConfig


def _get_section(config: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = config.get(key, {})
    if isinstance(value, Mapping):
        return value
    return {}


def build_reporter(config: Mapping[str, Any]) -> EvalReporter:
    report_cfg = _get_section(config, "report")
    cfg = ReportConfig(
        formats=report_cfg.get("formats") or ["json"],
        save_samples=bool(report_cfg.get("save_samples", True)),
        save_errors=bool(report_cfg.get("save_errors", True)),
        save_raw_payload=bool(report_cfg.get("save_raw_payload", False)),
        include_metadata=bool(report_cfg.get("include_metadata", True)),
        aggregate_by=report_cfg.get("aggregate_by") or [],
        percentiles=report_cfg.get("percentiles") or [50, 90, 95],
        sample_output_file=str(report_cfg.get("sample_output_file", "samples.jsonl")),
        summary_output_file=str(report_cfg.get("summary_output_file", "summary.json")),
        markdown_output_file=str(report_cfg.get("markdown_output_file", "report.md")),
    )
    return EvalReporter(cfg)
