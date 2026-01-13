import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import EmailOutbox


_T = {
    "en": {
        "invite.subject": "SystemECOM — Account invite",
        "invite.body": "You were invited to SystemECOM. Set your password here: {link}",
        "reset.subject": "SystemECOM — Password reset",
        "reset.body": "Reset your SystemECOM password here: {link}",
        "invoice_issued.subject": "SystemECOM — Invoice issued",
        "invoice_issued.body": "An invoice was issued for your account. Download it here: {link}",
        "inbound_received.subject": "SystemECOM — Inbound received",
        "inbound_received.body": "Inbound was received in the warehouse. View it here: {link}",
        "outbound_dispatched.subject": "SystemECOM — Outbound dispatched",
        "outbound_dispatched.body": "Outbound was dispatched. View status here: {link}",
    },
    "bs": {
        "invite.subject": "SystemECOM — Poziv za račun",
        "invite.body": "Pozvani ste u SystemECOM. Postavite lozinku ovdje: {link}",
        "reset.subject": "SystemECOM — Reset lozinke",
        "reset.body": "Resetujte lozinku za SystemECOM ovdje: {link}",
        "invoice_issued.subject": "SystemECOM — Faktura izdata",
        "invoice_issued.body": "Faktura je izdata za vaš račun. Preuzmite je ovdje: {link}",
        "inbound_received.subject": "SystemECOM — Prijem završen",
        "inbound_received.body": "Prijem je završen u skladištu. Pogledajte ovdje: {link}",
        "outbound_dispatched.subject": "SystemECOM — Otprema izvršena",
        "outbound_dispatched.body": "Otprema je izvršena. Status ovdje: {link}",
    },
    "de": {
        "invite.subject": "SystemECOM — Kontoeinladung",
        "invite.body": "Sie wurden zu SystemECOM eingeladen. Passwort setzen: {link}",
        "reset.subject": "SystemECOM — Passwort zurücksetzen",
        "reset.body": "Setzen Sie Ihr SystemECOM Passwort zurück: {link}",
        "invoice_issued.subject": "SystemECOM — Rechnung ausgestellt",
        "invoice_issued.body": "Eine Rechnung wurde für Ihr Konto ausgestellt. Download: {link}",
        "inbound_received.subject": "SystemECOM — Wareneingang abgeschlossen",
        "inbound_received.body": "Der Wareneingang wurde im Lager abgeschlossen. Ansicht: {link}",
        "outbound_dispatched.subject": "SystemECOM — Versand erfolgt",
        "outbound_dispatched.body": "Der Versand wurde durchgeführt. Status: {link}",
    },
}


def _t(lang: str, key: str) -> str:
    return _T.get(lang, _T["en"]).get(key, key)


def queue_email(db: Session, *, tenant_id: int, to_email: str, subject: str, body: str, language: str = "en") -> uuid.UUID:
    e = EmailOutbox(tenant_id=tenant_id, to_email=to_email, subject=subject, body=body, language=language, status="QUEUED")
    db.add(e)
    db.flush()
    return e.id


def queue_invite_email(db: Session, *, tenant_id: int, to_email: str, token: str, language: str) -> uuid.UUID:
    link = f"{settings.frontend_base_url}/{language}/invite-accept?token={token}"
    subject = _t(language, "invite.subject")
    body = _t(language, "invite.body").format(link=link)
    return queue_email(db, tenant_id=tenant_id, to_email=to_email, subject=subject, body=body, language=language)


def queue_password_reset_email(db: Session, *, tenant_id: int, to_email: str, token: str, language: str) -> uuid.UUID:
    link = f"{settings.frontend_base_url}/{language}/reset-password?token={token}"
    subject = _t(language, "reset.subject")
    body = _t(language, "reset.body").format(link=link)
    return queue_email(db, tenant_id=tenant_id, to_email=to_email, subject=subject, body=body, language=language)


def queue_invoice_issued_email(db: Session, *, tenant_id: int, to_email: str, invoice_id: str, language: str) -> uuid.UUID:
    link = f"{settings.frontend_base_url}/{language}/portal/invoices?invoice_id={invoice_id}"
    subject = _t(language, "invoice_issued.subject")
    body = _t(language, "invoice_issued.body").format(link=link)
    return queue_email(db, tenant_id=tenant_id, to_email=to_email, subject=subject, body=body, language=language)


def queue_inbound_received_email(db: Session, *, tenant_id: int, to_email: str, inbound_id: str, language: str) -> uuid.UUID:
    link = f"{settings.frontend_base_url}/{language}/portal/inbound?inbound_id={inbound_id}"
    subject = _t(language, "inbound_received.subject")
    body = _t(language, "inbound_received.body").format(link=link)
    return queue_email(db, tenant_id=tenant_id, to_email=to_email, subject=subject, body=body, language=language)


def queue_outbound_dispatched_email(db: Session, *, tenant_id: int, to_email: str, outbound_id: str, language: str) -> uuid.UUID:
    link = f"{settings.frontend_base_url}/{language}/portal/orders?outbound_id={outbound_id}"
    subject = _t(language, "outbound_dispatched.subject")
    body = _t(language, "outbound_dispatched.body").format(link=link)
    return queue_email(db, tenant_id=tenant_id, to_email=to_email, subject=subject, body=body, language=language)


