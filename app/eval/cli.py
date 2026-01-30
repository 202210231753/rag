"""Eval CLI 入口。"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any, Dict

from app.eval.configs.loader import load_config
from app.eval.core.interfaces import EvalContext
from app.eval.datasets import load_samples
from app.eval.engines import build_engine
from app.eval.reports import build_reporter
from app.eval.runners.factory import build_pipeline


def _override_output_dir(config: Dict[str, Any], output_dir: str | None) -> None:
    if not output_dir:
        return
    project = config.get("project")
    if not isinstance(project, dict):
        project = {}
        config["project"] = project
    project["output_dir"] = output_dir


async def run_eval(config_path: str, output_dir: str | None = None) -> None:
    config = load_config(config_path)
    _override_output_dir(config, output_dir)

    project_cfg = config.get("project", {})
    data_cfg = config.get("data", {})
    engine_cfg = config.get("engine", {})

    samples = load_samples(
        path=str(data_cfg.get("path", "")),
        format=str(data_cfg.get("format", "jsonl")),
        encoding=str(data_cfg.get("encoding", "utf-8")),
        field_map=data_cfg.get("field_map"),
        list_fields=data_cfg.get("list_fields"),
        split=data_cfg.get("split"),
        filters=data_cfg.get("filters"),
        sample_limit=data_cfg.get("sample_limit"),
        shuffle=bool(data_cfg.get("shuffle", False)),
        shuffle_seed=int(data_cfg.get("shuffle_seed", 42)),
        deduplicate=bool(data_cfg.get("deduplicate", False)),
        dedup_key=str(data_cfg.get("dedup_key", "id")),
        validate=bool(data_cfg.get("validate", True)),
        on_validation_error=str(data_cfg.get("on_validation_error", "fail")),
        drop_empty_query=bool(data_cfg.get("drop_empty_query", True)),
    )

    engine = build_engine(config)
    pipeline = build_pipeline(config, engine)
    reporter = build_reporter(config)

    context = EvalContext(
        run_id=str(project_cfg.get("run_id") or project_cfg.get("run_name") or "dev"),
        engine_type=str(engine_cfg.get("type", "api")),
        tags=list(project_cfg.get("tags") or []),
        seed=project_cfg.get("seed"),
        extra={"config_path": config_path},
    )

    try:
        results = await pipeline.run(samples, context=context)
        output_dir = str(project_cfg.get("output_dir", "app/eval/outputs"))
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        reporter.write(results, output_dir)
    finally:
        await engine.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Eval pipeline runner")
    parser.add_argument(
        "--config",
        default="app/eval/configs/eval_config.yaml",
        help="配置文件路径 (YAML/JSON)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="覆盖输出目录",
    )
    args = parser.parse_args()
    asyncio.run(run_eval(args.config, args.output_dir))


if __name__ == "__main__":
    main()
