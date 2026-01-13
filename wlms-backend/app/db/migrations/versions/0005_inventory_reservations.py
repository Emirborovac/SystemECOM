"""inventory_reservations (per-outbound allocations)

Revision ID: 0005_inventory_reservations
Revises: 0004_outbound_picking
Create Date: 2026-01-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_inventory_reservations"
down_revision = "0004_outbound_picking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outbound_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outbound_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("qty_reserved", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("outbound_id", "product_id", "batch_id", "location_id", name="uq_inv_res_out_prod_batch_loc"),
    )
    op.create_index("ix_inventory_reservations_tenant_id", "inventory_reservations", ["tenant_id"])
    op.create_index("ix_inventory_reservations_outbound_id", "inventory_reservations", ["outbound_id"])
    op.create_index("ix_inventory_reservations_client_id", "inventory_reservations", ["client_id"])
    op.create_index("ix_inventory_reservations_warehouse_id", "inventory_reservations", ["warehouse_id"])
    op.create_index("ix_inventory_reservations_product_id", "inventory_reservations", ["product_id"])
    op.create_index("ix_inventory_reservations_batch_id", "inventory_reservations", ["batch_id"])
    op.create_index("ix_inventory_reservations_location_id", "inventory_reservations", ["location_id"])


def downgrade() -> None:
    op.drop_index("ix_inventory_reservations_location_id", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_batch_id", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_product_id", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_warehouse_id", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_client_id", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_outbound_id", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_tenant_id", table_name="inventory_reservations")
    op.drop_table("inventory_reservations")


