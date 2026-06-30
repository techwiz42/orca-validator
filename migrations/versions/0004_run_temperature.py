"""temperature on validation_runs

Revision ID: 0004_run_temperature
Revises: 0003_document_fsm
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_run_temperature"
down_revision = "0003_document_fsm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("validation_runs", sa.Column(
        "temperature", sa.Float(), server_default="0.03", nullable=False))


def downgrade() -> None:
    op.drop_column("validation_runs", "temperature")
