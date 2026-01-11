import math
from typing import List


def mean(xs: List[float]) -> float:
    if not xs:
        return float("nan")
    return sum(xs) / len(xs)


def var(xs: List[float]) -> float:
    if not xs:
        return float("nan")
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def welch_t_test(a: List[float], b: List[float]) -> float:
    """Welch's t-test 的 p-value（用正态近似）。

    迁移自 python_rag/stats.py。
    """

    if len(a) < 2 or len(b) < 2:
        return float("nan")
    ma, mb = mean(a), mean(b)
    va, vb = var(a), var(b)
    na, nb = len(a), len(b)

    denom = va / na + vb / nb
    # 两组都无波动（方差为 0）时，welch 分母可能为 0
    # - 若均值相同：无法区分，p=1
    # - 若均值不同：差异为“确定性”，p=0
    if denom == 0:
        return 1.0 if ma == mb else 0.0

    _t = (ma - mb) / math.sqrt(denom)

    # df 保留以便未来扩展；当前用正态近似计算 p。
    _df = ((va / na + vb / nb) ** 2) / (
        (va * va) / (na * na * (na - 1)) + (vb * vb) / (nb * nb * (nb - 1))
    )

    z = abs(_t)
    return 2.0 * (1.0 - normal_cdf(z))
