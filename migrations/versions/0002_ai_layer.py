"""ai-assisted analysis layer on validation_results

Revision ID: 0002_ai_layer
Revises: 4e423202c85f
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_ai_layer"
down_revision = "4e423202c85f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("validation_results", sa.Column(
        "analysis", postgresql.JSONB(astext_type=sa.Text()),
        server_default="{}", nullable=False))
    op.add_column("validation_results", sa.Column(
        "revised_markdown", sa.Text(), nullable=True))
    op.add_column("validation_results", sa.Column(
        "analysis_status", sa.String(length=32), server_default="skipped", nullable=False))


def downgrade() -> None:
    op.drop_column("validation_results", "analysis_status")
    op.drop_column("validation_results", "revised_markdown")
    op.drop_column("validation_results", "analysis")
