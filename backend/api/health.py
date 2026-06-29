import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    checks = {"postgres": "ok"}
    try:
        r = redis.from_url(get_settings().REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:  # noqa: BLE001 — report degraded, don't 500 the probe
        checks["redis"] = f"unavailable: {e}"
    return {"status": "ok", "checks": checks}
