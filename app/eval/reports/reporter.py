"""评测报告输出实现。"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from app.eval.core.interfaces import EvalResult, Reporter


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except Exception:
        return None


def _percentile(values: Sequence[float], p: float) -> float:
    if not values:
        return 0.0
    if p <= 0:
        return values[0]
    if p >= 100:
        return values[-1]
    rank = int(math.ceil((p / 100.0) * len(values))) - 1
    rank = max(0, min(rank, len(values) - 1))
    return values[rank]


def _get_nested(mapping: Mapping[str, Any], path: str) -> Any:
    cur: Any = mapping
    for part in path.split("."):
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(part)
    return cur


def _extract_metadata(result: EvalResult) -> Dict[str, Any]:
    details = result.details or {}
    if isinstance(details, Mapping):
        metadata = details.get("metadata")
        if isinstance(metadata, Mapping):
            return dict(metadata)
        sample = details.get("sample")
        if isinstance(sample, Mapping):
            meta = sample.get("metadata")
            if isinstance(meta, Mapping):
                return dict(meta)
    return {}


def _group_key(result: EvalResult, fields: Sequence[str]) -> Tuple[Tuple[str, Any], ...]:
    if not fields:
        return tuple()
    details = result.details or {}
    metadata = _extract_metadata(result)
    values: List[Tuple[str, Any]] = []
    for field in fields:
        field = str(field)
        value: Any = None
        if field.startswith("metadata."):
            value = _get_nested(metadata, field.split(".", 1)[1])
        elif field.startswith("details."):
            value = _get_nested(details, field.split(".", 1)[1]) if isinstance(details, Mapping) else None
        elif field.startswith("sample."):
            sample = details.get("sample") if isinstance(details, Mapping) else None
            if isinstance(sample, Mapping):
                value = _get_nested(sample, field.split(".", 1)[1])
        else:
            # 兼容默认 metadata 域
            if isinstance(metadata, Mapping):
                value = _get_nested(metadata, field)
            if value is None and isinstance(details, Mapping):
                value = _get_nested(details, field)
        values.append((field, value))
    return tuple(values)


def _result_record(
    result: EvalResult,
    *,
    include_metadata: bool,
    save_raw_payload: bool,
) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "sample_id": result.sample_id,
        "stage": result.stage,
        "latency_ms": result.latency_ms,
        "engine_type": result.engine_type,
        "error": result.error,
    }
    for key, value in (result.metrics or {}).items():
        record[key] = value
    if include_metadata:
        meta = _extract_metadata(result)
        if meta:
            record["metadata"] = meta
    if result.details:
        record["details"] = result.details
    if save_raw_payload and result.raw_payload is not None:
        record["raw_payload"] = result.raw_payload
    return record


def _collect_metric_values(results: Sequence[EvalResult]) -> Dict[str, List[float]]:
    values: Dict[str, List[float]] = {}
    for result in results:
        for name, raw in (result.metrics or {}).items():
            val = _safe_float(raw)
            if val is None:
                continue
            values.setdefault(name, []).append(val)
    return values


def _aggregate_metrics(
    results: Sequence[EvalResult],
    percentiles: Sequence[int],
) -> Dict[str, Any]:
    values = _collect_metric_values(results)
    summary: Dict[str, Any] = {}
    for name, vals in values.items():
        if not vals:
            continue
        vals_sorted = sorted(vals)
        count = len(vals_sorted)
        mean = sum(vals_sorted) / float(count)
        entry: Dict[str, Any] = {
            "count": count,
            "mean": mean,
            "min": vals_sorted[0],
            "max": vals_sorted[-1],
        }
        for p in percentiles:
            entry[f"p{int(p)}"] = _percentile(vals_sorted, float(p))
        summary[name] = entry
    return summary


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _write_csv(path: Path, records: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: List[str] = []
    seen: set[str] = set()
    for record in records:
        for key in record.keys():
            if key in seen:
                continue
            seen.add(key)
            fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def _render_markdown(summary: Mapping[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Eval Report")
    lines.append("")
    total = summary.get("total", 0)
    errors = summary.get("errors", 0)
    lines.append(f"- total: {total}")
    lines.append(f"- errors: {errors}")
    lines.append("")

    metrics = summary.get("metrics", {})
    if metrics:
        lines.append("## Overall Metrics")
        lines.append("")
        headers = ["metric", "mean", "p50", "p90", "p95", "min", "max", "count"]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for name, entry in metrics.items():
            row = [
                name,
                f"{entry.get('mean', 0):.4f}",
                f"{entry.get('p50', 0):.4f}",
                f"{entry.get('p90', 0):.4f}",
                f"{entry.get('p95', 0):.4f}",
                f"{entry.get('min', 0):.4f}",
                f"{entry.get('max', 0):.4f}",
                str(entry.get("count", 0)),
            ]
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    by_stage = summary.get("by_stage", {})
    if by_stage:
        lines.append("## By Stage")
        for stage, payload in by_stage.items():
            lines.append(f"### {stage}")
            stage_metrics = payload.get("metrics", {})
            if not stage_metrics:
                lines.append("")
                continue
            headers = ["metric", "mean", "p50", "p90", "p95", "min", "max", "count"]
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for name, entry in stage_metrics.items():
                row = [
                    name,
                    f"{entry.get('mean', 0):.4f}",
                    f"{entry.get('p50', 0):.4f}",
                    f"{entry.get('p90', 0):.4f}",
                    f"{entry.get('p95', 0):.4f}",
                    f"{entry.get('min', 0):.4f}",
                    f"{entry.get('max', 0):.4f}",
                    str(entry.get("count", 0)),
                ]
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


@dataclass
class ReportConfig:
    formats: Sequence[str] = field(default_factory=lambda: ["json"])
    save_samples: bool = True
    save_errors: bool = True
    save_raw_payload: bool = False
    include_metadata: bool = True
    aggregate_by: Sequence[str] = field(default_factory=list)
    percentiles: Sequence[int] = field(default_factory=lambda: [50, 90, 95])
    sample_output_file: str = "samples.jsonl"
    summary_output_file: str = "summary.json"
    markdown_output_file: str = "report.md"


class EvalReporter(Reporter):
    """默认评测报告输出器。"""

    def __init__(self, config: Optional[ReportConfig] = None) -> None:
        self.config = config or ReportConfig()

    def write(self, results: Sequence[EvalResult], output_dir: str) -> None:
        cfg = self.config
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        errors = [r for r in results if r.error]
        total = len(results)

        summary: Dict[str, Any] = {
            "total": total,
            "errors": len(errors),
            "metrics": _aggregate_metrics(results, cfg.percentiles),
            "by_stage": {},
        }

        # by stage
        stage_groups: Dict[str, List[EvalResult]] = {}
        for result in results:
            stage = result.stage or "default"
            stage_groups.setdefault(stage, []).append(result)
        for stage, group in stage_groups.items():
            summary["by_stage"][stage] = {
                "count": len(group),
                "metrics": _aggregate_metrics(group, cfg.percentiles),
            }

        # by group fields
        if cfg.aggregate_by:
            grouped: Dict[str, List[EvalResult]] = {}
            for result in results:
                key_items = _group_key(result, cfg.aggregate_by)
                key_str = "|".join(f"{k}={v}" for k, v in key_items) if key_items else "all"
                grouped.setdefault(key_str, []).append(result)
            summary["by_group"] = {}
            for key, group in grouped.items():
                summary["by_group"][key] = {
                    "count": len(group),
                    "metrics": _aggregate_metrics(group, cfg.percentiles),
                }

        formats = {fmt.lower() for fmt in cfg.formats}

        if "json" in formats:
            _write_json(output_path / cfg.summary_output_file, summary)

        # sample records
        if cfg.save_samples:
            sample_results = results if cfg.save_errors else [r for r in results if not r.error]
            records = [
                _result_record(
                    r,
                    include_metadata=cfg.include_metadata,
                    save_raw_payload=cfg.save_raw_payload,
                )
                for r in sample_results
            ]
            if "json" in formats:
                _write_jsonl(output_path / cfg.sample_output_file, records)
            if "csv" in formats:
                _write_csv(output_path / "samples.csv", records)

        if "csv" in formats:
            # summary.csv
            summary_rows: List[Dict[str, Any]] = []
            for metric, entry in summary.get("metrics", {}).items():
                row = {"metric": metric}
                row.update(entry)
                summary_rows.append(row)
            _write_csv(output_path / "summary.csv", summary_rows)

        if "md" in formats:
            markdown = _render_markdown(summary)
            (output_path / cfg.markdown_output_file).write_text(markdown, encoding="utf-8")
