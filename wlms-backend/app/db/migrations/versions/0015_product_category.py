"""add product.category

Revision ID: 0015_product_category
Revises: 0014_outbound_packing_slip
Create Date: 2026-01-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0015_product_category"
down_revision = "0014_outbound_packing_slip"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("category", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "category")


