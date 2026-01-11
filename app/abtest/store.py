from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class Experiment:
    experiment_id: str
    name: str
    observed_metrics: List[str]
    routing_variables: List[str]
    stages: List[Dict[str, int]] = field(default_factory=list)
    status: str = "CONFIGURED"
    started_at: str | None = None


# 内存存储（与 python_rag 一致）。
experiments: Dict[str, Experiment] = {}

# 当前/上一版本哈希环参数缓存（避免存 ring 大对象；路由时即时构建）。
rings_current: Dict[str, Dict] = {}
rings_previous: Dict[str, Dict] = {}

# 已见用户：用于“扩大流量阶段”时保证老用户不翻桶。
seen_users: Dict[str, Set[str]] = {}

# 指标采集记录
metrics: List[Dict] = []

# 分流记录
routes: List[Dict] = []

# 报告缓存
reports: Dict[str, Dict] = {}
