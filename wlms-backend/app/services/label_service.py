import io

from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def render_location_labels_pdf(*, locations: list[dict], title: str = "Location labels") -> bytes:
    """
    locations: [{ "code": str, "barcode_value": str }]
    """
    buff = io.BytesIO()
    c = canvas.Canvas(buff, pagesize=A4)
    width, height = A4

    c.setTitle(title)

    margin_x = 10 * mm
    margin_y = 12 * mm
    cols = 2
    rows = 8
    label_w = (width - 2 * margin_x) / cols
    label_h = (height - 2 * margin_y) / rows

    per_page = cols * rows
    for idx, loc in enumerate(locations):
        if idx > 0 and idx % per_page == 0:
            c.showPage()

        pos = idx % per_page
        col = pos % cols
        row = pos // cols

        x = margin_x + col * label_w
        y = height - margin_y - (row + 1) * label_h

        code = str(loc.get("code") or "")
        barcode_value = str(loc.get("barcode_value") or code)

        # border
        c.setLineWidth(1)
        c.rect(x, y, label_w, label_h)

        # text
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x + 6 * mm, y + label_h - 10 * mm, code[:32])
        c.setFont("Helvetica", 8)
        c.drawString(x + 6 * mm, y + label_h - 15 * mm, barcode_value[:48])

        # barcode
        bc = code128.Code128(barcode_value, barHeight=12 * mm, barWidth=0.4)
        bc.drawOn(c, x + 6 * mm, y + 5 * mm)

    c.showPage()
    c.save()
    return buff.getvalue()


