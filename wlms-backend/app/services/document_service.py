import io
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.models.billing import Invoice


_DOC_T = {
    "en": {
        "inbound.title": "Receiving",
        "dispatch.title": "Dispatch",
        "packing.title": "Packing slip",
        "return.title": "Return",
        "common.lines": "Lines",
        "common.product": "Product",
        "common.qty": "Qty",
        "common.picked": "Picked",
        "common.disposition": "Disposition",
        "common.inbound_id": "Inbound ID",
        "common.outbound_id": "Outbound ID",
        "common.return_id": "Return ID",
    },
    "bs": {
        "inbound.title": "Prijem",
        "dispatch.title": "Otprema",
        "packing.title": "Otpremnica (pakovanje)",
        "return.title": "Povrat",
        "common.lines": "Stavke",
        "common.product": "Proizvod",
        "common.qty": "Količina",
        "common.picked": "Preuzeto",
        "common.disposition": "Postupanje",
        "common.inbound_id": "ID prijema",
        "common.outbound_id": "ID otpreme",
        "common.return_id": "ID povrata",
    },
    "de": {
        "inbound.title": "Wareneingang",
        "dispatch.title": "Versand",
        "packing.title": "Packliste",
        "return.title": "Rücksendung",
        "common.lines": "Positionen",
        "common.product": "Produkt",
        "common.qty": "Menge",
        "common.picked": "Kommissioniert",
        "common.disposition": "Disposition",
        "common.inbound_id": "Wareneingang-ID",
        "common.outbound_id": "Versand-ID",
        "common.return_id": "Retouren-ID",
    },
}


def _dt(lang: str, key: str) -> str:
    return _DOC_T.get(lang, _DOC_T["en"]).get(key, key)


def render_inbound_pdf(*, inbound_id: str, reference_number: str, lines: list[dict], language: str = "en") -> bytes:
    buff = io.BytesIO()
    c = canvas.Canvas(buff, pagesize=A4)
    width, height = A4
    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"{_dt(language, 'inbound.title')} — {reference_number}")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"{_dt(language, 'common.inbound_id')}: {inbound_id}")
    y -= 22
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, _dt(language, "common.lines"))
    y -= 16
    c.setFont("Helvetica", 10)
    for ln in lines:
        c.drawString(
            50,
            y,
            f"{_dt(language, 'common.product')}: {ln.get('product_id')}  {_dt(language, 'common.qty')}: {ln.get('received_qty')}",
        )
        y -= 14
        if y < 80:
            c.showPage()
            y = height - 60
    c.showPage()
    c.save()
    return buff.getvalue()


def render_dispatch_pdf(*, outbound_id: str, order_number: str, lines: list[dict], language: str = "en") -> bytes:
    buff = io.BytesIO()
    c = canvas.Canvas(buff, pagesize=A4)
    width, height = A4
    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"{_dt(language, 'dispatch.title')} — {order_number}")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"{_dt(language, 'common.outbound_id')}: {outbound_id}")
    y -= 22
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, _dt(language, "common.lines"))
    y -= 16
    c.setFont("Helvetica", 10)
    for ln in lines:
        c.drawString(
            50,
            y,
            f"{_dt(language, 'common.product')}: {ln.get('product_id')}  {_dt(language, 'common.picked')}: {ln.get('picked_qty')}",
        )
        y -= 14
        if y < 80:
            c.showPage()
            y = height - 60
    c.showPage()
    c.save()
    return buff.getvalue()


def render_packing_slip_pdf(*, outbound_id: str, order_number: str, lines: list[dict], packing: dict | None = None, language: str = "en") -> bytes:
    buff = io.BytesIO()
    c = canvas.Canvas(buff, pagesize=A4)
    width, height = A4
    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"{_dt(language, 'packing.title')} — {order_number}")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"{_dt(language, 'common.outbound_id')}: {outbound_id}")
    y -= 18
    if packing:
        meta = []
        if packing.get("carton_count") is not None:
            meta.append(f"cartons: {packing.get('carton_count')}")
        if packing.get("weight_kg") is not None:
            meta.append(f"weight_kg: {packing.get('weight_kg')}")
        if packing.get("carrier"):
            meta.append(f"carrier: {packing.get('carrier')}")
        if meta:
            c.setFont("Helvetica", 9)
            c.drawString(50, y, " / ".join(meta))
            y -= 18

    y -= 6
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, _dt(language, "common.lines"))
    y -= 16

    c.setFont("Helvetica", 10)
    for ln in lines:
        c.drawString(
            50,
            y,
            f"{_dt(language, 'common.product')}: {ln.get('product_id')}  {_dt(language, 'common.qty')}: {ln.get('qty')}",
        )
        y -= 14
        if y < 80:
            c.showPage()
            y = height - 60
    c.showPage()
    c.save()
    return buff.getvalue()


