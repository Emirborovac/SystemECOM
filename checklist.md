# WLMS Build Checklist (EN/BS/DE) — Page-by-page + Feature-by-feature

> Use this file as the single source of truth for what’s built.  
> Checkboxes: `[ ]` pending, `[x]` done.

---

## Progress snapshot (manual, keep updated)

- **Scaffold done**
  - [x] Monorepo folders: `wlms-backend/`, `wlms-frontend/`
  - [x] Backend boots (FastAPI skeleton) + health endpoints
  - [x] Frontend boots (Next.js skeleton) + locale routing (EN/BS/DE)
  - [x] Brutalist palette tokens implemented (black/white/dark blue/yellow accent)
- **Core MVP (backend) done**
  - [x] DB + migrations
  - [x] Auth (JWT access+refresh) + RBAC + tenant/client scoping
  - [x] Core entities (clients/users/warehouses/locations/products)
  - [x] Inbound → put-away → inventory ledger/balances
  - [x] Outbound → picking/packing/dispatch
  - [x] Billing (PALLET_POSITION_DAY) + invoices + PDFs
  - [x] Document center + reports + audit logs
- **Still to build (remaining big items)**
  - [x] Frontend i18n completeness (remove remaining hardcoded strings; persist user language)
  - [x] Admin auth pages (forgot/reset/invite accept)
  - [x] Worker scanner UX (camera/manual + wrong-scan enforcement/override)
  - [x] DevOps (Docker/Compose/CI)

---

## 0) Project decisions (confirm early)

- [x] **Monorepo layout decided** (`wlms-backend/` + `wlms-frontend/`)
- [x] **Target deployment** decided (systemctl/systemd services on VPS for now)
- [x] **Auth policy** confirmed (username+password v1; MFA deferred)
- [x] **Barcode policy** confirmed (**unique per client** / within `client_id`)
- [x] **Inventory unit policy** confirmed (support piece/carton/pallet conversions in v1; store internally as pieces)
- [x] **Expiry/lot rules** confirmed (FEFO default when expiry enabled; “any batch” acceptable when no expiry)
- [x] **Approval modes** confirmed for outbound (**per-client auto-approve** available; default stays admin-approve)
- [x] **Billing currency/tax** confirmed (per-client currency; VAT/tax supported per client; default Bosnia-friendly VAT)
 - [x] **Storage billing model** confirmed (**PALLET_POSITION_DAY** in v1)
 - [x] **Worker offline mode** confirmed (**Phase 2**, not in v1)

---

## 1) Repository + engineering foundations

### 1.1 Standards
- [x] **README**: local dev, env setup, run commands, architecture overview
- [x] **Env templates** created (frontend + backend) with NO secrets committed (`env.example`, `env.local.example`)
- [x] **Logging strategy** (request IDs + consistent request logs)
- [x] **Error handling** standard (API error schema)
- [x] **API versioning** (`/api/v1/...`) enforced
- [x] **RBAC/permissions** conventions documented (`docs/rbac.md`)
- [x] **i18n conventions** documented (translation keys only, no hardcoded strings) (`docs/i18n.md`)

### 1.2 Tooling
- [x] **Backend** lint/format (ruff/black) + type checking (mypy) configured
- [x] **Frontend** lint/format (eslint/prettier) configured
- [x] **Pre-commit hooks** configured
- [x] **CI**: build + unit tests + lint

---

## 2) Database + migrations (PostgreSQL)

### 2.1 Core schema (from RoadMap)
- [x] `tenants` table
- [x] `clients` table (preferred_language, billing_currency, etc.)
- [x] `users` table (role, language_pref, client_id nullable)
- [x] `warehouses` table
- [x] `warehouse_zones` table (zone_type)
- [x] `locations` table (code + barcode_value)
- [x] `products` table (client-scoped)
- [x] `product_batches` table (lot/expiry) (core table created)

### 2.2 Operational schema
- [x] `inbound_shipments` + `inbound_lines`
- [x] `outbound_orders` + `outbound_lines`
- [x] `picking_tasks` + `picking_task_lines`
- [x] `returns` + `return_lines`
- [x] `discrepancy_reports`

### 2.3 Inventory + ledger
- [x] `inventory_balances` (on_hand, reserved, available)
- [x] `inventory_ledger` (immutable, traceable)

