# SystemECOM — User Guide (Sidebar Tabs)

This guide explains **each sidebar tab** in SystemECOM: what it means, what features it has, and how to use it.

The UI is split into three main experiences (based on your role):
- **Admin**: manage tenants, clients, master data, operations, billing, audits
- **Client Portal**: client-facing inventory + orders + invoices + documents
- **Worker**: scan-based operational flows (receive, put-away, pick, pack/dispatch, returns, discrepancies)

---

## 1) Getting started

### Login
- Go to `/login`
- The login field accepts **username OR email**
- Choose your language (UI supports **en / bs / de** where implemented)

### Entry points (quick navigation)
- **Admin**: `/<locale>/admin/dashboard`
- **Client Portal**: `/<locale>/portal/dashboard`
- **Worker**: `/<locale>/worker/home`

> Replace `<locale>` with `en`, `bs`, or `de`.

---

## 2) Common UI patterns (used across tabs)

### IDs and scanning
Many operational screens use UUIDs (IDs) for:
- inbound IDs / outbound IDs / task IDs
- product IDs
- location IDs (and location barcodes)

In Worker screens you’ll see **scanner-friendly inputs** that are meant to accept barcode-scanner “keyboard input”.

### Where do I get IDs?
- **Client IDs**: `Admin → Clients` table (shows client ID)
- **Warehouse IDs**: `Admin → Warehouses` dropdown (shows warehouse ID)
- **Product IDs**: currently shown in listings/flows as UUIDs (e.g., pick lines show product_id)
- **Location IDs**: shown in `Admin → Warehouses → Locations` table and used across worker flows
- **Inbound IDs / Outbound IDs**: shown after creation and in list tables

### Downloads
Documents (PDFs/exports) are **protected** and require being logged in.
- If a download fails: re-login, then retry.

### “Supervisor override”
Some worker actions block “wrong scans” (safety):
- If the **product scan** or **from-location scan** doesn’t match what the task expects, the system prompts for a **Supervisor Override**.
- Use override only for real-world exceptions (damaged labels, relocation, emergency pick, etc.).

---

## 2.1) Core use cases (end-to-end workflows)

This section answers: **products entering**, **moving inside**, **leaving**, and **being returned**, including **pieces vs bulk** and **multiple lines/inputs**.

### Use case A — Products entering the warehouse (Inbound receiving)
**Who uses it**: Client (request/announce), Admin (create/start), Worker (scan receive)

**Normal flow (UI)**
- **Create inbound header**
  - Admin: `Admin → Inbound → Create + Start`
  - Client: `Client → Inbound → Submit inbound` (creates the inbound header; expected lines are not enforced in v1 UI)
- **Receive into STAGING**
  - Worker: `Worker → Inbound (Receive)` (or Admin “Scan line” tool)
  - Scan/enter: product **barcode**, STAGING **location**, and **qty**
- **Result**
  - Inventory is now in **STAGING** and will appear as **Put-away tasks**

**Pieces vs bulk**
- Current UI screens enter **qty only** → treated as **pieces**.
- Backend also supports `uom = piece/carton/pallet` for inbound scans, but the UI does not expose a UOM selector yet.

### Use case B — Moving products inside the warehouse (Put-away)
**Who uses it**: Worker (normal), Admin (backoffice)

**Normal flow**
- Worker: `Worker → Put-away`
- Select a task (what’s sitting in STAGING)
- Scan/enter:
  - expected **product**
  - expected **from-location**
  - destination **to-location** (should be STORAGE)
  - qty
- Confirm move (Supervisor override is available for wrong scans)

### Use case C — Products leaving the warehouse (Outbound shipping)
**Who uses it**: Client (request), Admin (approve & generate pick work), Worker (pick/pack/dispatch)

**Normal flow (UI)**
- **Create outbound order**
  - Client: `Client → Outbound Order` (creates an outbound with one line in the current UI)
- **Approve + generate picking**
  - Admin: `Admin → Outbound → Approve + Generate picks`
- **Pick**
  - Worker: `Worker → Picking`
  - Start task → load lines → scan product + from-location + to PACKING location → confirm picks → complete task
