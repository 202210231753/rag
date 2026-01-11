import hashlib
from typing import Dict, Optional


class ConsistentHashRing:
    """一致性哈希环（带权重的虚拟节点）。

    迁移自 python_rag/hash_ring.py。
    """

    def __init__(self, weights: Dict[str, int], virtual_nodes: int = 100):
        self.weights = dict(weights)
        self.virtual_nodes = virtual_nodes
        self.ring: Dict[int, str] = {}
        self.sorted_keys: list[int] = []
        self._build()

    def _h64(self, s: str) -> int:
        d = hashlib.sha256(s.encode("utf-8")).digest()
        h = 0
        for i in range(8):
            h = (h << 8) | d[i]
        return h & ((1 << 63) - 1)

    def _build(self) -> None:
        total = sum(self.weights.values()) or 1
        for version, weight in self.weights.items():
            vnode_count = max(1, round(weight / total * self.virtual_nodes))
            for i in range(vnode_count):
                key = f"{version}#{i}"
                self.ring[self._h64(key)] = version
        self.sorted_keys = sorted(self.ring.keys())

    def route(self, composite_key: str) -> Optional[str]:
        if not self.ring:
            return None
        h = self._h64(composite_key)
        idx = self._find_index(h)
        return self.ring[self.sorted_keys[idx]]

    def _find_index(self, h: int) -> int:
        lo, hi = 0, len(self.sorted_keys) - 1
        if h > self.sorted_keys[hi] or h <= self.sorted_keys[0]:
            return 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.sorted_keys[mid] < h:
                lo = mid + 1
            else:
                hi = mid - 1
        return lo
