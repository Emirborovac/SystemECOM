"""add token_version to users

Revision ID: 0013_user_token_version
Revises: 0012_billing_event_invoice_link
Create Date: 2026-01-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0013_user_token_version"
down_revision = "0012_billing_event_invoice_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("users", "token_version")