- **Pack**
  - Worker: `Worker → Pack` (confirm packing by outbound ID)
- **Dispatch**
  - Worker: `Worker → Dispatch` (confirm dispatch by outbound ID + packing location ID)

**Pieces vs bulk**
- Outbound lines support `uom = piece/carton/pallet` in the backend.
- Current Client/Admin UIs create outbound lines in **pieces** (no UOM selector yet).

**Multiple lines / multiple products**
- Backend supports **multiple outbound lines** per order.
- Current Client UI creates **one line per submission** (multi-line UI can be added later; API already supports it).

### Use case D — Products being returned (Returns processing)
**Who uses it**: Worker (process), Admin (review/visibility)

**Normal flow**
- Worker/Admin: open Returns screen
- Add return scan line:
  - product, qty
  - disposition: **RESTOCK / QUARANTINE / SCRAP**
  - optional destination location (recommended for RESTOCK/QUARANTINE)
- Complete the return

### Use case E — Inventory mismatch / damage / unknown stock (Discrepancies)
**Who uses it**: Worker (submit), Admin/Supervisor (approve/reject)

**Normal flow**
- Worker: `Worker → Discrepancies (Report Issue)` → submit a discrepancy (location, product, optional batch, counted qty, reason)
- Admin: `Admin → Discrepancies` → approve or reject

### Do we handle “pieces”, “bulk”, and “types”?

- **Pieces vs bulk (carton/pallet)**:
  - **Yes (backend)**: quantity inputs can be `piece`, `carton`, or `pallet` and are converted to pieces.
  - **UI today**: most forms only ask for `qty` and treat it as **pieces**. If you need carton/pallet entry right now, use the API or extend the UI.
- **Multiple inputs (many products / many lines)**:
  - **Inbound receiving**: yes — you can scan **multiple different products** into the same inbound by scanning multiple times.
  - **Outbound**: yes — backend supports **multiple lines** per order (UI currently submits one line per form submission).
  - **Returns**: yes — you can add multiple return lines, then complete.
- **Product “types”**:
  - **Category** is supported (used for filtering in Client Inventory).
  - **Batch/expiry fields** exist for inbound scans (backend supports them), but current UI defaults them to empty unless extended.

## 3) Admin sidebar tabs (Admin)

### Dashboard
**Meaning**: a high-level operational snapshot.

**Features**
- Today inbound count
- Today outbound count
- Pending discrepancies
- Occupied pallet positions
- Expiry risk counts (30/60/90 days)
- Top clients (by outbound activity)
- 14-day inbound/outbound trend

**How to use (step-by-step)**
- **Step 1**: Open `Admin → Dashboard`.
- **Step 2**: Check:
  - **Today inbound/outbound**: expected workload for today.
  - **Discrepancies pending**: items that require supervisor/admin decision.
  - **Occupied positions**: rough capacity indicator (distinct STORAGE locations with stock).
  - **Expiring (30/60/90)**: stock risk.
  - **Top clients** and **Trend**: volume insight.

### Clients
**Meaning**: customer accounts under your tenant.

**Features**
- Create client
- Set **preferred language**, **billing currency** (BAM/EUR), and **VAT rate**
- List existing clients (ID is shown and used across screens)

**How to use (step-by-step)**
- **Step 1 (Create)**: In `Admin → Clients`, fill:
  - **Client name** (required): e.g. `ACME d.o.o.`
  - **Language** (required): `en` / `bs` / `de`
  - **Currency** (required): `BAM` or `EUR`
  - **VAT rate** (required): decimal between `0` and `1` (Bosnia default is commonly `0.17`)
- **Step 2**: Click **Create**.
- **Step 3 (Verify)**: The client appears in the table. Copy the **client ID** for later (products, inbound/outbound, invoicing).

**Common mistakes**
- **VAT rate entered as 17 instead of 0.17**: VAT rate is a fraction, not a percent.

### Warehouses
**Meaning**: physical warehouses and their internal structure.

**Features**
- Create warehouse
- Select warehouse to manage details
- Create zones (STAGING / STORAGE / PACKING / RETURNS / QUARANTINE)
- Create locations (code + barcode value)
- **Bulk import locations (CSV)**
- **Download location labels PDF**

