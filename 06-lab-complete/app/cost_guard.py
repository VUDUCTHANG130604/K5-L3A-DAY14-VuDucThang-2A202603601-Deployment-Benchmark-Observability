"""Track the agent's daily LLM spend in Redis."""

from datetime import datetime, time, timedelta, timezone

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

# USD per 1,000 mock model tokens.
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006


def check_budget() -> None:
    today = datetime.now(timezone.utc).date()
    spent = float(r.get(f"agent:cost:{today.isoformat()}") or 0)
    if spent >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exceeded")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    cost = (
        input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K
    ) / 1000
    today = datetime.now(timezone.utc).date()
    reset = datetime.combine(today + timedelta(days=1), time.min, tzinfo=timezone.utc)
    key = f"agent:cost:{today.isoformat()}"

    with r.pipeline() as transaction:
        transaction.incrbyfloat(key, cost)
        transaction.expireat(key, reset)
        transaction.execute()
    return cost
