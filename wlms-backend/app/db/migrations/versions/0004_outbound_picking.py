"""outbound orders + picking tasks

Revision ID: 0004_outbound_picking
Revises: 0003_inbound_inventory
Create Date: 2026-01-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_outbound_picking"
down_revision = "0003_inbound_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbound_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_number", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("destination_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requested_ship_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbound_orders_tenant_id", "outbound_orders", ["tenant_id"])
    op.create_index("ix_outbound_orders_client_id", "outbound_orders", ["client_id"])
    op.create_index("ix_outbound_orders_warehouse_id", "outbound_orders", ["warehouse_id"])
    op.create_index("ix_outbound_orders_order_number", "outbound_orders", ["order_number"])

    op.create_table(
        "outbound_lines",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("outbound_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outbound_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_qty", sa.Integer(), nullable=False),
        sa.Column("reserved_qty", sa.Integer(), nullable=False),
        sa.Column("picked_qty", sa.Integer(), nullable=False),
        sa.Column("batch_policy", sa.String(length=16), nullable=True),
    )
    op.create_index("ix_outbound_lines_outbound_id", "outbound_lines", ["outbound_id"])
    op.create_index("ix_outbound_lines_product_id", "outbound_lines", ["product_id"])

    op.create_table(
        "picking_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("outbound_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outbound_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_picking_tasks_outbound_id", "picking_tasks", ["outbound_id"])
    op.create_index("ix_picking_tasks_assigned_to_user_id", "picking_tasks", ["assigned_to_user_id"])

    op.create_table(
        "picking_task_lines",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("picking_task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("picking_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("from_location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("qty_to_pick", sa.Integer(), nullable=False),
        sa.Column("qty_picked", sa.Integer(), nullable=False),
    )
    op.create_index("ix_picking_task_lines_picking_task_id", "picking_task_lines", ["picking_task_id"])
    op.create_index("ix_picking_task_lines_product_id", "picking_task_lines", ["product_id"])
    op.create_index("ix_picking_task_lines_batch_id", "picking_task_lines", ["batch_id"])
    op.create_index("ix_picking_task_lines_from_location_id", "picking_task_lines", ["from_location_id"])


def downgrade() -> None:
    op.drop_index("ix_picking_task_lines_from_location_id", table_name="picking_task_lines")
    op.drop_index("ix_picking_task_lines_batch_id", table_name="picking_task_lines")
    op.drop_index("ix_picking_task_lines_product_id", table_name="picking_task_lines")
    op.drop_index("ix_picking_task_lines_picking_task_id", table_name="picking_task_lines")
    op.drop_table("picking_task_lines")

    op.drop_index("ix_picking_tasks_assigned_to_user_id", table_name="picking_tasks")
    op.drop_index("ix_picking_tasks_outbound_id", table_name="picking_tasks")
    op.drop_table("picking_tasks")

    op.drop_index("ix_outbound_lines_product_id", table_name="outbound_lines")
    op.drop_index("ix_outbound_lines_outbound_id", table_name="outbound_lines")
    op.drop_table("outbound_lines")

    op.drop_index("ix_outbound_orders_order_number", table_name="outbound_orders")
    op.drop_index("ix_outbound_orders_warehouse_id", table_name="outbound_orders")
    op.drop_index("ix_outbound_orders_client_id", table_name="outbound_orders")
    op.drop_index("ix_outbound_orders_tenant_id", table_name="outbound_orders")
    op.drop_table("outbound_orders")