### 2.4 Billing + documents + audit
- [x] `price_lists` (rules_json)
- [x] `billing_events`
- [x] `invoices` + `invoice_lines`
- [x] `files` (PDFs, exports)
- [x] `audit_logs`

### 2.5 Constraints & tenant safety (hard requirement)
- [x] Unique constraints enforced (e.g., `unique(client_id, sku)` etc.)
- [x] Foreign keys + indexes for common filters (tenant_id/client_id/warehouse_id)
- [x] **Backend query scoping** always applies tenant/client filters (no “UI-only” isolation) (verified via integration tests across list/download endpoints)

---

## 3) Backend (FastAPI) — Cross-cutting requirements

### 3.1 App core
- [x] Config system reads `.env`
- [x] DB session setup + migrations scaffolded (SQLAlchemy + Alembic)
- [x] CORS configured for frontend origins
- [x] Request auth middleware/dependencies (JWT)
- [x] RBAC dependency helpers (role/permission checks)
- [x] Rate limiting on auth endpoints (Redis-backed; falls back to in-memory if Redis unavailable)
- [x] Audit logging service wired for write operations
- [x] i18n utilities for server-generated strings (emails/PDF keys)

### 3.2 Auth & security
- [x] `POST /api/v1/auth/login` (access+refresh)
- [x] `POST /api/v1/auth/refresh`
- [x] `POST /api/v1/auth/forgot-password` (email outbox)
- [x] `POST /api/v1/auth/reset-password`
- [x] `POST /api/v1/auth/logout`
- [x] Password hashing (argon2/bcrypt) + secure policies
- [x] Token invalidation strategy (token_version-based invalidation; logout bumps version; access/refresh checked against DB)
- [x] User language preference stored and returned

---

## Phase utilities (dev-only)

- [x] Dev bootstrap/init endpoint exists (create first tenant + admin user) — `POST /api/v1/dev/init` (ENV=dev only)

### 3.3 Roles (minimum v1)
- [x] Warehouse Admin
- [x] Warehouse Supervisor
- [x] Warehouse Worker
- [x] Client User
- [x] (Optional v1) Driver/Courier role placeholder

---

## 4) Frontend (Next.js App Router) — Cross-cutting requirements

### 4.0 Brand, theme, and layout rules (hard requirement)
- [x] **Visual direction**: serious, symmetrical, brutalist-inspired; no playful/bubbly/goofy visuals
- [x] **Palette** locked and implemented:
  - [x] Black
  - [x] White
  - [x] Dark blue
  - [x] Yellow (accent only)
- [x] **Typography**: clean, professional, high-legibility; consistent across portals
- [x] **Layout**: strong grid, consistent spacing scale, sharp corners, minimal decoration
- [x] **Components**: tables/forms/buttons designed for enterprise ops (dense but readable)

### 4.1 Global UI
- [x] App shell: top bar (language selector EN/BS/DE), profile, logout
- [x] Left navigation per role (admin/client/worker) (v1 minimal)
- [x] Route protection (auth guard) (v1 minimal client-side)
- [x] API client with token refresh handling
- [x] Form validation + consistent toasts/errors (base toast system + API error parsing; applied on key pages)
- [x] Table components (pagination, filters, export triggers) (reusable DataTable with filter + pagination; download/export buttons per page)

### 4.2 i18n end-to-end (hard requirement)
- [x] Translation keys used everywhere (no hardcoded text)
- [x] Language selector persists per user
- [x] Emails rendered in user language (invite/reset + invoice issued email localized per user language_pref)
- [x] PDFs generated in selected language (client preferred_language default; falls back to user language)

---

## 5) Pages (page-by-page) — Admin Portal

### 5.1 Auth pages
- [x] Login page (language dropdown)
- [x] Forgot password page
- [x] Reset password page
- [x] Invite acceptance / set password page

### 5.2 Admin navigation pages (from RoadMap)
- [x] Dashboard
- [x] Clients (basic page)
- [x] Warehouses & Zones (basic page)
- [x] Locations (basic page inside Warehouses)
- [x] Products (global view + client filter) (basic page)
- [x] Inbound (basic page)
- [x] Put-away (basic page)
- [x] Outbound Orders (basic page)
- [x] Picking (basic page)
- [x] Packing / Dispatch (basic page)
- [x] Returns (basic page)
- [x] Discrepancies (basic page)
- [x] Billing & Invoices (basic page: invoices list/generate)
- [x] Reports (basic page)
- [x] Documents (basic page)
- [x] Users & Roles (UI + backend endpoints)
- [x] Settings (prices, templates, languages) (basic: price list editor)