**How to use (step-by-step)**
- **Step 1 (Create warehouse)**:
  - Field **Warehouse name** (required): e.g. `Sarajevo WH`
  - Click **Create**
- **Step 2 (Select warehouse)**:
  - Use the dropdown and pick your warehouse (it shows the **warehouse ID**).
- **Step 3 (Create zones)**:
  - **Zone name** (required): e.g. `STAGING-01`, `STORAGE-A`, `PACK-01`
  - **Zone type** (required): choose one of:
    - `STAGING` (receiving)
    - `STORAGE` (main inventory)
    - `PACKING` (picked/packed staging)
    - `RETURNS` / `QUARANTINE` (optional)
  - Click **Add**
- **Step 4 (Create locations)**:
  - **Zone** (required): pick the zone you want the location in
  - **Code** (required): human label, e.g. `A-01-01`
  - **Barcode** (required): what gets scanned, e.g. `LOC-A-01-01` (print this)
  - Click **Add**
- **Step 5 (Bulk import locations - optional)**:
  - Select **Zone**
  - Pick CSV file
  - Click **Upload**
  - Review created count + errors table
- **Step 6 (Labels)**:
  - Click **Download PDF** and print labels for your locations.

**What you should see**
- Zones table populated with IDs and types.
- Locations table showing code, barcode, and zone ID.

**Common mistakes**
- Creating STAGING locations in a STORAGE zone: receiving scans will fail because staging must be in a `STAGING` zone.

### Products
**Meaning**: master product catalog for client inventory.

**Features**
- Create product (client_id, SKU, name, optional category, optional barcode)
- Configure conversions for bulk handling (carton/pallet) on products (if used)
- Filter listing by `client_id` (by entering it before refresh)
- **Bulk import products (CSV)** with error reporting

**How to use (step-by-step)**
- **Step 1 (Choose client)**:
  - Fill **clientId** (required): paste a client UUID from `Admin → Clients`.
- **Step 2 (Create product)**: fill:
  - **SKU** (required): e.g. `SKU-0001`
  - **Name** (required): e.g. `Mineral Water 0.5L`
  - **Category** (optional): e.g. `Beverages`
  - **Barcode** (optional but recommended if scanning): e.g. `3871234567890`
  - Click **Create**
- **Step 3 (Verify)**:
  - Click **Refresh list**.
  - Confirm it appears in the products table (with client_id and product id).

**Bulk / carton / pallet**
- Backend supports `piece/carton/pallet` conversions using product `carton_qty` and `pallet_qty`.
- The current Products UI does not expose carton/pallet fields; if you need bulk conversions now, set them via API/DB/admin extension.

**Common mistakes**
- Forgetting clientId: product creation/import will fail or create in the wrong scope.

### Inbound
**Meaning**: receiving stock into the warehouse.

**Features**
- Create inbound and immediately **Start receiving**
- Receive by scanning lines into a **STAGING** location (barcode + qty)
- Inbound list (status, client, warehouse)

**How to use (step-by-step)**
- **Step 1 (Create + Start)**:
  - **Client** (required): select from dropdown
  - **Warehouse** (required): select from dropdown
  - Click **Create + Start**
  - Copy the shown **Inbound ID** (also auto-fills “Scan line” inbound id).
- **Step 2 (Scan into STAGING)**:
  - **Inbound ID** (required): paste/scan inbound UUID
  - **Staging location** (required): pick a STAGING location from dropdown
  - **Product barcode** (required): scan/enter the product barcode
  - **Qty** (required): integer >= 1
  - Click **Receive**
- **Step 3 (Repeat)**:
  - For multiple products or multiple cartons-as-pieces: repeat Step 2 as many times as needed.
- **Step 4 (Verify)**:
  - In the inbound list table, verify status and IDs.
  - Go to `Admin → Put-away` or `Worker → Put-away` to move stock into STORAGE.

**Common mistakes**
- Using a staging location that is not in a STAGING zone.
- Scanning a barcode that doesn’t exist on any product.

