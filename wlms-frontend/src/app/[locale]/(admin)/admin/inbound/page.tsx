"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

type Client = { id: string; name: string };
type Warehouse = { id: string; name: string };
type Zone = { id: number; warehouse_id: string; zone_type: string };
type Location = { id: string; warehouse_id: string; zone_id: number; code: string; barcode_value: string };

type Inbound = {
  id: string;
  tenant_id: number;
  client_id: string;
  warehouse_id: string;
  reference_number: string;
  status: string;
};

export default function AdminInboundPage() {
  useRequireAuth();
  const t = useTranslations("pages.adminInbound");
  const [items, setItems] = useState<Inbound[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [clients, setClients] = useState<Client[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [stagingLocations, setStagingLocations] = useState<Location[]>([]);

  const [clientId, setClientId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [createdInboundId, setCreatedInboundId] = useState<string>("");

  const [scanInboundId, setScanInboundId] = useState("");
  const [barcode, setBarcode] = useState("");
  const [qty, setQty] = useState(1);
  const [stagingLocationId, setStagingLocationId] = useState("");

  async function loadRefs() {
    const [c, w] = await Promise.all([api<Client[]>("/api/v1/clients"), api<Warehouse[]>("/api/v1/warehouses")]);
    setClients(c);
    setWarehouses(w);
    if (!clientId && c[0]?.id) setClientId(c[0].id);
    if (!warehouseId && w[0]?.id) setWarehouseId(w[0].id);
  }

  async function loadStagingLocations(wid: string) {
    if (!wid) return;
    const [zones, locs] = await Promise.all([
      api<Zone[]>(`/api/v1/warehouses/${wid}/zones`),
      api<Location[]>(`/api/v1/warehouses/${wid}/locations`)
    ]);
    const zoneTypeById = new Map<number, string>(zones.map((z) => [z.id, z.zone_type]));
    const staging = locs.filter((l) => zoneTypeById.get(l.zone_id) === "STAGING");
    setStagingLocations(staging);
    if (!stagingLocationId && staging[0]?.id) setStagingLocationId(staging[0].id);
  }

  async function load() {
    setError(null);
    const data = await api<Inbound[]>("/api/v1/inbound");
    setItems(data);
  }

  useEffect(() => {
    void load().catch(() => setError(t("loadFailed")));
    void loadRefs().catch(() => setError(t("loadRefsFailed")));
  }, []);

  useEffect(() => {
    void loadStagingLocations(warehouseId).catch(() => {});
  }, [warehouseId]);

  return (
    <AppShell nav="admin" title={t("title")}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("create")}
          </div>
          <form
            className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-4"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                const inbound = await api<Inbound>("/api/v1/inbound", {
                  method: "POST",
                  body: { client_id: clientId, warehouse_id: warehouseId }
                });
                setCreatedInboundId(inbound.id);
                setScanInboundId(inbound.id);
                await api(`/api/v1/inbound/${inbound.id}/start-receiving`, { method: "POST" });
                await load();
              } catch {
                setError(t("createFailed"));
              }
            }}
          >
            <select className="input" value={clientId} onChange={(e) => setClientId(e.target.value)}>
              <option value="">{t("client")}</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.id})
                </option>
              ))}
            </select>
            <select className="input" value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)}>
              <option value="">{t("warehouse")}</option>
              {warehouses.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name} ({w.id})
                </option>
              ))}
            </select>
            <button className="btn btn-primary" type="submit">{t("createStart")}</button>
            <div className="text-sm text-muted md:col-span-1">
              {createdInboundId ? `${t("created")}: ${createdInboundId}` : ""}
            </div>
          </form>
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("scanLine")}
          </div>
          <form
            className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-5"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                await api(`/api/v1/inbound/${scanInboundId}/scan-line`, {
                  method: "POST",
                  body: {
                    barcode,
                    qty,
                    location_staging_id: stagingLocationId
                  }
                });
                setBarcode("");
                setQty(1);
                await load();
              } catch {
                setError(t("scanFailed"));
              }
            }}
          >
            <input className="input" placeholder={t("inboundId")} value={scanInboundId} onChange={(e) => setScanInboundId(e.target.value)} />
            <select className="input" value={stagingLocationId} onChange={(e) => setStagingLocationId(e.target.value)}>
              <option value="">{t("stagingLocation")}</option>
              {stagingLocations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.code} ({l.barcode_value})
                </option>
              ))}
            </select>
            <input className="input" placeholder={t("productBarcode")} value={barcode} onChange={(e) => setBarcode(e.target.value)} />
            <input className="input" type="number" min={1} value={qty} onChange={(e) => setQty(Number(e.target.value))} />
            <button className="btn btn-primary" type="submit">{t("receive")}</button>
          </form>
          <div className="mt-3 flex gap-3">
            <button className="btn btn-ghost" type="button" onClick={() => void load().catch(() => setError(t("reloadFailed")))}>
              {t("refreshList")}
            </button>
          </div>
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("list")}
          </div>
          <div className="mt-3 overflow-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2 text-left">{t("ref")}</th>
                  <th className="py-2 text-left">{t("status")}</th>
                  <th className="py-2 text-left">{t("client")}</th>
                  <th className="py-2 text-left">{t("warehouse")}</th>
                  <th className="py-2 text-left">{t("id")}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((i) => (
                  <tr key={i.id} className="border-b border-border">
                    <td className="py-2">{i.reference_number}</td>
                    <td className="py-2">{i.status}</td>
                    <td className="py-2 font-mono text-xs">{i.client_id}</td>
                    <td className="py-2 font-mono text-xs">{i.warehouse_id}</td>
                    <td className="py-2 font-mono text-xs">{i.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppShell>
  );
}