def render_return_pdf(*, return_id: str, lines: list[dict], language: str = "en") -> bytes:
    buff = io.BytesIO()
    c = canvas.Canvas(buff, pagesize=A4)
    width, height = A4
    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, _dt(language, "return.title"))
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"{_dt(language, 'common.return_id')}: {return_id}")
    y -= 22
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, _dt(language, "common.lines"))
    y -= 16
    c.setFont("Helvetica", 10)
    for ln in lines:
        c.drawString(
            50,
            y,
            f"{_dt(language, 'common.product')}: {ln.get('product_id')}  {_dt(language, 'common.qty')}: {ln.get('qty')}  {_dt(language, 'common.disposition')}: {ln.get('disposition')}",
        )
        y -= 14
        if y < 80:
            c.showPage()
            y = height - 60
    c.showPage()
    c.save()
    return buff.getvalue()


_TRANSLATIONS = {
    "en": {
        "invoice.title": "Invoice",
        "invoice.period": "Period",
        "invoice.total": "Total",
        "invoice.subtotal": "Subtotal",
        "invoice.tax": "Tax",
        "invoice.lines": "Lines",
        "invoice.line.INBOUND_LINE": "Inbound handling (lines)",
        "invoice.line.DISPATCH_ORDER": "Dispatch (orders)",
        "invoice.line.STORAGE_DAY": "Storage (pallet-position-day)",
        "invoice.line.PRINT_LABEL": "Printing (labels)",
    },
    "bs": {
        "invoice.title": "Faktura",
        "invoice.period": "Period",
        "invoice.total": "Ukupno",
        "invoice.subtotal": "Međuzbir",
        "invoice.tax": "Porez",
        "invoice.lines": "Stavke",
        "invoice.line.INBOUND_LINE": "Prijem (stavke)",
        "invoice.line.DISPATCH_ORDER": "Otprema (nalozi)",
        "invoice.line.STORAGE_DAY": "Skladištenje (paletno mjesto/dan)",
        "invoice.line.PRINT_LABEL": "Štampa (etikete)",
    },
    "de": {
        "invoice.title": "Rechnung",
        "invoice.period": "Zeitraum",
        "invoice.total": "Summe",
        "invoice.subtotal": "Zwischensumme",
        "invoice.tax": "Steuer",
        "invoice.lines": "Positionen",
        "invoice.line.INBOUND_LINE": "Wareneingang (Positionen)",
        "invoice.line.DISPATCH_ORDER": "Versand (Aufträge)",
        "invoice.line.STORAGE_DAY": "Lagerung (Palettenplatz/Tag)",
        "invoice.line.PRINT_LABEL": "Druck (Labels)",
    },
}


def _t(lang: str, key: str) -> str:
    return _TRANSLATIONS.get(lang, _TRANSLATIONS["en"]).get(key, key)


def render_invoice_pdf(*, invoice: Invoice, language: str = "en") -> bytes:
    # Minimal PDF generator (no external OS deps).
    # We keep fonts default to be portable; can add branded font later.
    buff = io.BytesIO()
    c = canvas.Canvas(buff, pagesize=A4)
    width, height = A4

    y = height - 60
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, f"{_t(language, 'invoice.title')} — {invoice.id}")

    y -= 24
    c.setFont("Helvetica", 10)
    c.drawString(
        50,
        y,
        f"{_t(language, 'invoice.period')}: {invoice.period_start.isoformat()} → {invoice.period_end.isoformat()}",
    )

    y -= 30
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, _t(language, "invoice.lines"))
    y -= 16

    c.setFont("Helvetica", 10)
    for line in invoice.lines:
        label = _t(language, f"invoice.line.{line.description_params_json.get('event_type', line.description_key)}")
        c.drawString(50, y, label)
        c.drawRightString(420, y, str(line.quantity))
        c.drawRightString(510, y, f"{float(line.total_price):.2f} {invoice.currency}")
        y -= 14
        if y < 80:
            c.showPage()
            y = height - 60

    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(510, y, f"{_t(language, 'invoice.subtotal')}: {float(invoice.subtotal):.2f} {invoice.currency}")
    y -= 14
    c.drawRightString(510, y, f"{_t(language, 'invoice.tax')}: {float(invoice.tax_total):.2f} {invoice.currency}")
    y -= 14
    c.drawRightString(510, y, f"{_t(language, 'invoice.total')}: {float(invoice.total):.2f} {invoice.currency}")

    c.showPage()
    c.save()
    return buff.getvalue()