### Put-away
**Meaning**: moving received stock from STAGING into STORAGE.

**Features**
- Shows put-away tasks (what’s on hand in STAGING)
- Confirm move to a destination STORAGE location (to_location_id + qty)

**How to use (step-by-step)**
- **Step 1**: Open `Admin → Put-away`.
- **Step 2**: Fill:
  - **To location (storage)** (required): destination STORAGE location UUID
  - **Qty** (required): integer >= 1 (how much to move from that task line)
- **Step 3**: In the tasks table:
  - Find the correct row (product_id + from_location_id)
  - Click **Move**
- **Step 4**: Click **Refresh** and confirm the row decreases/disappears.

**Common mistakes**
- Using a destination that is not a STORAGE location.
- Entering qty greater than on-hand (will fail).

### Outbound
**Meaning**: approving outbound orders and generating pick tasks.

**Features**
- Pick an outbound order
- **Approve** it
- **Generate picks** for it (creates pick tasks/lines)
- View list of outbound orders and statuses

**How to use (step-by-step)**
- **Step 1**: Ensure an outbound order exists:
  - Client creates via `Client → Outbound Order`, or use API/backoffice.
- **Step 2**: Open `Admin → Outbound`.
- **Step 3**: Select the outbound in the dropdown (shows order number + status).
  - If needed, paste an ID into **Outbound ID (manual override)**.
- **Step 4**: Click **Approve + Generate picks**.
- **Step 5 (Verify)**:
  - Status should change.
  - Go to `Worker → Picking` (or `Admin → Picking`) to see tasks and lines.

**Common mistakes**
- Trying to generate picks before stock is available or before inbound has been put away.

### Picking
**Meaning**: pick task execution (admin view).

**Features**
- Start a picking task
- View task lines
- Select a line (auto-fill product/from-location) and scan pick into a PACKING location
- Complete the task

**How to use (step-by-step)**
- **Step 1**: Open `Admin → Picking`.
- **Step 2 (Start task)**:
  - Choose a **task** from the dropdown
  - Click **Start**
- **Step 3 (Pick scan)**:
  - In “Pick line (auto-fill)”, select a line to auto-fill **product_id** and **from_location_id** and remaining qty
  - Select a **packing location** (must be a PACKING zone location)
  - Click **Pick**
- **Step 4 (Complete)**:
  - Click **Complete task**
- **Step 5 (Verify)**:
  - Task status updates
  - Next steps: `Pack` then `Dispatch`

### Packing/Dispatch
**Meaning**: packing confirmation and dispatch confirmation (admin view).

**Features**
- Confirm packing for an outbound order
- Confirm dispatch (requires outboundId + packingLocationId)

**How to use (step-by-step)**
- **Packing**
  - **Outbound ID** (required): outbound UUID
  - Click **Confirm packing**
- **Dispatch**
  - **Outbound ID** (required)
  - **Packing location ID** (required): packing location UUID (where picked goods were staged)
  - Click **Confirm dispatch**

**What you should see**
- No error message after submit.
- Documents/PDFs should appear in `Admin → Documents` for packing/dispatch as applicable.

### Returns
**Meaning**: receiving returns back into stock (or quarantine/scrap).

**Features**
- Add return scan lines (product_id, qty, disposition)
- Dispositions: **RESTOCK**, **QUARANTINE**, **SCRAP**
- Complete return
- View list of returns

**How to use (step-by-step)**
- **Step 1 (Add return line)**:
  - **Return ID** (required): UUID of the return record
  - **Product ID** (required): product UUID
  - **Qty** (required): integer >= 1
  - **Disposition** (required): RESTOCK / QUARANTINE / SCRAP
  - **To location**:
    - required for RESTOCK/QUARANTINE in real operations
    - can be left blank for SCRAP (depends on your policy)
  - Click **Add line**
- **Step 2 (Complete)**:
  - Click **Complete return**
- **Step 3 (Verify)**:
  - Return appears/updates in the list and inventory is adjusted accordingly.

### Discrepancies
**Meaning**: exception handling for inventory count differences.

**Features**
- View discrepancies (status, delta, product, location)
- Approve or reject discrepancies (only while PENDING)

