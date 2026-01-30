"""LLM 判分器（用于生成与端到端指标）。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

try:
    from openai import AsyncOpenAI  # type: ignore
except Exception:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore


_JSON_RE = re.compile(r"\{.*\}", re.S)


@dataclass
class LLMJudgeConfig:
    provider: str = "openai"
    api_key: str = ""
    base_url: Optional[str] = None
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 512
    timeout_seconds: int = 30


class LLMJudge:
    """基于 OpenAI 兼容接口的 LLM Judge。"""

    def __init__(self, config: LLMJudgeConfig) -> None:
        if AsyncOpenAI is None:  # pragma: no cover
            raise RuntimeError("openai SDK 未安装，无法使用 LLMJudge")
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )

    async def score_generation(
        self,
        query: str,
        answer: str,
        contexts: Sequence[str],
        reference_answers: Optional[Sequence[str]] = None,
        *,
        metric_keys: Optional[Iterable[str]] = None,
    ) -> Dict[str, float]:
        keys = list(metric_keys or [
            "faithfulness",
            "answer_relevance",
            "answer_correctness",
            "hallucination_rate",
        ])
        data = await self._score(query, answer, contexts, reference_answers, keys)
        return {k: float(data.get(k, 0.0)) for k in keys}

    async def score_e2e(
        self,
        query: str,
        answer: str,
        contexts: Sequence[str],
        reference_answers: Optional[Sequence[str]] = None,
        *,
        metric_keys: Optional[Iterable[str]] = None,
    ) -> Dict[str, float]:
        keys = list(metric_keys or ["e2e_correctness", "e2e_faithfulness"])
        data = await self._score(query, answer, contexts, reference_answers, keys)
        return {k: float(data.get(k, 0.0)) for k in keys}

    async def _score(
        self,
        query: str,
        answer: str,
        contexts: Sequence[str],
        reference_answers: Optional[Sequence[str]],
        metric_keys: Sequence[str],
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(query, answer, contexts, reference_answers, metric_keys)
        response = await self.client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            messages=[
                {"role": "system", "content": "You are a strict evaluator. Output JSON only."},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content if response.choices else ""
        parsed = self._extract_json(content)
        if not isinstance(parsed, dict):
            raise RuntimeError(f"LLMJudge 输出解析失败: {content}")
        return parsed

    def _build_prompt(
        self,
        query: str,
        answer: str,
        contexts: Sequence[str],
        reference_answers: Optional[Sequence[str]],
        metric_keys: Sequence[str],
    ) -> str:
        lines = [
            "请基于上下文、问题与答案，对指定指标给出 0-1 之间的评分。",
            "输出 JSON，键必须严格等于以下列表：",
            ", ".join(metric_keys),
            "",
            f"问题: {query}",
            f"答案: {answer}",
            "",
            "上下文:",
        ]
        if contexts:
            for idx, ctx in enumerate(contexts, start=1):
                lines.append(f"[{idx}] {ctx}")
        else:
            lines.append("(none)")
        if reference_answers:
            lines.append("")
            lines.append("参考答案:")
            for idx, ans in enumerate(reference_answers, start=1):
                lines.append(f"[{idx}] {ans}")
        lines.append("")
        lines.append("请仅输出 JSON。")
        return "\n".join(lines)

    def _extract_json(self, content: str) -> Any:
        if not content:
            return None
        content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = _JSON_RE.search(content)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return None
        return None
