"""add product.pallet_qty

Revision ID: 0018_product_pallet_qty
Revises: 0017_client_vat_rate
Create Date: 2026-01-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0018_product_pallet_qty"
down_revision = "0017_client_vat_rate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("pallet_qty", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "pallet_qty")


