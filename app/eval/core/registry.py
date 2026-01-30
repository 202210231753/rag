"""简单注册表实现。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.eval.core.interfaces import Registry


class SimpleRegistry(Registry):
    """用于注册引擎、指标、报告器等插件。"""

    def __init__(self) -> None:
        self._items: Dict[str, Any] = {}

    def register(self, key: str, value: Any, *, override: bool = False) -> None:
        if not key:
            raise ValueError("注册键不能为空")
        if not override and key in self._items:
            raise KeyError(f"注册项已存在: {key}")
        self._items[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._items:
            return self._items[key]
        if default is not None:
            return default
        raise KeyError(f"未找到注册项: {key}")

    def list(self) -> List[str]:
        return sorted(self._items.keys())

    def exists(self, key: str) -> bool:
        return key in self._items
