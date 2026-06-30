"""Visit log — records the IP + time of each hit to the public site URL.

Recorded server-side by the web middleware (which sees the real client IP via nginx's
X-Forwarded-For / X-Real-IP). Read endpoint is API-key protected — visitor IPs are not public.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.deps import require_api_key
from backend.models import Visit

router = APIRouter(tags=["visits"])

# The real Next.js routes. Everything else is a probe / scanner hitting a non-existent path.
APP_PATHS = ("/", "/privacy", "/tos", "/visits")


class VisitIn(BaseModel):
    ip: str
    path: str = "/"
    user_agent: str | None = None


@router.post("/visits", status_code=201)
async def record_visit(
    body: VisitIn,
    subject: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    db.add(Visit(
        ip=body.ip[:64],
        path=(body.path or "/")[:512],
        user_agent=(body.user_agent or "")[:512] or None,
    ))
    await db.commit()
    return {"ok": True}


@router.get("/visits")
async def list_visits(
    limit: int = 500,
    app_only: bool = False,
    subject: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(5000, limit))
    q = select(Visit).order_by(Visit.hit_at.desc())
    if app_only:
        q = q.where(Visit.path.in_(APP_PATHS))   # filter probes out of the query, not just the view
    rows = (await db.execute(q.limit(limit))).scalars().all()
    total = (await db.execute(select(func.count()).select_from(Visit))).scalar() or 0
    app_total = (await db.execute(
        select(func.count()).select_from(Visit).where(Visit.path.in_(APP_PATHS))
    )).scalar() or 0
    unique = (await db.execute(select(func.count(func.distinct(Visit.ip))))).scalar() or 0
    return {
        "total": total,
        "app_total": app_total,
        "unique_ips": unique,
        "app_only": app_only,
        "showing": len(rows),
        "visits": [
            {
                "ip": v.ip,
                "path": v.path,
                "user_agent": v.user_agent,
                "hit_at": v.hit_at.isoformat() if v.hit_at else None,
            }
            for v in rows
        ],
    }
