"""OrcaBridge — process-level registry of OrcaMachine instances, one per run.

Emulates revenue_cycle's RCMOrcaBridge: machines restore from Postgres snapshots via
load_or_start(); snapshots auto-save after each transition. Keyed by run_id
"{doc_type}:{entity_id}" (entity_id == validation run id).
"""
import logging
from typing import Any

from orca_runtime_python import OrcaMachine

from machines import MACHINE_DEFS
from backend.orca.persistence import PostgresMachinePersistence
from backend.orca.registry import REGISTER_FNS

logger = logging.getLogger(__name__)


class OrcaBridge:
    def __init__(self) -> None:
        self._persistence = PostgresMachinePersistence()
        self._machines: dict[str, OrcaMachine] = {}

    def _run_id(self, doc_type: str, entity_id: str) -> str:
        return f"{doc_type}:{entity_id}"

    async def get_or_create(self, doc_type: str, entity_id: str, context: dict[str, Any]) -> OrcaMachine:
        run_id = self._run_id(doc_type, entity_id)
        if run_id in self._machines:
            if context:
                self._machines[run_id].context.update(context)
            return self._machines[run_id]

        existed = await self._persistence.exists(run_id)
        if not context and not existed:
            raise ValueError(f"Context is required to start a new machine for {run_id}")

        machine = OrcaMachine(
            definition=MACHINE_DEFS[doc_type],
            context=context,
            on_transition=None,
            persistence=self._persistence,
            run_id=run_id,
        )
        REGISTER_FNS[doc_type](machine)
        await machine.load_or_start()
        if context:
            machine.context.update(context)
        if not existed:
            # start() does not auto-save (only transitions do); persist the initial snapshot.
            await self._persistence.save(run_id, machine.snapshot())

        self._machines[run_id] = machine
        return machine

    async def send(
        self,
        doc_type: str,
        entity_id: str,
        event_name: str,
        payload: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ):
        machine = await self.get_or_create(doc_type, entity_id, context or {})
        result = await machine.send(event_name, payload or {})
        if not getattr(result, "taken", True):
            logger.warning(
                "Event %s not taken for %s:%s (state=%s, guard_failed=%s, error=%s)",
                event_name, doc_type, entity_id, machine.state,
                getattr(result, "guard_failed", None), getattr(result, "error", None),
            )
        return result, machine

    async def shutdown(self) -> None:
        for machine in self._machines.values():
            await machine.stop()
        self._machines.clear()


_bridge: OrcaBridge | None = None


def get_bridge() -> OrcaBridge:
    global _bridge
    if _bridge is None:
        _bridge = OrcaBridge()
    return _bridge
