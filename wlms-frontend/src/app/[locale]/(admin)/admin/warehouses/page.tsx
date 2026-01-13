"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api, apiBaseUrl } from "@/lib/api/http";
import { getAccessToken } from "@/lib/auth/tokens";

type Warehouse = { id: string; name: string; address: string | null; timezone: string | null };
type Zone = { id: number; warehouse_id: string; name: string; zone_type: string };
type Location = { id: string; warehouse_id: string; zone_id: number; code: string; barcode_value: string; is_active: boolean };

export default function AdminWarehousesPage() {
  useRequireAuth();
  const t = useTranslations("pages.adminWarehouses");
  const tt = useTranslations("pages.adminWarehousesPage");
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<string>("");

  const [warehouseName, setWarehouseName] = useState("");
  const [zoneName, setZoneName] = useState("");
  const [zoneType, setZoneType] = useState("STAGING");
  const [locCode, setLocCode] = useState("");
  const [locBarcode, setLocBarcode] = useState("");
  const [locZoneId, setLocZoneId] = useState<number | "">("");

  const [error, setError] = useState<string | null>(null);
  const [importZoneId, setImportZoneId] = useState<number | "">("");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<{ created: number; errors: Array<{ row: number; field: string; message: string }> } | null>(null);

  async function loadWarehouses() {
    const data = await api<Warehouse[]>("/api/v1/warehouses");
    setWarehouses(data);
  }

  async function loadDetails(warehouseId: string) {
    const [z, l] = await Promise.all([
      api<Zone[]>(`/api/v1/warehouses/${warehouseId}/zones`),
      api<Location[]>(`/api/v1/warehouses/${warehouseId}/locations`)
    ]);
    setZones(z);
    setLocations(l);
  }

  useEffect(() => {
    (async () => {
      setError(null);
      try {
        await loadWarehouses();
      } catch {
        setError(tt("loadFailed"));
      }
    })();
  }, []);

  useEffect(() => {
    if (!selectedWarehouseId) return;
    void loadDetails(selectedWarehouseId);
  }, [selectedWarehouseId]);

  return (
    <AppShell nav="admin" title={t("title")}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("create")}
          </div>
          <form
            className="mt-3 flex flex-col gap-3 sm:flex-row"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                await api("/api/v1/warehouses", { method: "POST", body: { name: warehouseName } });
                setWarehouseName("");
                await loadWarehouses();
              } catch {
                setError(tt("createWarehouseFailed"));
              }
            }}
          >
            <input className="input flex-1" placeholder={tt("warehouseName")} value={warehouseName} onChange={(e) => setWarehouseName(e.target.value)} />
            <button className="btn btn-primary" type="submit">{tt("create")}</button>
          </form>
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("select")}
          </div>
          <div className="mt-3 flex flex-col gap-3 sm:flex-row">
            <select
              className="input flex-1"
              value={selectedWarehouseId}
              onChange={(e) => setSelectedWarehouseId(e.target.value)}
            >
              <option value="">—</option>
              {warehouses.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name} ({w.id})
                </option>
              ))}
            </select>
          </div>
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>

        {selectedWarehouseId ? (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="card p-5">
                <div className="text-xs uppercase tracking-widest text-muted">
                  {tt("zones")}
                </div>
                <form
                  className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    setError(null);
                    try {
                      await api(`/api/v1/warehouses/${selectedWarehouseId}/zones`, {
                        method: "POST",
                        body: { name: zoneName, zone_type: zoneType }
                      });
                      setZoneName("");
                      await loadDetails(selectedWarehouseId);
                    } catch {
                      setError(tt("createZoneFailed"));
                    }
                  }}
                >
                  <input className="input" placeholder={tt("zoneName")} value={zoneName} onChange={(e) => setZoneName(e.target.value)} />
                  <select className="input" value={zoneType} onChange={(e) => setZoneType(e.target.value)}>
                    <option value="STAGING">{tt("zoneTypeStaging")}</option>
                    <option value="STORAGE">{tt("zoneTypeStorage")}</option>
                    <option value="PACKING">{tt("zoneTypePacking")}</option>
                    <option value="RETURNS">{tt("zoneTypeReturns")}</option>
                    <option value="QUARANTINE">{tt("zoneTypeQuarantine")}</option>
                  </select>
                  <button className="btn btn-primary" type="submit">{tt("add")}</button>
                </form>
                <div className="mt-3 overflow-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="py-2 text-left">{tt("id")}</th>
                        <th className="py-2 text-left">{tt("name")}</th>
                        <th className="py-2 text-left">{tt("type")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {zones.map((z) => (
                        <tr key={z.id} className="border-b border-border">
                          <td className="py-2 font-mono text-xs">{z.id}</td>
                          <td className="py-2">{z.name}</td>
                          <td className="py-2">{z.zone_type}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="card p-5">
                <div className="text-xs uppercase tracking-widest text-muted">
                  {tt("locations")}
                </div>
                <form
                  className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-4"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    setError(null);
                    if (!locZoneId) {
                      setError(tt("pickZone"));
                      return;
                    }
                    try {
                      await api(`/api/v1/warehouses/${selectedWarehouseId}/locations`, {
                        method: "POST",
                        body: { zone_id: locZoneId, code: locCode, barcode_value: locBarcode }
                      });
                      setLocCode("");
                      setLocBarcode("");
                      await loadDetails(selectedWarehouseId);
                    } catch {
                      setError(tt("createLocationFailed"));
                    }
                  }}
                >
                  <select className="input" value={locZoneId} onChange={(e) => setLocZoneId(e.target.value ? Number(e.target.value) : "")}>
                    <option value="">{tt("zone")}</option>
                    {zones.map((z) => (
                      <option key={z.id} value={z.id}>
                        {z.name} ({z.zone_type})
                      </option>
                    ))}
                  </select>
                  <input className="input" placeholder={tt("code")} value={locCode} onChange={(e) => setLocCode(e.target.value)} />
                  <input className="input" placeholder={tt("barcode")} value={locBarcode} onChange={(e) => setLocBarcode(e.target.value)} />
                  <button className="btn btn-primary" type="submit">{tt("add")}</button>
                </form>
                <div className="mt-3 overflow-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="py-2 text-left">{tt("code")}</th>
                        <th className="py-2 text-left">{tt("barcode")}</th>
                        <th className="py-2 text-left">{tt("zone")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {locations.map((l) => (
                        <tr key={l.id} className="border-b border-border">
                          <td className="py-2">{l.code}</td>
                          <td className="py-2 font-mono text-xs">{l.barcode_value}</td>
                          <td className="py-2 font-mono text-xs">{l.zone_id}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="card p-5">
                <div className="text-xs uppercase tracking-widest text-muted">{tt("bulkImportLocations")}</div>
                <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
                  <select
                    className="input"
                    value={importZoneId}
                    onChange={(e) => setImportZoneId(e.target.value ? Number(e.target.value) : "")}
                  >
                    <option value="">{tt("zone")}</option>
                    {zones.map((z) => (
                      <option key={z.id} value={z.id}>
                        {z.name} ({z.zone_type})
                      </option>
                    ))}
                  </select>
                  <input
                    className="input"
                    type="file"
                    accept=".csv,text/csv"
                    onChange={(e) => setImportFile(e.target.files?.[0] ?? null)}
                  />
                  <button
                    className="btn btn-primary"
                    type="button"
                    onClick={async () => {
                      setError(null);
                      setImportResult(null);
                      if (!importZoneId) {
                        setError(tt("pickZone"));
                        return;
                      }
                      if (!importFile) {
                        setError(tt("pickCsvFile"));
                        return;
                      }
                      try {
                        const fd = new FormData();
                        fd.append("file", importFile);
                        const res = await api<{ created: number; errors: Array<{ row: number; field: string; message: string }> }>(
                          `/api/v1/warehouses/${selectedWarehouseId}/locations/import-csv?zone_id=${encodeURIComponent(String(importZoneId))}`,
                          { method: "POST", body: fd },
                        );
                        setImportResult(res);
                        await loadDetails(selectedWarehouseId);
                      } catch {
                        setError(tt("importFailed"));
                      }
                    }}
                  >
                    {tt("upload")}
                  </button>
                </div>
                <div className="mt-3 text-sm text-muted">{tt("csvColumnsHint")}</div>
                {importResult ? (
                  <div className="mt-3 text-sm">
                    {tt("importCreated")}: {importResult.created}{" "}
                    {importResult.errors.length ? `(${tt("importErrors")}: ${importResult.errors.length})` : ""}
                  </div>
                ) : null}
                {importResult?.errors?.length ? (
                  <div className="mt-3 overflow-auto">
                    <table className="w-full border-collapse text-sm">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="py-2 text-left">{tt("row")}</th>
                          <th className="py-2 text-left">{tt("field")}</th>
                          <th className="py-2 text-left">{tt("message")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {importResult.errors.slice(0, 50).map((er, i) => (
                          <tr key={i} className="border-b border-border">
                            <td className="py-2">{er.row}</td>
                            <td className="py-2">{er.field}</td>
                            <td className="py-2">{er.message}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </div>

              <div className="card p-5">
                <div className="text-xs uppercase tracking-widest text-muted">{tt("printLocationLabels")}</div>
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <button
                    className="btn btn-primary"
                    type="button"
                    onClick={async () => {
                      setError(null);
                      try {
                        const token = getAccessToken();
                        const res = await fetch(`${apiBaseUrl()}/api/v1/warehouses/${selectedWarehouseId}/locations/labels.pdf`, {
                          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
                        });
                        if (!res.ok) throw new Error(await res.text());
                        const blob = await res.blob();
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = `location_labels_${selectedWarehouseId}.pdf`;
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                        URL.revokeObjectURL(url);
                      } catch {
                        setError(tt("downloadFailed"));
                      }
                    }}
                  >
                    {tt("downloadPdf")}
                  </button>
                </div>
                <div className="mt-3 text-sm text-muted">{tt("labelsHint")}</div>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}


