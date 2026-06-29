"""document_fsm on validation_results

Revision ID: 0003_document_fsm
Revises: 0002_ai_layer
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_document_fsm"
down_revision = "0002_ai_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("validation_results", sa.Column(
        "document_fsm", postgresql.JSONB(astext_type=sa.Text()),
        server_default="{}", nullable=False))


def downgrade() -> None:
    op.drop_column("validation_results", "document_fsm")
