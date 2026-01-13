# SystemECOM — Ubuntu First-Test Blueprint (IP + Ports)

This document is the **single blueprint** for developers to deploy and test SystemECOM on an Ubuntu server **using only the server IP + ports**.

**Ports (per your server constraints)**
- **Backend (FastAPI)**: `2000`
- **Frontend (Next.js)**: `2020`

**URLs**
- **Backend**: `http://<SERVER_IP>:2000`
- **Frontend**: `http://<SERVER_IP>:2020`

---

## 1) Prerequisites (Ubuntu)

Install required tools:

```bash
sudo apt update
sudo apt install -y git curl ca-certificates
sudo apt install -y python3 python3-venv python3-pip
sudo apt install -y nodejs npm
sudo apt install -y docker.io docker-compose-plugin
```

Recommended: ensure the user running the app has Docker permissions:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## 2) Expected folder layout

Example layout (you can change paths; keep consistent):

```
/opt/systemecom/
  wlms-backend/
  wlms-frontend/
  docker-compose.yml
```

Clone/update:

```bash
git clone <YOUR_REPO_URL> /opt/systemecom
cd /opt/systemecom
```

---

## 3) Start infrastructure (Postgres + Redis + MinIO)

From repo root:

```bash
docker compose up -d db redis minio minio-init
docker compose ps
```

---

## 4) Backend setup (FastAPI) — port 2000

### 4.1 Create backend environment file

In `wlms-backend/`:

```bash
cd /opt/systemecom/wlms-backend
cp env.example .env
```

Edit `wlms-backend/.env`:

**Required minimum keys**
- `ENV=dev`
- `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/systemecom`
- `JWT_SECRET=<long-random-secret>`
- `CORS_ORIGINS=http://<SERVER_IP>:2020`

### 4.2 Install backend dependencies

```bash
cd /opt/systemecom/wlms-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4.3 Run DB migrations

```bash
cd /opt/systemecom/wlms-backend
source venv/bin/activate
alembic upgrade head
```

### 4.4 Run backend (foreground for first tests)

```bash
cd /opt/systemecom/wlms-backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 2000
```

Sanity check:

```bash
curl -s http://127.0.0.1:2000/health
```

---

## 5) Frontend setup (Next.js) — port 2020

### 5.1 Create frontend environment file

```bash
cd /opt/systemecom/wlms-frontend
cp env.local.example .env.local
```

Edit `wlms-frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://<SERVER_IP>:2000
```

### 5.2 Install + build + run

```bash
cd /opt/systemecom/wlms-frontend
npm ci
npm run build
npm run start -- --port 2020
```

Open:
- `http://<SERVER_IP>:2020/en/login`

---

## 6) One-time bootstrap (create first tenant + admin)

The backend has a dev-only bootstrap endpoint (only when `ENV=dev`).

```bash
curl -s -X POST "http://127.0.0.1:2000/api/v1/dev/init" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "DemoTenant",
    "admin_email": "admin@example.com",
    "admin_password": "admin12345",
    "admin_full_name": "Admin",
    "admin_language_pref": "en"
  }'
```

Login:
- **Username**: `admin@example.com` (you can use username OR email in the login field)
- **Password**: `admin12345`

---

## 7) Manual end-to-end test flow (the “real” first test)

Follow this exactly, top to bottom:

### 7.1 Admin setup
1. **Admin → Clients**
   - Create a client
   - Set **currency** (BAM or EUR)
   - Set **VAT rate** (default 0.17 for Bosnia, adjust per client)
2. **Admin → Warehouses**
   - Create warehouse
   - Create zones: **STAGING**, **STORAGE**, **PACKING** (minimum)
   - Create locations, OR bulk import locations CSV
   - Download and verify **Location Labels PDF**
3. **Admin → Products**
   - Create product with **barcode**
   - If using carton/pallet scanning: set **carton_qty** / **pallet_qty**
   - (Optional) Set **category** for filtering

### 7.2 Inbound → Put-away
4. **Admin → Inbound**
   - Create inbound for the client + warehouse
5. **Worker → Receive**
   - Start receiving
   - Scan product barcode + qty into STAGING
   - If scanning cartons/pallets: provide `uom` as carton/pallet (UI or API depending on workflow)
   - Complete inbound (receiving PDF should be generated)
6. **Worker → Put-away**
   - Move from STAGING to STORAGE (destination must be a STORAGE zone)

### 7.3 Outbound → Pick → Pack → Dispatch
7. **Admin (or Client) → Outbound**
   - Create outbound order with lines
8. **Admin → Outbound**
   - Approve outbound
   - Generate pick task
9. **Worker → Pick**
   - Start task
   - Scan correct product + from-location (wrong scan should block unless supervisor override is used)
   - Complete task (moves goods to PACKING location)
10. **Worker → Pack**
   - Confirm packing (optional: cartons/weight/carrier)
   - Packing slip PDF should be generated
11. **Worker → Dispatch**
   - Confirm dispatch from packing location
   - Dispatch PDF should be generated

### 7.4 Billing / Invoice
12. **Admin → Invoices**
   - Generate invoice for the period (include today)
   - Verify:
     - subtotal
     - VAT/tax total
     - total
   - Download invoice PDF
13. **Admin → Documents**
   - Verify PDFs are listed and downloadable (auth-protected downloads)

---

## 8) Automated tests (optional but recommended)

### 8.1 Backend tests

```bash
cd /opt/systemecom/wlms-backend
source venv/bin/activate
pytest -q
```

### 8.2 Frontend E2E tests (Playwright)

Requires backend + frontend running.

```bash
cd /opt/systemecom/wlms-frontend
npm run test:e2e
```

---

## 9) systemd (systemctl) services (optional, recommended after first manual run)

Templates exist in:
- `deploy/systemd/systemecom-backend.service`
- `deploy/systemd/systemecom-frontend.service`

**Important**: adjust the `ExecStart` ports to **2000** and **2020**.

### Install services
Copy to systemd:

```bash
sudo mkdir -p /etc/systemecom
sudo cp /opt/systemecom/deploy/systemd/systemecom-backend.service /etc/systemd/system/systemecom-backend.service
sudo cp /opt/systemecom/deploy/systemd/systemecom-frontend.service /etc/systemd/system/systemecom-frontend.service
```

Create env files:
- `/etc/systemecom/backend.env` (copy from `wlms-backend/env.example` keys)
- `/etc/systemecom/frontend.env` (must include `NEXT_PUBLIC_API_BASE_URL=http://<SERVER_IP>:2000`)

Enable + start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now systemecom-backend
sudo systemctl enable --now systemecom-frontend
```

Logs:

```bash
journalctl -u systemecom-backend -f
journalctl -u systemecom-frontend -f
```

---

## 10) Troubleshooting quick hits

- **Frontend can’t call backend**:
  - Check `NEXT_PUBLIC_API_BASE_URL`
  - Check backend `CORS_ORIGINS` includes `http://<SERVER_IP>:2020`
- **Migrations fail**:
  - Confirm DB is up: `docker compose ps`
  - Confirm `DATABASE_URL` points to localhost and correct port
- **Login fails**:
  - Login input is **username OR email**
  - Confirm `ENV=dev` and you ran `/api/v1/dev/init`
- **Ports blocked**:
  - Open firewall or use different ports:
    - `sudo ufw allow 2000/tcp`
    - `sudo ufw allow 2020/tcp`


