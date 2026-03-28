"""配置加载器（支持 YAML/JSON）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_config(path: str) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    suffix = file_path.suffix.lower()
    if suffix in {".json"}:
        return json.loads(file_path.read_text(encoding="utf-8"))

    # 默认尝试 YAML
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("未安装 PyYAML，无法读取 YAML 配置") from exc

    return yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
