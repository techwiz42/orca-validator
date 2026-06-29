import os
import sys

# Make the repo root importable (backend.*, machines.*) without an editable install.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup():
    """Run the verification gate (populates VERIFIED_MACHINES) and create tables once,
    on the shared session loop, for every DB-touching test."""
    from backend.app.config import get_settings
    from backend.app.database import Base, engine
    from backend.app.state import VERIFIED_MACHINES
    from backend.orca.verification import verify_machines_dir

    VERIFIED_MACHINES.update(verify_machines_dir(get_settings().MACHINES_DIR))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
