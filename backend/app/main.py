"""orca-validator FastAPI app.

Lifespan enforces the verification gate (refuse to boot on an unverified machine) and,
for the MVP, creates tables (Alembic migrations are a follow-up task).
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

import backend.models  # noqa: F401  — register models for create_all
from backend.api import documents, health, machines
from backend.app.config import get_settings
from backend.app.database import Base, engine
from backend.app.state import VERIFIED_MACHINES
from backend.orca.verification import verify_machines_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orca_validator")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # BOOT GATE — refuse to start if any machine fails ORCA verification.
    verified = verify_machines_dir(settings.MACHINES_DIR)
    VERIFIED_MACHINES.clear()
    VERIFIED_MACHINES.update(verified)
    logger.info("Verified %d ORCA machine(s): %s", len(verified), ", ".join(sorted(verified)))

    # MVP: create tables. (Alembic migrations are task §0.4 / a follow-up.)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    await engine.dispose()


app = FastAPI(title="orca-validator", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(documents.router)
app.include_router(machines.router)
