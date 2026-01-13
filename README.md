# SystemECOM (WLMS) — Monorepo

SystemECOM is a multi-tenant Warehouse & Logistics Management System (WLMS) with:

- **Admin Portal** (warehouse admin/supervisors)
- **Client Portal** (client self-service)
- **Worker PWA** (scan-first warehouse flows)

Languages (end-to-end): **English / Bosnian / German**.

## Repo layout

```
SystemECOM/
  wlms-backend/   # FastAPI + PostgreSQL + Redis + Celery
  wlms-frontend/  # Next.js (Admin + Client + Worker PWA)
  RoadMap.txt
  checklist.md
```

## Quick start (dev)

### Backend

1) Copy env:

`wlms-backend/env.example` → `wlms-backend/.env`

2) Create venv + install:

```bash
cd wlms-backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3) Run API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `GET http://localhost:8000/health`

### Frontend

1) Copy env:

`wlms-frontend/env.local.example` → `wlms-frontend/.env.local`

2) Install + run:

```bash
cd wlms-frontend
npm install
npm run dev
```

---

## Theme direction (non-negotiable)

- **Serious**, symmetrical, brutalist-inspired UI
- Colors: **black / white / dark blue / yellow (accent only)**
- No bubbly/goofy/cartoon visuals

## Environments

See `docs/environments.md` for the recommended `.env` strategy (dev/staging/prod) and minimum required variables.


