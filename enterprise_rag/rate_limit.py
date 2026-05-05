from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass


@dataclass
class Bucket:
    window_start: float
    count: int


_BUCKETS: dict[str, Bucket] = {}


def rate_limit_key(database_path: str, client_host: str, api_key: str | None) -> str:
    if api_key:
        digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
        return f"{database_path}:api:{digest}"
    return f"{database_path}:ip:{client_host}"


def allow_request(key: str, limit: int, now: float | None = None) -> tuple[bool, int]:
    if limit <= 0:
        return True, 0
    now = now or time.time()
    bucket = _BUCKETS.get(key)
    if bucket is None or now - bucket.window_start >= 60:
        _BUCKETS[key] = Bucket(window_start=now, count=1)
        return True, limit - 1
    if bucket.count >= limit:
        return False, 0
    bucket.count += 1
    return True, limit - bucket.count


def reset_rate_limits() -> None:
    _BUCKETS.clear()