### 5.3 Admin Dashboard (minimum cards/charts)
- [x] Today inbound count
- [x] Today outbound count
- [x] Current occupied pallet positions
- [x] Discrepancies pending approval
- [x] Expiring items (30/60/90 days)
- [x] Expiring items (30/60/90 days) (counts)
- [x] Charts: inbound/outbound over time (basic table)
- [x] Charts: top clients by activity (basic list)

---

## 6) Pages (page-by-page) — Client Portal

### 6.1 Navigation pages
- [x] Dashboard
- [x] My Inventory (snapshot + filters)
- [x] Create Inbound Notice (basic page)
- [x] Create Outbound Order (basic page)
- [x] Orders (status tracking) (basic page)
- [x] Returns (status) (basic page)
- [x] Invoices (list + download) (basic page)
- [x] Reports (basic page)
- [x] Documents (basic page)
- [x] Settings (users, language) (basic page)

### 6.2 Client Inventory page behaviors
- [x] Table: SKU, Name, On hand, Reserved, Available (v1: IDs; labels later)
- [x] Filters: warehouse, expiry range, product category
- [x] Per-location breakdown modal/page

---

## 7) Pages (page-by-page) — Worker UI (PWA-first)

### 7.1 Worker Home
- [x] Big buttons: Receive, Put-away, Pick, Pack, Dispatch (optional), Returns, Report Issue
- [x] Offline indicator + queued actions (**Phase 2**, not v1) (explicitly deferred to Phase 2; no offline queue in v1)

### 7.2 Scanner UX (cross-flow)
- [x] Camera scanning (browser BarcodeDetector, where supported)
- [x] Manual barcode entry fallback
- [x] Haptic/audio feedback (basic)
- [x] “Wrong scan” blocking rules (basic UI enforcement)
- [x] Supervisor override flow (when allowed) (basic)

---

## 8) Core modules — Backend services + endpoints + acceptance criteria

## 8.1 Clients (Organization model)
- [x] Admin can create client (name, address, tax IDs, billing profile, preferred_language)
- [x] Admin can invite client user (email invite → set password) (invite token + accept endpoint)
- [x] Client portal shows only client assets (API scoped by tenant/client)
- [x] API scoping prevents cross-client access even by ID tampering

## 8.2 Warehouses, zones, locations
- [x] Create warehouse
- [x] Create zones (STAGING, STORAGE, PACKING, RETURNS, QUARANTINE)
- [x] Create locations (code + barcode_value)
- [x] Bulk import locations (CSV/Excel) (Admin UI CSV upload + backend import endpoint + error report)
- [x] Location labels printable (barcode/QR) (A4 PDF generator with Code128 barcodes)

## 8.3 Products (per client)
- [x] CRUD product
- [x] CSV/Excel import with validation + error report (Admin UI CSV upload + backend import endpoint + error list)
- [x] Duplicate SKU detection per client (DB constraint + 409)
- [x] Barcode uniqueness policy enforced (**unique within `client_id`**) (DB constraint + 409)

## 8.4 Inventory engine (ledger + balances) (hard requirement)
- [x] Ledger events defined and implemented
- [x] Balance updates derived and stored (fast reads)
- [x] Available = on_hand - reserved (consistent)
- [x] Full traceability: every ledger entry links to reference + user + timestamps
- [x] Ability to reconstruct history from ledger
 - [x] `GET /api/v1/inventory/balances` implemented (tenant/client scoped + filters)
 - [x] `GET /api/v1/inventory/movements` implemented (ledger list; tenant/client scoped)
 - [x] `POST /api/v1/inventory/transfer` implemented (manual transfer; blocks moving reserved stock)

## 8.5 Inbound receiving
- [x] Create inbound (client or warehouse)
- [x] Worker “start receiving”
- [x] Scan product barcode / search
- [x] Enter qty received
- [x] Lot/expiry capture enforced when enabled (required when product.lot_tracking_enabled/expiry_tracking_enabled; enforced on inbound scan-line)
- [x] Receive to staging location (must be STAGING zone)
- [x] Receiving PDF generated + stored
- [x] Ledger movements created (+ into staging)
 - [x] API endpoints implemented: create/list/get/start-receiving/scan-line/complete

