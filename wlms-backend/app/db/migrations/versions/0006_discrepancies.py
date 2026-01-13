"""discrepancy_reports

Revision ID: 0006_discrepancies
Revises: 0005_inventory_reservations
Create Date: 2026-01-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_discrepancies"
down_revision = "0005_inventory_reservations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discrepancy_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("system_qty", sa.Integer(), nullable=False),
        sa.Column("counted_qty", sa.Integer(), nullable=False),
        sa.Column("delta_qty", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_discrepancy_reports_tenant_id", "discrepancy_reports", ["tenant_id"])
    op.create_index("ix_discrepancy_reports_client_id", "discrepancy_reports", ["client_id"])
    op.create_index("ix_discrepancy_reports_warehouse_id", "discrepancy_reports", ["warehouse_id"])
    op.create_index("ix_discrepancy_reports_product_id", "discrepancy_reports", ["product_id"])
    op.create_index("ix_discrepancy_reports_batch_id", "discrepancy_reports", ["batch_id"])
    op.create_index("ix_discrepancy_reports_location_id", "discrepancy_reports", ["location_id"])


def downgrade() -> None:
    op.drop_index("ix_discrepancy_reports_location_id", table_name="discrepancy_reports")
    op.drop_index("ix_discrepancy_reports_batch_id", table_name="discrepancy_reports")
    op.drop_index("ix_discrepancy_reports_product_id", table_name="discrepancy_reports")
    op.drop_index("ix_discrepancy_reports_warehouse_id", table_name="discrepancy_reports")
    op.drop_index("ix_discrepancy_reports_client_id", table_name="discrepancy_reports")
    op.drop_index("ix_discrepancy_reports_tenant_id", table_name="discrepancy_reports")
    op.drop_table("discrepancy_reports")


