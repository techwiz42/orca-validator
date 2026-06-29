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
    async with sem:
        try:
            await run_validation(run_id)
        except Exception:  # noqa: BLE001 — never let one job kill the worker
            logger.exception("worker: run %s failed", run_id)


async def main() -> None:
    settings = get_settings()
    sem = asyncio.Semaphore(settings.WORKER_CONCURRENCY)
    inflight: set[asyncio.Task] = set()
    logger.info("worker started (concurrency=%d)", settings.WORKER_CONCURRENCY)
    while True:
        run_id = await dequeue(timeout=5)
        if run_id is None:
            continue
        task = asyncio.create_task(_run_one(run_id, sem))
        inflight.add(task)
        task.add_done_callback(inflight.discard)


if __name__ == "__main__":
    asyncio.run(main())
