"""Validation worker — consumes the Redis queue with bounded concurrency.

Run as its own process/container: `python -m backend.pipeline.worker`. OCR + LLM are the
heavy bit, so concurrency is capped (WORKER_CONCURRENCY) and never unbounded — that boundedness
is what keeps the co-located droplet's DB pool from being starved.
"""
import asyncio
import logging

from backend.app.config import get_settings
from backend.queue import dequeue
from backend.pipeline.validate import run_validation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orca_worker")


async def _run_one(run_id, sem: asyncio.Semaphore) -> None:
    try:
        await run_validation(run_id)
    except Exception:  # noqa: BLE001 — never let one job kill the worker
        logger.exception("worker: run %s failed", run_id)
    finally:
        sem.release()


async def main() -> None:
    settings = get_settings()
    sem = asyncio.Semaphore(settings.WORKER_CONCURRENCY)
    inflight: set[asyncio.Task] = set()
    logger.info("worker started (concurrency=%d)", settings.WORKER_CONCURRENCY)
    while True:
        # Acquire a slot BEFORE pulling work: at most WORKER_CONCURRENCY jobs leave Redis at once,
        # the rest stay durably queued (a crash loses only the in-flight few, not the backlog).
        await sem.acquire()
        run_id = await dequeue(timeout=5)
        if run_id is None:
            sem.release()  # nothing queued — release and poll again
            continue
        task = asyncio.create_task(_run_one(run_id, sem))
        inflight.add(task)
        task.add_done_callback(inflight.discard)


if __name__ == "__main__":
    asyncio.run(main())