## 8.6 Put-away (staging → storage)
- [x] Put-away tasks generated from staging inventory
- [x] System suggests location (configurable rules) (put-away tasks include suggested STORAGE location)
- [x] Worker scans pallet + destination location (worker put-away flow scans from/to location values)
- [x] Confirm move
- [x] Wrong-location scan blocks/warns (supervisor override if allowed) (backend enforces STORAGE destination; UI pre-fills suggested STORAGE location)
- [x] Ledger movement recorded (location transfer)
 - [x] API endpoints implemented: tasks + confirm

## 8.7 Outbound order creation (client)
- [x] Create outbound order with destination + lines
- [x] Validate available stock (via reservation on approve)
- [x] Approval flow (admin approve vs **per-client auto-approve** setting) (admin approve implemented)
- [x] Reserve stock upon approval (configurable) (reserve on approve implemented)
- [x] Cannot request more than available (unless backorder mode enabled) (v1 enforced)

### Outbound implementation notes (SystemECOM)
- [x] Per-order reservations table exists (`inventory_reservations`) so multiple orders can reserve simultaneously

## 8.8 Picking (guided, scan-validated)
- [x] Generate pick tasks/batches
- [x] Route/group by zone/location (pick generation + pick lines ordered by zone/location)
- [x] Worker scans location then product (v1: task line uses from_location_id/product_id; scan endpoint)
- [x] Enforce correct SKU + location (backend pick scan must match task line: product_id + batch_id + from_location_id)
- [x] FEFO suggestions when expiry enabled (pick ordering prefers earlier expiry where batch expiry exists)
- [x] Confirm picked qty and move to packing staging
- [x] Available/reserved updated correctly (reservations consumed + balances updated)

## 8.9 Packing
- [x] Confirm picked items per order (basic endpoint)
- [x] Print packing slip / labels (Packing Slip PDF generated + stored on packing confirm; downloadable)
- [x] Mark order packed
- [x] Optional capture: cartons, weight, carrier (captured in outbound_orders.packing_json)

## 8.10 Dispatch
- [x] Confirm loading / dispatch (basic endpoint)
- [x] Generate dispatch PDF + store
- [x] Finalize stock decrement
- [x] Create billing events for dispatch (if enabled in pricing) (DISPATCH_ORDER event created on dispatch confirm)

## 8.11 Returns
- [x] Receive returned items (scan SKU + qty) (API)
- [x] Choose disposition: RESTOCK / QUARANTINE / SCRAP (API)
- [x] Route to correct location/zone (RESTOCK/QUARANTINE use to_location_id)
- [x] Return PDF generated + stored

## 8.12 Discrepancies (approval required)
- [x] Worker creates discrepancy report (product, location, counted qty, reason)
- [x] System calculates delta vs system qty
- [x] Status = Pending
- [x] Admin approve → adjustment ledger applied
- [x] Admin reject → no change (logged)
- [x] No adjustment without approval (unless admin created it)

---

## 9) Billing & invoicing (monthly automation)

### 9.1 Pricing model
- [x] `price_lists.rules_json` schema finalized (v1)
- [x] UI to edit price list per client (backend endpoints)
- [x] Validation for required fields (currency, storage model, etc.) (backend validates `rules_json` on price list upsert)

### 9.2 Billing events generation
- [x] Inbound confirmed → billing events created
- [x] Dispatch confirmed → billing events created
- [x] Daily storage cron → storage-day events generated from balances (`POST /api/v1/billing/run-daily-storage`)
- [x] Printing/labels → printing events created (PRINT_LABEL billing event created on packing slip generation)

### 9.3 Invoice generation
- [x] Admin selects client + period start/end (+ optional language override)
- [x] System aggregates events into invoice + lines
- [x] Invoice status flow: Draft → Issued → Paid (manual v1)
- [x] Every invoice line is traceable (drilldown) (invoice lines endpoint + drilldown json)
- [x] Invoice PDF generation localized (EN/BS/DE) (basic)
- [x] Store PDF in `files` and allow download by permission/tenant

---

## 10) Documents center

- [x] Store generated docs: receiving, dispatch, discrepancy, invoices, packing slips, reports (invoices implemented)
- [x] Search/filter by type/date (basic)
- [x] Download rules enforced by role + tenant/client scoping

---

## 11) Reports & exports

