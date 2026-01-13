"""returns

Revision ID: 0008_returns
Revises: 0007_billing_invoices_files
Create Date: 2026-01-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0008_returns"
down_revision = "0007_billing_invoices_files"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "returns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_returns_tenant_id", "returns", ["tenant_id"])
    op.create_index("ix_returns_client_id", "returns", ["client_id"])
    op.create_index("ix_returns_warehouse_id", "returns", ["warehouse_id"])

    op.create_table(
        "return_lines",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("return_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("returns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("disposition", sa.String(length=16), nullable=False),
        sa.Column("to_location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_return_lines_return_id", "return_lines", ["return_id"])
    op.create_index("ix_return_lines_product_id", "return_lines", ["product_id"])
    op.create_index("ix_return_lines_batch_id", "return_lines", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_return_lines_batch_id", table_name="return_lines")
    op.drop_index("ix_return_lines_product_id", table_name="return_lines")
    op.drop_index("ix_return_lines_return_id", table_name="return_lines")
    op.drop_table("return_lines")

    op.drop_index("ix_returns_warehouse_id", table_name="returns")
    op.drop_index("ix_returns_client_id", table_name="returns")
    op.drop_index("ix_returns_tenant_id", table_name="returns")
    op.drop_table("returns")


