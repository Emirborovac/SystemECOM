# Environments (.env) — SystemECOM

SystemECOM is a monorepo:

- `wlms-backend/` (FastAPI)
- `wlms-frontend/` (Next.js)

## Local dev

- Backend: copy `wlms-backend/env.example` → `wlms-backend/.env`
- Frontend: copy `wlms-frontend/env.local.example` → `wlms-frontend/.env.local`

## Staging / Production

- Keep `.env` files **out of git** (already ignored).
- Prefer **host-level secrets** (CI/CD secret store) that populate env vars at runtime.
- Use `ENV=staging` / `ENV=prod` in backend.

## Recommended minimum variables

Backend:

- `DATABASE_URL`
- `JWT_SECRET`
- `CORS_ORIGINS`
- `FRONTEND_BASE_URL`
- `FILE_STORAGE_PROVIDER` (+ S3/MinIO vars when not LOCAL)

Frontend:

- `NEXT_PUBLIC_API_BASE_URL`


