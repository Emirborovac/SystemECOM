"""product_batches, inbound, inventory ledger/balances

Revision ID: 0003_inbound_inventory
Revises: 0002_warehouse_location_product
Create Date: 2026-01-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_inbound_inventory"
down_revision = "0002_warehouse_location_product"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_number", sa.String(length=64), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("product_id", "batch_number", "expiry_date", name="uq_product_batches_product_batch_expiry"),
    )
    op.create_index("ix_product_batches_product_id", "product_batches", ["product_id"])

    op.create_table(
        "inbound_shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference_number", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("supplier", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_inbound_shipments_tenant_id", "inbound_shipments", ["tenant_id"])
    op.create_index("ix_inbound_shipments_client_id", "inbound_shipments", ["client_id"])
    op.create_index("ix_inbound_shipments_warehouse_id", "inbound_shipments", ["warehouse_id"])
    op.create_index("ix_inbound_shipments_reference_number", "inbound_shipments", ["reference_number"])

    op.create_table(
        "inbound_lines",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("inbound_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inbound_shipments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expected_qty", sa.Integer(), nullable=True),
        sa.Column("received_qty", sa.Integer(), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_inbound_lines_inbound_id", "inbound_lines", ["inbound_id"])
    op.create_index("ix_inbound_lines_product_id", "inbound_lines", ["product_id"])
    op.create_index("ix_inbound_lines_batch_id", "inbound_lines", ["batch_id"])

    op.create_table(
        "inventory_balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("on_hand_qty", sa.Integer(), nullable=False),
        sa.Column("reserved_qty", sa.Integer(), nullable=False),
        sa.Column("available_qty", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "product_id", "batch_id", "location_id", name="uq_inv_bal_tenant_prod_batch_loc"),
    )
    op.create_index("ix_inventory_balances_tenant_id", "inventory_balances", ["tenant_id"])
    op.create_index("ix_inventory_balances_client_id", "inventory_balances", ["client_id"])
    op.create_index("ix_inventory_balances_warehouse_id", "inventory_balances", ["warehouse_id"])
    op.create_index("ix_inventory_balances_product_id", "inventory_balances", ["product_id"])
    op.create_index("ix_inventory_balances_batch_id", "inventory_balances", ["batch_id"])
    op.create_index("ix_inventory_balances_location_id", "inventory_balances", ["location_id"])

    op.create_table(
        "inventory_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("from_location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("to_location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("qty_delta", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("reference_type", sa.String(length=16), nullable=False),
        sa.Column("reference_id", sa.String(length=64), nullable=False),
        sa.Column("performed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_inventory_ledger_tenant_id", "inventory_ledger", ["tenant_id"])
    op.create_index("ix_inventory_ledger_client_id", "inventory_ledger", ["client_id"])
    op.create_index("ix_inventory_ledger_warehouse_id", "inventory_ledger", ["warehouse_id"])
    op.create_index("ix_inventory_ledger_product_id", "inventory_ledger", ["product_id"])
    op.create_index("ix_inventory_ledger_batch_id", "inventory_ledger", ["batch_id"])
    op.create_index("ix_inventory_ledger_from_location_id", "inventory_ledger", ["from_location_id"])
    op.create_index("ix_inventory_ledger_to_location_id", "inventory_ledger", ["to_location_id"])


def downgrade() -> None:
    op.drop_index("ix_inventory_ledger_to_location_id", table_name="inventory_ledger")
    op.drop_index("ix_inventory_ledger_from_location_id", table_name="inventory_ledger")
    op.drop_index("ix_inventory_ledger_batch_id", table_name="inventory_ledger")
    op.drop_index("ix_inventory_ledger_product_id", table_name="inventory_ledger")
    op.drop_index("ix_inventory_ledger_warehouse_id", table_name="inventory_ledger")
    op.drop_index("ix_inventory_ledger_client_id", table_name="inventory_ledger")
    op.drop_index("ix_inventory_ledger_tenant_id", table_name="inventory_ledger")
    op.drop_table("inventory_ledger")

    op.drop_index("ix_inventory_balances_location_id", table_name="inventory_balances")
    op.drop_index("ix_inventory_balances_batch_id", table_name="inventory_balances")
    op.drop_index("ix_inventory_balances_product_id", table_name="inventory_balances")
    op.drop_index("ix_inventory_balances_warehouse_id", table_name="inventory_balances")
    op.drop_index("ix_inventory_balances_client_id", table_name="inventory_balances")
    op.drop_index("ix_inventory_balances_tenant_id", table_name="inventory_balances")
    op.drop_table("inventory_balances")

    op.drop_index("ix_inbound_lines_batch_id", table_name="inbound_lines")
    op.drop_index("ix_inbound_lines_product_id", table_name="inbound_lines")
    op.drop_index("ix_inbound_lines_inbound_id", table_name="inbound_lines")
    op.drop_table("inbound_lines")

    op.drop_index("ix_inbound_shipments_reference_number", table_name="inbound_shipments")
    op.drop_index("ix_inbound_shipments_warehouse_id", table_name="inbound_shipments")
    op.drop_index("ix_inbound_shipments_client_id", table_name="inbound_shipments")
    op.drop_index("ix_inbound_shipments_tenant_id", table_name="inbound_shipments")
    op.drop_table("inbound_shipments")

    op.drop_index("ix_product_batches_product_id", table_name="product_batches")
    op.drop_table("product_batches")


