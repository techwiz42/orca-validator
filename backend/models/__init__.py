"""SQLAlchemy models for orca-validator."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner: Mapped[str] = mapped_column(String(255), index=True)  # bootstrap: API-key subject
    doc_type: Mapped[str] = mapped_column(String(64), index=True)  # e.g. "contract"
    filename: Mapped[str] = mapped_column(String(512))
    blob_ref: Mapped[str] = mapped_column(String(1024))
    # uploaded → queued → running → done → failed
    status: Mapped[str] = mapped_column(String(32), default="uploaded", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    runs: Mapped[list["ValidationRun"]] = relationship(back_populates="document")


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    machine_id: Mapped[str] = mapped_column(String(128))
    machine_version: Mapped[str] = mapped_column(String(64))
    machine_hash: Mapped[str] = mapped_column(String(128))  # attributes a run to an exact verified spec
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="runs")
    result: Mapped["ValidationResult | None"] = relationship(back_populates="run", uselist=False)


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("validation_runs.id"), unique=True, index=True)
    verdict: Mapped[str] = mapped_column(String(16))  # pass | fail | error
    final_state: Mapped[str] = mapped_column(String(128))
    reasons: Mapped[list] = mapped_column(JSONB, default=list)
    extracted_fields: Mapped[dict] = mapped_column(JSONB, default=dict)
    machine_context: Mapped[dict] = mapped_column(JSONB, default=dict)
    # AI-assisted layer (Together) — NOT part of the verified verdict.
    analysis: Mapped[dict] = mapped_column(JSONB, default=dict)        # structured contract analysis
    revised_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)  # proposed redline
    analysis_status: Mapped[str] = mapped_column(String(32), default="skipped")  # done|skipped|error
    # FSM the document itself expresses, extracted + ORCA-verified {orca_md, mermaid, verified, report}
    document_fsm: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    run: Mapped["ValidationRun"] = relationship(back_populates="result")


class MachineSnapshot(Base):
    """One row per persisted OrcaMachine instance (the ORCA persistence adapter target).

    run_id convention: '{entity_type}:{entity_id}' (entity_type == validation run id).
    """
    __tablename__ = "machine_snapshots"

    run_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    machine_name: Mapped[str] = mapped_column(String(128))
    current_state: Mapped[str] = mapped_column(String(128), index=True)
    snapshot_json: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
