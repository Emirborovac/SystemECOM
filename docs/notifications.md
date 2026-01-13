# Notifications (Email) — SystemECOM

SystemECOM queues emails into `email_outbox` and sends them asynchronously (v1 can be a simple polling worker; Celery planned).

## Template strategy (v1)

- **Templates live in code** in `wlms-backend/app/services/notification_service.py`
- **Key-based + params**:
  - Example keys: `invite.subject`, `invite.body`, `invoice_issued.subject`
  - Params: `{link}` (and other placeholders as needed)
- **Per-user language**:
  - Each queued email stores `language` and is rendered using that locale (EN/BS/DE)
  - Fallback: missing keys fall back to English

## Feature toggles (env)

Configured via backend `.env` (see `wlms-backend/env.example`):

- `NOTIFY_INBOUND_RECEIVED_EMAIL` (default `false`)
- `NOTIFY_OUTBOUND_DISPATCHED_EMAIL` (default `false`)
- `NOTIFY_INVOICE_ISSUED_EMAIL` (default `true`)