**How to use (step-by-step)**
- **Step 1**: Open `Admin → Discrepancies` and click **Refresh**.
- **Step 2**: For each PENDING discrepancy:
  - Review **delta**, **product_id**, **location_id**
  - Click **Approve** to apply the adjustment, or **Reject** to discard it
- **Step 3**: Verify status updates from PENDING to APPROVED/REJECTED.

### Invoices
**Meaning**: generate, issue, and manage invoices.

**Features**
- Generate invoice for a client for a date range (language uses current UI locale)
- List invoices (status, client, period, totals)
- Download PDF (if generated)
- Issue invoice
- View invoice lines
- Mark paid

**How to use (step-by-step)**
- **Pre-req**: Configure price list first in `Admin → Settings`.
- **Step 1 (Generate)**:
  - **Client ID** (required): client UUID
  - **Start date** (required): `YYYY-MM-DD`
  - **End date** (required): `YYYY-MM-DD`
  - Click **Generate**
- **Step 2 (Verify)**:
  - Invoice appears in the table with totals and currency
- **Step 3 (Review lines)**:
  - Click **Lines** to view invoice line items
- **Step 4 (PDF)**:
  - If **PDF** button is shown, click it to download
- **Step 5 (Issue)**:
  - Click **Issue** to mark invoice as issued (and trigger optional notifications if enabled)
- **Step 6 (Mark paid)**:
  - Click **Mark paid** when payment is received

### Reports
**Meaning**: downloadable operational and billing exports.

**Features**
- Choose format: CSV/JSON
- Download:
  - inventory snapshot
  - expiry
  - movements
  - discrepancies
  - inventory reconcile
  - volumes (date range)
  - billing events (date range)

**How to use (step-by-step)**
- **Step 1**: Choose **format**: `csv` (Excel) or `json` (integrations).
- **Step 2**: For range reports, fill:
  - **start**: `YYYY-MM-DD`
  - **end**: `YYYY-MM-DD`
- **Step 3**: Click the report button you need:
  - Inventory snapshot / Expiry / Movements / Discrepancies / Inventory reconcile
  - Volumes (needs start/end)
  - Billing events (needs start/end)
- **Step 4**: Your browser downloads the file.

### Audit
**Meaning**: immutable history of system write actions (for traceability).

**Features**
- View audit rows: time, action, entity, actor

**How to use (step-by-step)**
- **Step 1**: Open `Admin → Audit`.
- **Step 2**: Click **Refresh**.
- **Step 3**: Read:
  - **time**: when it happened
  - **action**: e.g. `inbound.create`, `outbound.approve`, etc.
  - **entity**: type + id
  - **actor**: user id (or blank for system actions)

### Users
**Meaning**: manage user accounts and invitations.

**Features**
- Create users directly (email, password, full name, role, language)
- Roles include: WAREHOUSE_ADMIN, WAREHOUSE_SUPERVISOR, WAREHOUSE_WORKER, DRIVER, CLIENT_USER
- Invite a **client user** by email (invite flow)
- List users with search + pagination

**How to use (step-by-step)**
- **Create direct (internal staff)**
  - **email** (required)
  - **password** (required)
  - **full name** (optional but recommended)
  - **role** (required): choose correct RBAC role
  - **language** (required)
  - **client**: only set when role is `CLIENT_USER`
  - Click **Create**
- **Invite client user**
  - **email** (required)
  - **client** (required)
  - **invite language** (required)
  - Click **Send invite**
- **Verify**
  - Confirm the user appears in the users table.

### Settings
**Meaning**: billing configuration (price lists) per client.

**Features**
- Select client
- View current price list (if exists)
- Edit **rules JSON** + effective date
- Save with validation errors shown (if rules are invalid)

**How to use (step-by-step)**
- **Step 1**: Select a client from the dropdown.
- **Step 2**: Set **effectiveFrom** (date `YYYY-MM-DD`).
- **Step 3**: Edit **rules JSON** in the editor.
  - Keep it valid JSON (commas, quotes, braces).
- **Step 4**: Click **Save price list**.
- **Step 5**: If you see an error message, fix the JSON/rules and save again.

