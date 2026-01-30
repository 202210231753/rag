"""评测流水线的组合与执行入口。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Sequence

from app.eval.core.interfaces import EvalContext, EvalResult, EvalSample, Runner


@dataclass
class EvalPipeline:
    """可组合的评测流水线。"""

    runners: List[Runner]
    fail_fast: bool = False
    on_error: Optional[Callable[[Runner, Exception], None]] = None
    on_runner_start: Optional[Callable[[Runner], None]] = None
    on_runner_end: Optional[Callable[[Runner, Sequence[EvalResult]], None]] = None

    async def run(
        self, samples: Iterable[EvalSample], context: Optional[EvalContext] = None
    ) -> List[EvalResult]:
        """顺序执行各个 runner，结果拼接输出。"""
        sample_list = list(samples)
        ctx = context or EvalContext()
        results: List[EvalResult] = []
        for runner in self.runners:
            if self.on_runner_start:
                self.on_runner_start(runner)
            try:
                runner_results = await runner.run(sample_list, context=ctx)
                results.extend(runner_results)
                if self.on_runner_end:
                    self.on_runner_end(runner, runner_results)
            except Exception as exc:
                if self.on_error:
                    self.on_error(runner, exc)
                if self.fail_fast:
                    raise
        return results
