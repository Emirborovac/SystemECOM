# systemd deployment (systemctl) — SystemECOM

This repo can be deployed on a Linux VPS using `systemctl` by running backend + frontend as systemd services.

## Recommended layout (example)

- `/opt/systemecom/`
  - `wlms-backend/`
  - `wlms-frontend/`
- Env files:
  - `/etc/systemecom/backend.env`
  - `/etc/systemecom/frontend.env`

## Backend service

1. Copy the template `deploy/systemd/systemecom-backend.service` to `/etc/systemd/system/systemecom-backend.service`.
2. Create `/etc/systemecom/backend.env` (see `wlms-backend/env.example` for keys).
3. Ensure backend venv exists (example):
   - `python3 -m venv /opt/systemecom/wlms-backend/venv`
   - `/opt/systemecom/wlms-backend/venv/bin/pip install -r /opt/systemecom/wlms-backend/requirements.txt`
4. Enable + start:
   - `sudo systemctl daemon-reload`
   - `sudo systemctl enable --now systemecom-backend`

## Frontend service

1. Copy `deploy/systemd/systemecom-frontend.service` to `/etc/systemd/system/systemecom-frontend.service`.
2. Create `/etc/systemecom/frontend.env`:
   - `NEXT_PUBLIC_API_BASE_URL=https://your-domain.com`
3. Build once:
   - `cd /opt/systemecom/wlms-frontend && npm ci && npm run build`
4. Enable + start:
   - `sudo systemctl daemon-reload`
   - `sudo systemctl enable --now systemecom-frontend`

## Logs

- `journalctl -u systemecom-backend -f`
- `journalctl -u systemecom-frontend -f`


