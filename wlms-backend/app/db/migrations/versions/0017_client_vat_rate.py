"""add client.vat_rate

Revision ID: 0017_client_vat_rate
Revises: 0016_user_username
Create Date: 2026-01-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0017_client_vat_rate"
down_revision = "0016_user_username"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("vat_rate", sa.Numeric(6, 4), nullable=False, server_default="0.17"))


def downgrade() -> None:
    op.drop_column("clients", "vat_rate")


