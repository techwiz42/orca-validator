"""Postgres-backed async persistence adapter for OrcaMachine snapshots.

Implements the orca_runtime_python persistence contract (save / load / exists) over
the `machine_snapshots` table. Mirrors revenue_cycle's machine_persistence.py.
"""
from typing import Any

from sqlalchemy import select

from backend.app.database import AsyncSessionLocal
from backend.models import MachineSnapshot


def _leaf_state(snapshot: dict[str, Any]) -> str:
    state = snapshot.get("state", "")
    try:
        from orca_runtime_python.types import StateValue
        return StateValue(state).leaf()
    except Exception:
        return str(state) if state else "unknown"


class PostgresMachinePersistence:
    async def save(self, run_id: str, snapshot: dict[str, Any]) -> None:
        async with AsyncSessionLocal() as db:
            row = (
                await db.execute(select(MachineSnapshot).where(MachineSnapshot.run_id == run_id))
            ).scalars().first()
            if row:
                row.snapshot_json = snapshot
                row.current_state = _leaf_state(snapshot)
                row.machine_name = snapshot.get("machine") or row.machine_name
            else:
                db.add(MachineSnapshot(
                    run_id=run_id,
                    machine_name=snapshot.get("machine") or "unknown",
                    current_state=_leaf_state(snapshot),
                    snapshot_json=snapshot,
                ))
            await db.commit()

    async def load(self, run_id: str) -> dict[str, Any] | None:
        async with AsyncSessionLocal() as db:
            row = (
                await db.execute(select(MachineSnapshot).where(MachineSnapshot.run_id == run_id))
            ).scalars().first()
            return row.snapshot_json if row else None

    async def exists(self, run_id: str) -> bool:
        return await self.load(run_id) is not None