**Tip (safe workflow)**
- Start from the default JSON template shown in the editor and modify values gradually.

### Documents
**Meaning**: all stored/generated files (PDFs, exports, etc.).

**Features**
- Filter by file type and created date range
- Search by name/type
- Download any file (authorized)

**How to use (step-by-step)**
- **Step 1**: (Optional) Filter:
  - **fileType**: e.g. `INVOICE_PDF`, `INBOUND_PDF`, `DISPATCH_PDF` (depends on backend naming)
  - **createdAfter / createdBefore**: date/time strings (as used by API)
- **Step 2**: Use the search box to find by name/type.
- **Step 3**: Click **Download** on the row you need.
- **Step 4**: If download fails, re-login and retry.

---

## 4) Client Portal sidebar tabs (Client)

### Dashboard
**Meaning**: landing page for client users.

**Status**: currently a **placeholder** screen (inventory/orders/invoices/documents are in their own tabs).

### Inventory
**Meaning**: read-only view of the client’s inventory balances.

**Features**
- Filters:
  - warehouse_id
  - product category
  - expiry date range (after/before)
- Grouped summary by product (on hand / reserved / available)
- Pagination (50 per page)
- Click a product row to open **per-location breakdown**

**How to use (step-by-step)**
- **Step 1**: (Optional) Fill filters:
  - **warehouseId**: paste the warehouse UUID (recommended)
  - **productCategory**: exact text match category
  - **expiryAfter / expiryBefore**: date strings (if expiry is used for your products)
- **Step 2**: Review the grouped rows:
  - **on hand**: total pieces in stock
  - **reserved**: allocated to outbound but not yet picked
  - **available**: usable stock
- **Step 3**: Click a product row to open the **per-location breakdown** panel.

### Inbound
**Meaning**: request/announce incoming shipments (inbound creation).

**Features**
- Create inbound with:
  - client_id, warehouse_id, supplier, notes
  - one line (product_id, expected_qty)

**How to use (step-by-step)**
- Fill:
  - **clientId** (required): your client UUID
  - **warehouseId** (required): destination warehouse UUID
  - **supplier** (optional)
  - **notes** (optional)
  - **productId** (required): product UUID
  - **expectedQty** (required): integer >= 1 (in pieces)
- Click **Submit inbound**
- Copy the created inbound id and share with warehouse staff for receiving.

### Outbound Order
**Meaning**: create outbound shipping requests.

**Features**
- Create outbound with:
  - client_id, warehouse_id
  - destination name + address
  - one line (product_id, qty)

**How to use (step-by-step)**
- Fill:
  - **clientId** (required)
  - **warehouseId** (required)
  - **destination name** (required)
  - **destination address** (required)
  - **productId** (required)
  - **qty** (required): integer >= 1 (pieces)
- Click **Submit**
- Copy the created outbound id/order number.
- Track status in **Orders** (approval + picking + dispatch is done by warehouse staff/admin).

### Orders
**Meaning**: list of outbound orders and their statuses.

**Features**
- View order number, status, warehouse, id

**How to use**
- Use it to monitor if your order is pending, picking, packed, dispatched, etc.

### Returns
**Meaning**: view returns created for your client.

**Features**
- List return status, warehouse, id

**How to use**
- Use it for visibility; return processing is usually done by warehouse staff.

### Invoices
**Meaning**: invoice list and PDF download.

**Features**
- List invoices (status, period, total)
- Download invoice PDF when available

**How to use**
- Download PDFs for accounting; contact admin if invoice is missing or totals are unexpected.

### Reports
**Meaning**: client downloads for operational reporting.

**Features**
- Same report endpoints as admin (inventory snapshot, movements, expiry, etc.)
- CSV/JSON formats + optional date range

**How to use**
- Use for reconciliation and planning (expiry + movements are most common).

### Documents
**Meaning**: client access to generated documents.

**Features**
- Filter by file type / date range
- Download documents

**How to use**
- Use to retrieve packing slips, dispatch PDFs, invoices, and exports relevant to your client.

### Settings
**Meaning**: client preferences page.

