"""评测引擎工厂：根据配置自动创建引擎实例。"""

from __future__ import annotations

from typing import Any, Mapping

from app.eval.core.interfaces import Engine
from app.eval.engines.api_engine import ApiEngine
from app.eval.engines.internal_engine import InternalEngine
from app.eval.engines.ragas_engine import RagasEngine


def _get_section(config: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = config.get(key, {})
    if isinstance(value, Mapping):
        return value
    return {}


def build_engine(config: Mapping[str, Any]) -> Engine:
    """根据配置创建评测引擎。

    兼容两种传入方式：
    1) 完整配置字典（包含 engine/api/internal/ragas 段）
    2) 仅 engine 段（包含 type）+ 其它段缺失时使用默认值
    """
    if not isinstance(config, Mapping):
        raise ValueError("config must be a mapping")

    engine_cfg = _get_section(config, "engine")
    if not engine_cfg and "type" in config:
        engine_cfg = config  # 兼容仅传 engine 段

    engine_type = str(engine_cfg.get("type", "api")).lower()

    if engine_type == "api":
        api_cfg = _get_section(config, "api")
        return ApiEngine(
            base_url=str(api_cfg.get("base_url", "http://localhost:8010")),
            timeout_seconds=int(api_cfg.get("timeout_seconds", 30)),
            max_concurrency=int(api_cfg.get("max_concurrency", 10)),
            retries=int(api_cfg.get("retries", 2)),
            retry_backoff_seconds=float(api_cfg.get("retry_backoff_seconds", 0.2)),
            retry_on_status=api_cfg.get("retry_on_status"),
            verify_ssl=bool(api_cfg.get("verify_ssl", True)),
            circuit_breaker=api_cfg.get("circuit_breaker"),
            headers=api_cfg.get("headers"),
            endpoints=api_cfg.get("endpoints"),
        )

    if engine_type == "internal":
        internal_cfg = _get_section(config, "internal")
        return InternalEngine(
            search_gateway_path=internal_cfg.get("search_gateway_path") or None,
            lazy_init=bool(internal_cfg.get("lazy_init", False)),
        )

    if engine_type == "ragas":
        ragas_cfg = _get_section(config, "ragas")
        enabled = ragas_cfg.get("enabled", True)
        if enabled is False:
            raise ValueError("ragas engine is disabled by config")
        return RagasEngine(
            metrics=ragas_cfg.get("metrics") or [],
            llm_provider=str(ragas_cfg.get("llm_provider", "")),
            embedding_provider=str(ragas_cfg.get("embedding_provider", "")),
            batch_size=int(ragas_cfg.get("batch_size", 8)),
        )

    raise ValueError(f"unsupported engine type: {engine_type}")
