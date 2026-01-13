"""warehouses, zones, locations, products

Revision ID: 0002_warehouse_location_product
Revises: 0001_initial_core
Create Date: 2026-01-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_warehouse_location_product"
down_revision = "0001_initial_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "warehouses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_warehouses_tenant_id", "warehouses", ["tenant_id"])

    op.create_table(
        "warehouse_zones",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("zone_type", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_warehouse_zones_warehouse_id", "warehouse_zones", ["warehouse_id"])

    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_id", sa.Integer(), sa.ForeignKey("warehouse_zones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("barcode_value", sa.String(length=128), nullable=False),
        sa.Column("aisle", sa.String(length=32), nullable=True),
        sa.Column("rack", sa.String(length=32), nullable=True),
        sa.Column("level", sa.String(length=32), nullable=True),
        sa.Column("bin", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("warehouse_id", "code", name="uq_locations_warehouse_code"),
        sa.UniqueConstraint("warehouse_id", "barcode_value", name="uq_locations_warehouse_barcode"),
    )
    op.create_index("ix_locations_warehouse_id", "locations", ["warehouse_id"])
    op.create_index("ix_locations_zone_id", "locations", ["zone_id"])

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("barcode", sa.String(length=128), nullable=True),
        sa.Column("uom", sa.String(length=16), nullable=False),
        sa.Column("carton_qty", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.String(length=32), nullable=True),
        sa.Column("dims_cm_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("lot_tracking_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("expiry_tracking_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("client_id", "sku", name="uq_products_client_sku"),
        sa.UniqueConstraint("client_id", "barcode", name="uq_products_client_barcode"),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])
    op.create_index("ix_products_client_id", "products", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_products_client_id", table_name="products")
    op.drop_index("ix_products_tenant_id", table_name="products")
    op.drop_table("products")

    op.drop_index("ix_locations_zone_id", table_name="locations")
    op.drop_index("ix_locations_warehouse_id", table_name="locations")
    op.drop_table("locations")

    op.drop_index("ix_warehouse_zones_warehouse_id", table_name="warehouse_zones")
    op.drop_table("warehouse_zones")

    op.drop_index("ix_warehouses_tenant_id", table_name="warehouses")
    op.drop_table("warehouses")


