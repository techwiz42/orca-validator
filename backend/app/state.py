"""Process-level state populated at boot (after the verification gate runs)."""

# machine filename (e.g. "contract_validation.orca.md") -> content hash, for verified machines.
VERIFIED_MACHINES: dict[str, str] = {}
