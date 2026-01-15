from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_keyword(keyword: str) -> str:
    """
    关键词规范化（用于热搜计数与榜单合并）

    规则（按你确认的需求做最小化处理）：
    - 去除首尾空白、压缩连续空白为单空格
    - 英文大小写统一：使用 casefold()
    """
    if not keyword:
        return ""
    compact = _WHITESPACE_RE.sub(" ", keyword.strip())
    return compact.casefold()

