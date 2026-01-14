from __future__ import annotations

import time
from typing import Any, Optional


class FakePipeline:
    def __init__(self, redis: "FakeRedis"):
        self._redis = redis
        self._ops: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def smembers(self, key: str) -> "FakePipeline":
        self._ops.append(("smembers", (key,), {}))
        return self

    def hgetall(self, key: str) -> "FakePipeline":
        self._ops.append(("hgetall", (key,), {}))
        return self

    def hmget(self, key: str, keys: list[str]) -> "FakePipeline":
        self._ops.append(("hmget", (key, keys), {}))
        return self

    def hdel(self, key: str, field: str) -> "FakePipeline":
        self._ops.append(("hdel", (key, field), {}))
        return self

    def zscore(self, key: str, member: str) -> "FakePipeline":
        self._ops.append(("zscore", (key, member), {}))
        return self

    def zincrby(self, key: str, amount: float, member: str) -> "FakePipeline":
        self._ops.append(("zincrby", (key, amount, member), {}))
        return self

    async def execute(self) -> list[Any]:
        results: list[Any] = []
        for name, args, kwargs in self._ops:
            func = getattr(self._redis, name)
            results.append(await func(*args, **kwargs))
        self._ops.clear()
        return results


class FakeRedis:
    """
    进程内 Redis 最小实现（覆盖热搜/输入提示测试所需命令）

    目的：在无法建立 socket 的环境中做集成级验证，不依赖真实 Redis。
    """

    def __init__(self):
        self._strings: dict[str, tuple[str, Optional[float]]] = {}
        self._sets: dict[str, set[str]] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._zsets: dict[str, dict[str, float]] = {}
        self._lists: dict[str, list[str]] = {}

    def pipeline(self) -> FakePipeline:
        return FakePipeline(self)

    async def ping(self) -> str:
        return "PONG"

    async def flushdb(self) -> bool:
        self._strings.clear()
        self._sets.clear()
        self._hashes.clear()
        self._zsets.clear()
        self._lists.clear()
        return True

    async def set(self, key: str, value: str, *, nx: bool = False, ex: Optional[int] = None):
        now = time.time()
        if nx:
            existing = self._strings.get(key)
            if existing is not None:
                _, expire_at = existing
                if expire_at is None or expire_at > now:
                    return None
        expire_at = (now + ex) if ex else None
        self._strings[key] = (str(value), expire_at)
        return True

    async def get(self, key: str) -> Optional[str]:
        now = time.time()
        existing = self._strings.get(key)
        if existing is None:
            return None
        value, expire_at = existing
        if expire_at is not None and expire_at <= now:
            del self._strings[key]
            return None
        return value

    async def delete(self, key: str) -> int:
        removed = 0
        for store in (self._strings, self._sets, self._hashes, self._zsets, self._lists):
            if key in store:
                del store[key]
                removed += 1
        return removed

    async def sadd(self, key: str, *members: str) -> int:
        s = self._sets.setdefault(key, set())
        before = len(s)
        for m in members:
            if m:
                s.add(str(m))
        return len(s) - before

    async def srem(self, key: str, *members: str) -> int:
        s = self._sets.setdefault(key, set())
        removed = 0
        for m in members:
            if m in s:
                s.remove(m)
                removed += 1
        return removed

    async def smembers(self, key: str) -> set[str]:
        return set(self._sets.get(key, set()))

    async def hset(self, key: str, field: str, value: str) -> int:
        h = self._hashes.setdefault(key, {})
        existed = 1 if field in h else 0
        h[str(field)] = str(value)
        return 0 if existed else 1

    async def hget(self, key: str, field: str) -> Optional[str]:
        return self._hashes.get(key, {}).get(field)

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._hashes.get(key, {}))

    async def hmget(self, key: str, keys: list[str]) -> list[Optional[str]]:
        h = self._hashes.get(key, {})
        return [h.get(k) for k in keys]

    async def hdel(self, key: str, field: str) -> int:
        h = self._hashes.get(key, {})
        if field in h:
            del h[field]
            return 1
        return 0

    async def zscore(self, key: str, member: str) -> Optional[float]:
        return self._zsets.get(key, {}).get(member)

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        z = self._zsets.setdefault(key, {})
        added = 0
        for member, score in (mapping or {}).items():
            if member not in z:
                added += 1
            z[str(member)] = float(score)
        return added

    async def zincrby(self, key: str, amount: float, member: str) -> float:
        z = self._zsets.setdefault(key, {})
        z[member] = float(z.get(member, 0.0)) + float(amount)
        return float(z[member])

    async def zrevrange(self, key: str, start: int, end: int, *, withscores: bool = False):
        z = self._zsets.get(key, {})
        items = sorted(z.items(), key=lambda x: (-x[1], x[0]))
        sliced = items[start:] if end < 0 else items[start : end + 1]
        if withscores:
            return [(k, float(v)) for k, v in sliced]
        return [k for k, _ in sliced]

    async def zrangebylex(self, key: str, min_lex: str, max_lex: str, *, start: int = 0, num: Optional[int] = None):
        z = self._zsets.get(key, {})
        members = sorted(z.keys())
        filtered = [m for m in members if _lex_in_range(m, min_lex, max_lex)]
        if start < 0:
            start = 0
        if num is None:
            return filtered[start:]
        return filtered[start : start + num]

    async def zunionstore(self, dest: str, keys, aggregate: str | None = None):
        if aggregate not in (None, "sum"):
            raise NotImplementedError("当前仅支持默认 sum 聚合")

        if isinstance(keys, dict):
            if len(keys) != 1:
                raise NotImplementedError("当前仅支持单个 zset 的 zunionstore")
            (src, weight), = list(keys.items())
        else:
            if len(keys) != 1:
                raise NotImplementedError("当前仅支持单个 zset 的 zunionstore")
            src = keys[0]
            weight = 1.0

        weight = float(weight)
        src_z = self._zsets.get(src, {})
        self._zsets[dest] = {k: float(v) * weight for k, v in src_z.items()}
        return len(self._zsets[dest])

    async def rename(self, src: str, dest: str) -> bool:
        if src in self._zsets:
            self._zsets[dest] = self._zsets[src]
            del self._zsets[src]
            return True
        raise KeyError(src)

    async def lpush(self, key: str, *values: str) -> int:
        lst = self._lists.setdefault(key, [])
        for v in values:
            lst.insert(0, str(v))
        return len(lst)

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        lst = self._lists.get(key, [])
        n = len(lst)
        s = _normalize_index(start, n)
        e = _normalize_index(end, n)
        if e < s:
            self._lists[key] = []
            return True
        self._lists[key] = lst[s : e + 1]
        return True

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        lst = self._lists.get(key, [])
        if not lst:
            return []
        n = len(lst)
        s = _normalize_index(start, n)
        e = _normalize_index(end, n)
        if e < s:
            return []
        return lst[s : e + 1]

    async def eval(self, script: str, numkeys: int, *args):
        """
        仅实现 hot_search incr 脚本：HGET boost -> ZINCRBY hot_list
        """
        if numkeys != 2:
            raise NotImplementedError("仅支持 2 个 key 的 eval")
        boost_key, hot_key, keyword, base_increment = args
        boost = await self.hget(str(boost_key), str(keyword))
        if boost is None:
            boost = "1"
        delta = float(base_increment) * float(boost)
        return await self.zincrby(str(hot_key), delta, str(keyword))


class FakeRedisClient:
    def __init__(self, client: FakeRedis):
        self._client = client

    @property
    def client(self) -> FakeRedis:
        return self._client


def _normalize_index(index: int, length: int) -> int:
    if index < 0:
        index = length + index
    if index < 0:
        return 0
    if index >= length:
        return length - 1
    return index


def _parse_lex_bound(bound: str) -> tuple[str | None, bool]:
    if bound == "-":
        return None, True
    if bound == "+":
        return None, True
    if not bound:
        return "", True
    if bound[0] == "[":
        return bound[1:], True
    if bound[0] == "(":
        return bound[1:], False
    return bound, True


def _lex_in_range(value: str, min_lex: str, max_lex: str) -> bool:
    min_v, min_inclusive = _parse_lex_bound(min_lex)
    max_v, max_inclusive = _parse_lex_bound(max_lex)

    if min_v is not None:
        if value < min_v or (not min_inclusive and value == min_v):
            return False
    if max_v is not None:
        if value > max_v or (not max_inclusive and value == max_v):
            return False
    return True

