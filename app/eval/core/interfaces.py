"""评测框架核心接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


@dataclass
class EvalSample:
    """统一评测样本结构。"""

    id: str
    query: str
    answers: Optional[List[str]] = None
    relevant_doc_ids: Optional[List[str]] = None
    relevant_texts: Optional[List[str]] = None
    rewrite: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    candidate_doc_ids: Optional[List[str]] = None
    candidate_texts: Optional[List[str]] = None
    contexts: Optional[List[str]] = None
    split: Optional[str] = None


@dataclass
class EvalResult:
    """单样本评测结果。"""

    sample_id: str
    metrics: Dict[str, float]
    details: Optional[Dict[str, Any]] = None
    stage: Optional[str] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None
    engine_type: Optional[str] = None


@dataclass
class EvalContext:
    """评测上下文，用于传递配置与全局信息。"""

    run_id: str = "dev"
    engine_type: str = "api"
    tags: List[str] = field(default_factory=list)
    seed: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """安全获取额外上下文信息。"""
        return self.extra.get(key, default)


class Engine(ABC):
    """评测引擎抽象接口（API / 内部调用 / 第三方）。"""

    @abstractmethod
    async def retrieve(self, query: str, top_n: int, recall_top_k: int) -> Mapping[str, Any]:
        """执行检索，返回原始响应结构。"""

    async def rerank(self, query: str, candidates: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        """执行重排（可选）。"""
        raise NotImplementedError

    async def rewrite(self, query: str) -> str:
        """执行 Query 改写（可选）。"""
        raise NotImplementedError

    async def generate(self, query: str, contexts: Sequence[str]) -> Mapping[str, Any]:
        """执行生成（可选）。"""
        raise NotImplementedError

    async def close(self) -> None:
        """释放资源（可选）。"""
        return None


class Metric(ABC):
    """指标计算接口。"""

    @abstractmethod
    def name(self) -> str:
        """指标名称。"""

    @abstractmethod
    def compute(self, sample: EvalSample, payload: Mapping[str, Any]) -> float:
        """计算指标分数。"""


class Runner(ABC):
    """评测流程执行接口。"""

    @abstractmethod
    async def run(self, samples: Iterable[EvalSample], context: Optional[EvalContext] = None) -> List[EvalResult]:
        """执行评测并返回结果列表。"""


class Reporter(ABC):
    """报告输出接口。"""

    @abstractmethod
    def write(self, results: Sequence[EvalResult], output_dir: str) -> None:
        """输出报告。"""


class Registry(ABC):
    """注册表接口，用于插件化发现。"""

    @abstractmethod
    def register(self, key: str, value: Any, *, override: bool = False) -> None:
        """注册对象。"""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """获取对象。"""

    @abstractmethod
    def list(self) -> List[str]:
        """列出已注册键。"""
