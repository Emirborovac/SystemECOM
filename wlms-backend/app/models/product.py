import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("client_id", "sku", name="uq_products_client_sku"),
        UniqueConstraint("client_id", "barcode", name="uq_products_client_barcode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)

    barcode: Mapped[str | None] = mapped_column(String(128), nullable=True)
    uom: Mapped[str] = mapped_column(String(16), nullable=False, default="piece")  # piece/carton/pallet
    carton_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pallet_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)

    weight_kg: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dims_cm_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    lot_tracking_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    expiry_tracking_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", backref="products")
    client = relationship("Client", backref="products")


