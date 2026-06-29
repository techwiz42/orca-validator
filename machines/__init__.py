"""Load + expose the verified ORCA validation machines (one per doc type)."""
from pathlib import Path

from orca_runtime_python import parse_orca_md

_here = Path(__file__).parent


def _load(filename: str):
    return parse_orca_md((_here / filename).read_text())


CONTRACT_VALIDATION_DEF = _load("contract_validation.orca.md")

# doc_type -> machine definition
MACHINE_DEFS = {
    "contract": CONTRACT_VALIDATION_DEF,
}
