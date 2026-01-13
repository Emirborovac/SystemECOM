"""add packing_json and packing_slip_file_id to outbound_orders

Revision ID: 0014_outbound_packing_slip
Revises: 0013_user_token_version
Create Date: 2026-01-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0014_outbound_packing_slip"
down_revision = "0013_user_token_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("outbound_orders", sa.Column("packing_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("outbound_orders", sa.Column("packing_slip_file_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_outbound_orders_packing_slip_file_id",
        "outbound_orders",
        "files",
        ["packing_slip_file_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_outbound_orders_packing_slip_file_id"), "outbound_orders", ["packing_slip_file_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_outbound_orders_packing_slip_file_id"), table_name="outbound_orders")
    op.drop_constraint("fk_outbound_orders_packing_slip_file_id", "outbound_orders", type_="foreignkey")
    op.drop_column("outbound_orders", "packing_slip_file_id")
    op.drop_column("outbound_orders", "packing_json")


