from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, List


@dataclass(frozen=True)
class TokenizerInfo:
    tokenizer_id: str
    name: str
    description: str


class Tokenizer:
    info: TokenizerInfo

    def is_available(self) -> bool:
        return True

    def tokenize(self, text: str) -> List[str]:
        raise NotImplementedError


class JiebaTokenizer(Tokenizer):
    info = TokenizerInfo(
        tokenizer_id="jieba",
        name="jieba（经典中文分词）",
        description="基于前缀词典 + HMM 的中文分词，适合通用场景",
    )

    def tokenize(self, text: str) -> List[str]:
        try:
            import jieba  # type: ignore
        except Exception as exc:
            raise RuntimeError("未安装 jieba，无法使用 jieba 分词器") from exc

        tokens = jieba.lcut(text, cut_all=False, HMM=True)
        return [t.strip() for t in tokens if t and t.strip()]

    def is_available(self) -> bool:
        try:
            import jieba  # type: ignore  # noqa: F401

            return True
        except Exception:
            return False


@lru_cache(maxsize=1)
def _get_hanlp_tokenizer() -> Any:
    try:
        import hanlp  # type: ignore
    except Exception as exc:
        raise RuntimeError("未安装 HanLP，无法使用 hanlp 分词器") from exc

    try:
        pretrained = hanlp.pretrained.tok
        model_id = getattr(pretrained, "FINE_ELECTRA_SMALL_ZH", None) or getattr(
            pretrained, "COARSE_ELECTRA_SMALL_ZH", None
        )
        if model_id:
            return hanlp.load(model_id)
    except Exception:
        pass

    try:
        return hanlp.load("tok/fine")
    except Exception:
        return hanlp.load("tok/coarse")


class HanLPTokenizer(Tokenizer):
    info = TokenizerInfo(
        tokenizer_id="hanlp",
        name="HanLP（深度学习分词）",
        description="HanLP 预训练分词模型（需本地已缓存模型文件）",
    )

    def tokenize(self, text: str) -> List[str]:
        tokenizer = _get_hanlp_tokenizer()
        result = tokenizer(text)

        if isinstance(result, list):
            if not result:
                return []
            if all(isinstance(item, str) for item in result):
                return [item.strip() for item in result if item and item.strip()]
            tokens: List[str] = []
            for item in result:
                if isinstance(item, list):
                    tokens.extend([str(x).strip() for x in item if str(x).strip()])
                else:
                    s = str(item).strip()
                    if s:
                        tokens.append(s)
            return tokens

        s = str(result).strip()
        return [s] if s else []

    def is_available(self) -> bool:
        try:
            import hanlp  # type: ignore  # noqa: F401

            return True
        except Exception:
            return False
