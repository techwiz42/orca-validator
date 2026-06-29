"""Maps a doc type to its verified machine definition + action registration."""
from machines import MACHINE_DEFS
from backend.orca.actions.contract_actions import register_contract_actions

# doc_type -> the function that binds the machine's computation-layer actions
REGISTER_FNS = {
    "contract": register_contract_actions,
}

# doc_type -> stable machine id (matches the *.orca.md filename stem)
MACHINE_IDS = {
    "contract": "contract_validation",
}


def supported_doc_types() -> list[str]:
    return sorted(set(MACHINE_DEFS) & set(REGISTER_FNS))