**Status**: currently a **placeholder** (intended for client preferences/account settings).

---

## 5) Worker sidebar tabs (Worker)

### Home
**Meaning**: worker landing page with quick actions.

**Features**
- Buttons that jump directly into Receive / Put-away / Pick / Pack / Dispatch / Returns / Report Issue

### Inbound (Receive)
**Meaning**: scan goods into STAGING for an inbound.

**Features**
- Start receiving (by inbound ID)
- Scan line into staging (product barcode, staging location ID, qty)
- Inbound list with status

**How to use (step-by-step)**
- **Step 1 (Start receiving)**:
  - Scan/enter **Inbound ID**
  - Click **Start**
- **Step 2 (Scan into staging)**:
  - Scan **Product barcode**
  - Scan **Staging location ID** (STAGING location)
  - Enter **Qty**
  - Click **Confirm scan**
- **Step 3**: Repeat Step 2 for every item/carton (as pieces).

### Put-away
**Meaning**: move goods from STAGING into STORAGE locations.

**Features**
- Choose a task from the list
- Scan product + from-location + to-location
- Blocks wrong scans (Supervisor override supported)

**How to use (step-by-step)**
- **Step 1**: Click **Refresh** and select a task.
- **Step 2**: Scan fields:
  - **Product (scan)** must match expected
  - **From location (scan)** must match expected
  - **To location (scan)** should be a STORAGE location
  - **Qty** to move
- **Step 3**: Click **Confirm put-away**.
- **If blocked**: open **Supervisor override** and proceed only if approved.

### Picking
**Meaning**: pick reserved stock for outbound orders into PACKING.

**Features**
- Start picking task (task ID)
- Load task lines
- Select a line and scan:
  - product
  - from-location
  - to PACKING location
- Blocks wrong scans (Supervisor override supported)
- Complete the task

**How to use (step-by-step)**
- **Step 1 (Start task)**:
  - Scan/enter **Task ID**
  - Click **Start**
  - Click **Load lines**
- **Step 2 (Pick line)**:
  - Select a line from dropdown (it shows what to pick and from where)
  - Scan:
    - **Product** (must match)
    - **From location** (must match)
    - **To packing location** (PACKING location)
  - Enter **Qty**
  - Click **Confirm pick**
- **Step 3 (Complete)**:
  - When all lines are fully picked, click **Complete task**

### Packing/Dispatch (Pack)
**Meaning**: confirm packing step for an outbound order.

**Features**
- Confirm packing by outbound ID

**How to use (step-by-step)**
- Scan/enter **Outbound ID**
- Click **Confirm pack**
- If it fails, verify the outbound has been picked and is ready for packing.

### Packing/Dispatch (Dispatch)
**Meaning**: confirm the outbound has physically left the warehouse.

**Features**
- Confirm dispatch using outbound ID + packing location ID

**How to use (step-by-step)**
- Scan/enter **Outbound ID**
- Scan/enter **Packing location ID**
- Click **Confirm dispatch**

### Returns
**Meaning**: process return lines into restock/quarantine/scrap.

**Features**
- Add return line (return ID, product ID, qty, disposition, optional destination location)
- Complete return

**How to use (step-by-step)**
- Scan/enter **Return ID**
- Scan/enter **Product ID**
- Enter **Qty**
- Choose **Disposition**:
  - RESTOCK (back to sellable stock)
  - QUARANTINE (hold)
  - SCRAP (discard)
- Scan **To location** when applicable (recommended for RESTOCK/QUARANTINE)
- Click **Add line**
- Click **Complete return** when finished

### Discrepancies (Report Issue)
**Meaning**: submit an inventory discrepancy for review.

**Features**
- Create discrepancy with:
  - location_id
  - product_id
  - optional batch_id
  - counted_qty
  - reason

**How to use (step-by-step)**
- Scan **Location ID**
- Scan **Product ID**
- (Optional) scan/enter **Batch ID**
- Enter **Counted qty**
- Enter **Reason** (required): e.g. `Damaged case`, `Missing 3 pcs`, `Label unreadable`
- Click **Submit**
- Admin reviews it in `Admin → Discrepancies`


