"""App-level LLM spend cap — a per-UTC-day token budget tracked in Redis.

A backstop *in addition to* the Together account-level spend limit (set that too). Best-effort:
on a Redis hiccup it fails open (allows the call) rather than blocking validation, and a small
overshoot under high concurrency is acceptable for a cost guard.
"""
import datetime
import logging

import redis.asyncio as redis

from backend.app.config import get_settings

logger = logging.getLogger(__name__)
_redis: redis.Redis | None = None


class BudgetExceeded(RuntimeError):
    pass


def _client() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _redis


def _key() -> str:
    return f"orca:llm:tokens:{datetime.datetime.utcnow().date().isoformat()}"


async def check_budget() -> None:
    s = get_settings()
    if s.TOGETHER_DAILY_TOKEN_BUDGET <= 0:
        return
    try:
        used = int(await _client().get(_key()) or 0)
    except Exception as e:  # noqa: BLE001 — fail open on Redis trouble
        logger.warning("LLM budget check failed (allowing): %s", e)
        return
    if used >= s.TOGETHER_DAILY_TOKEN_BUDGET:
        raise BudgetExceeded(
            f"daily LLM token budget reached ({used}/{s.TOGETHER_DAILY_TOKEN_BUDGET})")


async def record_usage(tokens: int) -> None:
    if tokens <= 0:
        return
    try:
        c = _client()
        await c.incrby(_key(), tokens)
        await c.expire(_key(), 172_800)  # keep ~2 days
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM budget record failed: %s", e)
