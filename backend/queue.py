"""Redis-backed validation job queue.

The MVP API path uses FastAPI BackgroundTasks (in-process). When USE_REDIS_QUEUE is set,
the API enqueues run ids here instead and the dedicated worker (pipeline/worker.py) consumes
them — the production shape, so slow OCR/LLM work never rides on an API worker.
"""
from uuid import UUID

import redis.asyncio as redis
from redis.exceptions import TimeoutError as RedisTimeoutError

from backend.app.config import get_settings

_QUEUE_KEY = "orca:validation:queue"
_redis: redis.Redis | None = None


def _client() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _redis


async def enqueue(run_id: UUID) -> None:
    await _client().lpush(_QUEUE_KEY, str(run_id))


async def dequeue(timeout: int = 5) -> UUID | None:
    try:
        item = await _client().brpop(_QUEUE_KEY, timeout=timeout)
    except RedisTimeoutError:
        # Blocking-pop read window elapsed with nothing queued — the client read-timeout fires
        # alongside the server-side BRPOP timeout. Treat as "nothing dequeued", not an error.
        return None
    if not item:
        return None
    _, run_id = item
    return UUID(run_id)