- [x] Inventory snapshot report (filters) (API + CSV)
- [x] Expiry report (API + CSV)
- [x] Movement history report (ledger search) (API + CSV)
- [x] Inbound/outbound volumes report (API + CSV)
- [x] Discrepancy report (API + CSV)
- [x] Billing events report (API + CSV)
- [x] Export CSV/Excel (CSV implemented; Excel later)
- [x] PDF exports where appropriate (dispatch/inbound/return/invoice + packing slip + location label PDFs)
- [x] Client can export only their own data (reports endpoints enforce client scoping)
- [x] Admin can export across clients (admin can run reports without client restriction within tenant)

---

## 12) Notifications (email minimum)

- [x] Account invites email (localized) (email outbox)
- [x] Password reset email (localized) (email outbox)
- [x] Optional inbound received email (env toggle; localized per user language)
- [x] Optional outbound dispatched email (env toggle; localized per user language)
- [x] Invoice issued email (localized; env toggle)
- [x] Template management strategy (keys + params) (documented in `docs/notifications.md`)

---

## 13) Audit trail (hard requirement)

- [x] All write operations create audit log entry
- [x] Audit captures actor, action, entity, before/after (when applicable) (service + schema)
- [x] Audit captures IP/user-agent when available (wired in all API write endpoints)
- [x] Admin UI to view/search audit logs (minimum) (API endpoint)

---

## 14) Security & compliance hardening (v1)

- [x] Role/permission checks on every protected endpoint (warehouse-staff/admin routes use role deps; client user restrictions enforced in handlers)
- [x] Tenant/client scoping enforced in queries (critical gaps fixed; ongoing verification)
- [x] Rate limiting for auth endpoints
- [x] Input validation for all endpoints (core schemas enforce qty/date/min lengths; endpoints still validate domain rules)
- [x] Secure file access (auth-checked streaming)
- [x] Soft-delete strategy where needed (confirm which entities) (v1: no destructive delete endpoints exposed; use `is_active` where available; revisit when adding delete APIs)

---

## 15) Testing plan (must-have)

### 15.1 Unit tests
- [x] Inventory ledger → balance update correctness
- [x] Reservation logic correctness
- [x] Invoice generation correctness (events → lines)
- [x] Auth dependency enforces tenant_id + client_id consistency (security regression tests)

### 15.2 Integration tests
- [x] Inbound full flow (integration test; requires TEST_DATABASE_URL)
- [x] Outbound full flow (integration test; requires TEST_DATABASE_URL)
- [x] Tenant/client scoping (ID tampering tests) (integration tests; requires TEST_DATABASE_URL)

### 15.3 E2E tests (Playwright)
- [x] Client creates outbound order (Playwright spec added; requires running FE+BE)
- [x] Worker picks and dispatches (Playwright spec added; requires running FE+BE)
- [x] Invoice generated + downloadable PDF (Playwright spec added; requires running FE+BE)

---

## 16) DevOps & deployment

- [x] Dockerfiles: backend, frontend
- [x] Docker Compose: Postgres, Redis, MinIO, backend, frontend
- [x] MinIO integration for object storage (dev)
- [x] NGINX reverse proxy config (optional v1) (`deploy/nginx.systemecom.conf`)
- [x] CI/CD pipeline (GitHub Actions): test + build (basic)
- [x] Environments: dev/staging/prod `.env` strategy (`docs/environments.md` + README link)
- [x] Observability: logs + basic health checks

---

## 17) “Definition of Done” (system-level)

- [x] All flows scan-validated and auditable (audit_log on writes; scan-first worker flows enforce expected scans + supervisor override)
- [x] Client isolation enforced at backend
- [x] Multi-language works across UI + PDFs + emails (EN/BS/DE UI; multilingual PDFs/emails)
- [x] Inventory matches ledger (reconcilable)
- [x] Invoices traceable to events
- [x] Worker UI usable on mobile (PWA) (installable manifest + mobile viewport)
- [x] Admin portal operationally complete (v1 scope: all core ops pages exist and are wired end-to-end)
- [x] Document center stores/retrieves PDFs securely
- [x] CI/CD runs tests and builds containers

---

## Open questions (remaining)

- [x] **Inventory unit policy**: do we support carton/pallet conversions in v1, or store everything in “pieces” only? (tracked in section 0)
- [x] **Expiry/lot rules**: is FEFO mandatory when expiry is enabled, or optional per client/product? (tracked in section 0)
- [x] **Billing tax**: do invoices need VAT/tax lines in v1, and if yes what default tax rate per client? (tracked in section 0)


