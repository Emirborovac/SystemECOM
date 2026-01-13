"""attach PDF file refs to inbound/outbound/returns

Revision ID: 0011_docs_pdf_refs
Revises: 0010_auth_invites_reset_email_outbox
Create Date: 2026-01-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0011_docs_pdf_refs"
down_revision = "0010_auth_invites_reset_email_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inbound_shipments", sa.Column("receiving_pdf_file_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_inbound_shipments_receiving_pdf_file_id",
        "inbound_shipments",
        "files",
        ["receiving_pdf_file_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("outbound_orders", sa.Column("dispatch_pdf_file_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_outbound_orders_dispatch_pdf_file_id",
        "outbound_orders",
        "files",
        ["dispatch_pdf_file_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("returns", sa.Column("return_pdf_file_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_returns_return_pdf_file_id",
        "returns",
        "files",
        ["return_pdf_file_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_returns_return_pdf_file_id", "returns", type_="foreignkey")
    op.drop_column("returns", "return_pdf_file_id")

    op.drop_constraint("fk_outbound_orders_dispatch_pdf_file_id", "outbound_orders", type_="foreignkey")
    op.drop_column("outbound_orders", "dispatch_pdf_file_id")

    op.drop_constraint("fk_inbound_shipments_receiving_pdf_file_id", "inbound_shipments", type_="foreignkey")
    op.drop_column("inbound_shipments", "receiving_pdf_file_id")


