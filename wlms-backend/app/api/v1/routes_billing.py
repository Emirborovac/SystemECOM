import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_admin_or_supervisor
from app.core.config import settings
from app.db.session import get_db
from app.models.billing import BillingEvent, Invoice, InvoiceLine, PriceList
from app.models.client import Client
from app.models.file import File
from app.models.user import User
from app.schemas.billing import (
    BillingEventOut,
    GenerateInvoiceBody,
    InvoiceLineOut,
    InvoiceOut,
    PriceListOut,
    PriceListUpsert,
    RunDailyStorageBody,
)
from app.services import billing_service
from app.services.document_service import render_invoice_pdf
from app.services.storage_service import save_bytes
from app.services.audit_service import audit_log
from app.services.notification_service import queue_invoice_issued_email

router = APIRouter(tags=["billing", "invoices"])


def _invoice_out(i: Invoice) -> InvoiceOut:
    return InvoiceOut(
        id=i.id,
        client_id=i.client_id,
        period_start=i.period_start,
        period_end=i.period_end,
        status=i.status,
        currency=i.currency,
        subtotal=float(i.subtotal),
        tax_total=float(i.tax_total),
        total=float(i.total),
        pdf_file_id=i.pdf_file_id,
    )


@router.get("/clients/{client_id}/price-list", response_model=PriceListOut)
def get_price_list(
    client_id: str, db: Session = Depends(get_db), _user: User = Depends(require_admin_or_supervisor)
) -> PriceListOut:
    try:
        cid = uuid.UUID(client_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    client = db.scalar(select(Client).where(Client.id == cid, Client.tenant_id == _user.tenant_id))
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    pl = db.scalar(select(PriceList).where(PriceList.client_id == cid).order_by(PriceList.effective_from.desc()))
    if pl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return PriceListOut(id=pl.id, client_id=pl.client_id, effective_from=pl.effective_from, rules_json=pl.rules_json)


@router.put("/clients/{client_id}/price-list", response_model=PriceListOut)
def upsert_price_list(
    client_id: str,
    payload: PriceListUpsert,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin_or_supervisor),
) -> PriceListOut:
    try:
        cid = uuid.UUID(client_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    client = db.scalar(select(Client).where(Client.id == cid, Client.tenant_id == _user.tenant_id))
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    billing_service.validate_price_list_rules(rules=payload.rules_json, client_currency=client.billing_currency)

    pl = PriceList(client_id=cid, effective_from=payload.effective_from, rules_json=payload.rules_json)
    db.add(pl)
    audit_log(
        db,
        tenant_id=_user.tenant_id,
        actor_user_id=_user.id,
        action="billing.price_list.upsert",
        entity_type="PriceList",
        entity_id=str(pl.id),
        after={"client_id": str(cid), "effective_from": pl.effective_from.isoformat()},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(pl)
    return PriceListOut(id=pl.id, client_id=pl.client_id, effective_from=pl.effective_from, rules_json=pl.rules_json)


@router.post("/billing/run-daily-storage")
def run_daily_storage(
    payload: RunDailyStorageBody,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin_or_supervisor),
) -> dict[str, int]:
    created = billing_service.run_daily_storage(db, event_date=payload.event_date)
    audit_log(
        db,
        tenant_id=_user.tenant_id,
        actor_user_id=_user.id,
        action="billing.run_daily_storage",
        entity_type="BillingRun",
        entity_id=payload.event_date.isoformat(),
        after={"created": created},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"created": created}


@router.post("/invoices/generate", response_model=InvoiceOut)
def generate_invoice(
    payload: GenerateInvoiceBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_supervisor),
) -> InvoiceOut:
    # Enforce tenant scoping via client ownership
    client = db.scalar(select(Client).where(Client.id == payload.client_id, Client.tenant_id == user.tenant_id))
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    invoice = billing_service.generate_invoice(
        db, client_id=payload.client_id, period_start=payload.period_start, period_end=payload.period_end
    )

    # Render + store PDF
    language = payload.language or (client.preferred_language if client else "en")
    pdf = render_invoice_pdf(invoice=invoice, language=language)
    key, size = save_bytes(data=pdf, filename=f"invoice_{invoice.id}.pdf")

    f = File(
        tenant_id=user.tenant_id,
        client_id=invoice.client_id,
        file_type="INVOICE_PDF",
        storage_provider=settings.file_storage_provider,
        storage_key=key,
        original_name=f"invoice_{invoice.id}.pdf",
        mime_type="application/pdf",
        size_bytes=size,
        created_by_user_id=user.id,
    )
    db.add(f)
    db.flush()
    invoice.pdf_file_id = f.id
    audit_log(
        db,
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="invoices.generate",
        entity_type="Invoice",
        entity_id=str(invoice.id),
        after={"client_id": str(invoice.client_id), "period_start": invoice.period_start.isoformat(), "period_end": invoice.period_end.isoformat(), "pdf_file_id": str(invoice.pdf_file_id)},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    db.refresh(invoice)
    return _invoice_out(invoice)


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[InvoiceOut]:
    stmt = select(Invoice).join(Client, Client.id == Invoice.client_id).where(Client.tenant_id == user.tenant_id)
    if user.client_id is not None:
        stmt = stmt.where(Invoice.client_id == user.client_id)
    items = db.scalars(stmt).all()
    return [_invoice_out(i) for i in items]


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> InvoiceOut:
    try:
        iid = uuid.UUID(invoice_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    inv = db.scalar(select(Invoice).join(Client, Client.id == Invoice.client_id).where(Invoice.id == iid, Client.tenant_id == user.tenant_id))
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if user.client_id is not None and inv.client_id != user.client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _invoice_out(inv)


@router.get("/invoices/{invoice_id}/lines", response_model=list[InvoiceLineOut])
def list_invoice_lines(invoice_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[InvoiceLineOut]:
    try:
        iid = uuid.UUID(invoice_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    inv = db.scalar(select(Invoice).join(Client, Client.id == Invoice.client_id).where(Invoice.id == iid, Client.tenant_id == user.tenant_id))
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if user.client_id is not None and inv.client_id != user.client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    lines = db.scalars(select(InvoiceLine).where(InvoiceLine.invoice_id == iid)).all()
    return [
        InvoiceLineOut(
            id=l.id,
            invoice_id=l.invoice_id,
            description_key=l.description_key,
            description_params_json=l.description_params_json,
            quantity=l.quantity,
            unit_price=float(l.unit_price),
            total_price=float(l.total_price),
            tax_rate=float(l.tax_rate),
            drilldown_query_json=l.drilldown_query_json,
        )
        for l in lines
    ]


@router.get("/invoices/{invoice_id}/events", response_model=list[BillingEventOut])
def list_invoice_events(invoice_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[BillingEventOut]:
    try:
        iid = uuid.UUID(invoice_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    inv = db.scalar(select(Invoice).join(Client, Client.id == Invoice.client_id).where(Invoice.id == iid, Client.tenant_id == user.tenant_id))
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if user.client_id is not None and inv.client_id != user.client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    events = db.scalars(select(BillingEvent).where(BillingEvent.invoice_id == iid).order_by(BillingEvent.event_date.asc())).all()
    return [
        BillingEventOut(
            id=e.id,
            invoice_id=e.invoice_id,
            client_id=e.client_id,
            warehouse_id=e.warehouse_id,
            event_type=e.event_type,
            quantity=e.quantity,
            unit_price=float(e.unit_price),
            total_price=float(e.total_price),
            reference_type=e.reference_type,
            reference_id=e.reference_id,
            event_date=e.event_date,
        )
        for e in events
    ]


@router.post("/invoices/{invoice_id}/issue")
def issue_invoice(
    invoice_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin_or_supervisor),
) -> dict[str, str]:
    try:
        iid = uuid.UUID(invoice_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    inv = db.scalar(select(Invoice).join(Client, Client.id == Invoice.client_id).where(Invoice.id == iid, Client.tenant_id == _user.tenant_id))
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if inv.status == "PAID":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invoice already paid")
    inv.status = "ISSUED"
    inv.issued_at = datetime.now(timezone.utc)
    if settings.notify_invoice_issued_email:
        # Email all active client users for this client (localized per user preference)
        recipients = db.scalars(select(User).where(User.client_id == inv.client_id, User.is_active.is_(True))).all()
        for r in recipients:
            if r.email:
                queue_invoice_issued_email(
                    db,
                    tenant_id=_user.tenant_id,
                    to_email=r.email,
                    invoice_id=str(inv.id),
                    language=r.language_pref or "en",
                )
    audit_log(
        db,
        tenant_id=_user.tenant_id,
        actor_user_id=_user.id,
        action="invoices.issue",
        entity_type="Invoice",
        entity_id=str(inv.id),
        after={"status": inv.status, "issued_at": inv.issued_at.isoformat()},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


@router.post("/invoices/{invoice_id}/mark-paid")
def mark_paid(
    invoice_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin_or_supervisor),
) -> dict[str, str]:
    try:
        iid = uuid.UUID(invoice_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    inv = db.scalar(select(Invoice).join(Client, Client.id == Invoice.client_id).where(Invoice.id == iid, Client.tenant_id == _user.tenant_id))
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    inv.status = "PAID"
    audit_log(
        db,
        tenant_id=_user.tenant_id,
        actor_user_id=_user.id,
        action="invoices.mark_paid",
        entity_type="Invoice",
        entity_id=str(inv.id),
        after={"status": inv.status},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.commit()
    return {"status": "ok"}


