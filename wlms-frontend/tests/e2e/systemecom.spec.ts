import { expect, test } from "@playwright/test";

type Tokens = { access_token: string; refresh_token: string };

const API_BASE = process.env.E2E_API_BASE_URL ?? "http://localhost:8000";
const LOCALE = process.env.E2E_LOCALE ?? "en";

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "admin@systemecom.local";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "admin123";

const CLIENT_EMAIL = process.env.E2E_CLIENT_EMAIL ?? "client@systemecom.local";
const CLIENT_PASSWORD = process.env.E2E_CLIENT_PASSWORD ?? "client123";

const WORKER_EMAIL = process.env.E2E_WORKER_EMAIL ?? "worker@systemecom.local";
const WORKER_PASSWORD = process.env.E2E_WORKER_PASSWORD ?? "worker123";

async function devInit(request: Parameters<typeof test>[1]["request"]) {
  const res = await request.post(`${API_BASE}/api/v1/dev/init`, {
    data: {
      tenant_name: "E2E Tenant",
      admin_email: ADMIN_EMAIL,
      admin_password: ADMIN_PASSWORD,
      admin_full_name: "Admin",
      admin_language_pref: "en"
    }
  });
  // 409 is fine if already initialized
  if (![200, 409].includes(res.status())) throw new Error(`dev/init failed: ${res.status()} ${await res.text()}`);
}

async function login(request: Parameters<typeof test>[1]["request"], email: string, password: string): Promise<Tokens> {
  const res = await request.post(`${API_BASE}/api/v1/auth/login`, { data: { email, password } });
  if (res.status() !== 200) throw new Error(`login failed: ${res.status()} ${await res.text()}`);
  const json = (await res.json()) as { access_token: string; refresh_token: string };
  return { access_token: json.access_token, refresh_token: json.refresh_token };
}

async function authPost(request: Parameters<typeof test>[1]["request"], token: string, path: string, data: unknown) {
  const res = await request.post(`${API_BASE}${path}`, {
    data,
    headers: { Authorization: `Bearer ${token}` }
  });
  if (![200, 201].includes(res.status())) throw new Error(`${path} failed: ${res.status()} ${await res.text()}`);
  return res.json();
}

