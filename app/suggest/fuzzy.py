from __future__ import annotations


def levenshtein_distance_limited(a: str, b: str, max_dist: int) -> int | None:
    """
    Levenshtein 编辑距离（限制最大距离，超过则早停返回 None）。

    说明：
    - 仅用于小候选池纠错，强调简单与可控。
    - 复杂度 O(len(a)*len(b))，但通过 max_dist 约束做剪枝。
    """
    if max_dist < 0:
        return None

    if a == b:
        return 0

    la = len(a)
    lb = len(b)
    if abs(la - lb) > max_dist:
        return None

    # 确保 b 更短以减少内存
    if lb > la:
        a, b = b, a
        la, lb = lb, la

    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur0 = i
        cur = [cur0] + [0] * lb
        min_in_row = cur0
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ca == b[j - 1] else 1
            cur[j] = min(
                prev[j] + 1,        # 删除
                cur[j - 1] + 1,     # 插入
                prev[j - 1] + cost  # 替换
            )
            if cur[j] < min_in_row:
                min_in_row = cur[j]

        if min_in_row > max_dist:
            return None
        prev = cur

    dist = prev[lb]
    return dist if dist <= max_dist else None

