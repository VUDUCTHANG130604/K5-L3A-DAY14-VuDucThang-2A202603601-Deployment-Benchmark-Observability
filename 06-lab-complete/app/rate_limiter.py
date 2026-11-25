"""Redis-backed sliding window shared by all workers and replicas."""

from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

WINDOW_MS = 60_000

# Use Redis time and evaluate the limit and insertion in one atomic operation.
SLIDING_WINDOW = """
local window_ms = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local time = redis.call('TIME')
local now = tonumber(time[1]) * 1000 + math.floor(tonumber(time[2]) / 1000)

redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window_ms)
if redis.call('ZCARD', KEYS[1]) >= limit then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return math.ceil((tonumber(oldest[2]) + window_ms - now) / 1000)
end

redis.call('ZADD', KEYS[1], now, ARGV[3])
redis.call('PEXPIRE', KEYS[1], window_ms)
return 0
"""


def check_rate_limit(key: str) -> None:
    key_digest = sha256(key.encode()).hexdigest()
    retry_after = r.eval(
        SLIDING_WINDOW,
        1,
        f"agent:rate:{key_digest}",
        WINDOW_MS,
        settings.rate_limit_per_minute,
        uuid4().hex,
    )
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
