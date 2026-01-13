"""link billing events to invoices (traceability)

Revision ID: 0012_billing_event_invoice_link
Revises: 0011_docs_pdf_refs
Create Date: 2026-01-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0012_billing_event_invoice_link"
down_revision = "0011_docs_pdf_refs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("billing_events", sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_billing_events_invoice_id", "billing_events", ["invoice_id"])
    op.create_foreign_key(
        "fk_billing_events_invoice_id",
        "billing_events",
        "invoices",
        ["invoice_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_billing_events_invoice_id", "billing_events", type_="foreignkey")
    op.drop_index("ix_billing_events_invoice_id", table_name="billing_events")
    op.drop_column("billing_events", "invoice_id")