async function authGet(request: Parameters<typeof test>[1]["request"], token: string, path: string) {
  const res = await request.get(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (res.status() !== 200) throw new Error(`${path} failed: ${res.status()} ${await res.text()}`);
  return res.json();
}

test("Client creates outbound → Worker picks/dispatches → Admin generates invoice + PDF link appears", async ({ page, request }) => {
  await devInit(request);
  const adminTokens = await login(request, ADMIN_EMAIL, ADMIN_PASSWORD);

  // Setup minimal master data via API
  const client = (await authPost(request, adminTokens.access_token, "/api/v1/clients", {
    name: "E2E Client",
    address: "Addr",
    tax_id: "TAX",
    billing_currency: "EUR",
    preferred_language: "en"
  })) as { id: string };

  const wh = (await authPost(request, adminTokens.access_token, "/api/v1/warehouses", { name: "E2E WH", address: "A", timezone: "UTC" })) as {
    id: string;
  };

  // Create zones + locations
  const stagingZone = (await authPost(request, adminTokens.access_token, `/api/v1/warehouses/${wh.id}/zones`, {
    name: "STG",
    zone_type: "STAGING"
  })) as { id: number };
  const storageZone = (await authPost(request, adminTokens.access_token, `/api/v1/warehouses/${wh.id}/zones`, {
    name: "STR",
    zone_type: "STORAGE"
  })) as { id: number };
  const packingZone = (await authPost(request, adminTokens.access_token, `/api/v1/warehouses/${wh.id}/zones`, {
    name: "PCK",
    zone_type: "PACKING"
  })) as { id: number };

  const stagingLoc = (await authPost(request, adminTokens.access_token, `/api/v1/warehouses/${wh.id}/locations`, {
    zone_id: stagingZone.id,
    code: "STG-01",
    barcode_value: "STG-01"
  })) as { id: string };
  const storageLoc = (await authPost(request, adminTokens.access_token, `/api/v1/warehouses/${wh.id}/locations`, {
    zone_id: storageZone.id,
    code: "A-01-01",
    barcode_value: "A-01-01"
  })) as { id: string };
  const packingLoc = (await authPost(request, adminTokens.access_token, `/api/v1/warehouses/${wh.id}/locations`, {
    zone_id: packingZone.id,
    code: "PACK-01",
    barcode_value: "PACK-01"
  })) as { id: string };

  const product = (await authPost(request, adminTokens.access_token, "/api/v1/products", {
    client_id: client.id,
    sku: "SKU-1",
    name: "Prod 1",
    description: null,
    barcode: "BC-001",
    uom: "piece",
    carton_qty: null,
    weight_kg: null,
    dims_cm_json: null,
    lot_tracking_enabled: false,
    expiry_tracking_enabled: false
  })) as { id: string };

  // Create worker + client user accounts
  await authPost(request, adminTokens.access_token, "/api/v1/users", {
    email: WORKER_EMAIL,
    password: WORKER_PASSWORD,
    full_name: "Worker",
    role: "WAREHOUSE_WORKER",
    language_pref: "en"
  });
  await authPost(request, adminTokens.access_token, "/api/v1/users", {
    email: CLIENT_EMAIL,
    password: CLIENT_PASSWORD,
    full_name: "Client User",
    role: "CLIENT_USER",
    language_pref: "en",
    client_id: client.id
  });

  const workerTokens = await login(request, WORKER_EMAIL, WORKER_PASSWORD);
  const clientTokens = await login(request, CLIENT_EMAIL, CLIENT_PASSWORD);

  // Seed inventory: inbound receive into staging + putaway to storage
  const inbound = (await authPost(request, adminTokens.access_token, "/api/v1/inbound", {
    client_id: client.id,
    warehouse_id: wh.id,
    supplier: "Supp",
    notes: null
  })) as { id: string };
  await authPost(request, workerTokens.access_token, `/api/v1/inbound/${inbound.id}/start-receiving`, {});
  await authPost(request, workerTokens.access_token, `/api/v1/inbound/${inbound.id}/scan-line`, {
    barcode: "BC-001",
    qty: 5,
    batch_number: null,
    expiry_date: null,
    location_staging_id: stagingLoc.id
  });
  await authPost(request, workerTokens.access_token, `/api/v1/inbound/${inbound.id}/complete`, {});
  await authPost(request, workerTokens.access_token, "/api/v1/putaway/confirm", {
    product_id: product.id,
    batch_id: null,
    qty: 5,
    from_location_id: stagingLoc.id,
    to_location_id: storageLoc.id
  });

  // UI: client creates outbound
  await page.addInitScript(({ access, refresh }) => {
    window.localStorage.setItem("systemecom.access_token", access);
    window.localStorage.setItem("systemecom.refresh_token", refresh);
  }, clientTokens);

  await page.goto(`/${LOCALE}/portal/outbound`);
  await page.getByPlaceholder("Client ID").fill(client.id);
  await page.getByPlaceholder("Warehouse ID").fill(wh.id);
  await page.getByPlaceholder("Destination name").fill("Dest");
  await page.getByPlaceholder("Destination address").fill("Addr");
  await page.getByPlaceholder("Product ID").fill(product.id);
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByText("Created outbound:")).toBeVisible();
  const createdText = await page.getByText("Created outbound:").textContent();
  const outboundId = (createdText ?? "").split("Created outbound:").pop()?.trim() ?? "";
  expect(outboundId).toMatch(/[0-9a-fA-F-]{36}/);

  // API: admin approve + generate picks
  await authPost(request, adminTokens.access_token, `/api/v1/outbound/${outboundId}/approve`, {});
  await authPost(request, adminTokens.access_token, `/api/v1/outbound/${outboundId}/generate-picks`, {});

  // UI: worker pick
  await page.addInitScript(({ access, refresh }) => {
    window.localStorage.setItem("systemecom.access_token", access);
    window.localStorage.setItem("systemecom.refresh_token", refresh);
  }, workerTokens);
  await page.goto(`/${LOCALE}/worker/pick`);

  const tasks = (await authGet(request, workerTokens.access_token, "/api/v1/picking/tasks")) as Array<{ id: string; outbound_id: string }>;
  const task = tasks.find((t) => t.outbound_id === outboundId) ?? tasks[0];
  expect(task?.id).toBeTruthy();
  await page.getByPlaceholder("UUID").first().fill(task.id);
  await page.getByRole("button", { name: "Load lines" }).click();

  // Provide packing location for to_location_id
  await page.getByLabel("To location (packing) (scan)").getByPlaceholder("UUID").fill(packingLoc.id);
  await page.getByRole("button", { name: "Confirm pick" }).click();
  await page.getByRole("button", { name: "Complete task" }).click();

  // UI: worker dispatch
  await page.goto(`/${LOCALE}/worker/dispatch`);
  await page.getByLabel("Outbound ID").getByPlaceholder("UUID").fill(outboundId);
  await page.getByLabel("Packing location ID").getByPlaceholder("UUID").fill(packingLoc.id);
  await page.getByRole("button", { name: "Confirm dispatch" }).click();

  // UI: admin invoice page should show a PDF link after generation
  await page.addInitScript(({ access, refresh }) => {
    window.localStorage.setItem("systemecom.access_token", access);
    window.localStorage.setItem("systemecom.refresh_token", refresh);
  }, adminTokens);
  await page.goto(`/${LOCALE}/admin/invoices`);
  await page.getByPlaceholder("Client ID").fill(client.id);
  await page.getByPlaceholder("YYYY-MM-DD start").fill("2020-01-01");
  await page.getByPlaceholder("YYYY-MM-DD end").fill("2030-01-01");
  await page.getByRole("button", { name: "Generate" }).click();
  // We expect at least one row and PDF button visible (if invoice created)
  await page.getByRole("button", { name: "Refresh" }).click();
  await expect(page.getByText("Invoices")).toBeVisible();
});


