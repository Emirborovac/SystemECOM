"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

type Product = {
  id: string;
  tenant_id: number;
  client_id: string;
  sku: string;
  name: string;
  category: string | null;
  barcode: string | null;
  uom: string;
};

export default function AdminProductsPage() {
  useRequireAuth();
  const t = useTranslations("pages.adminProducts");
  const tt = useTranslations("pages.adminProductsPage");
  const [items, setItems] = useState<Product[]>([]);
  const [clientId, setClientId] = useState("");
  const [sku, setSku] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [barcode, setBarcode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<{ created: number; errors: Array<{ row: number; field: string; message: string }> } | null>(null);

  async function load() {
    setError(null);
    const query = clientId ? `?client_id=${encodeURIComponent(clientId)}` : "";
    const data = await api<Product[]>(`/api/v1/products${query}`);
    setItems(data);
  }

  useEffect(() => {
    void load().catch(() => setError(tt("loadFailed")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AppShell nav="admin" title={t("title")}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("create")}
          </div>
          <form
            className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-5"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                await api<Product>("/api/v1/products", {
                  method: "POST",
                  body: {
                    client_id: clientId,
                    sku,
                    name,
                    category: category || null,
                    barcode: barcode || null,
                    uom: "piece"
                  }
                });
                setSku("");
                setName("");
                setCategory("");
                setBarcode("");
                await load();
              } catch {
                setError(tt("createFailed"));
              }
            }}
          >
            <input className="input" placeholder={tt("clientId")} value={clientId} onChange={(e) => setClientId(e.target.value)} />
            <input className="input" placeholder={tt("sku")} value={sku} onChange={(e) => setSku(e.target.value)} />
            <input className="input" placeholder={tt("name")} value={name} onChange={(e) => setName(e.target.value)} />
            <input className="input" placeholder={tt("categoryOptional")} value={category} onChange={(e) => setCategory(e.target.value)} />
            <input className="input" placeholder={tt("barcodeOptional")} value={barcode} onChange={(e) => setBarcode(e.target.value)} />
            <button className="btn btn-primary" type="submit">{tt("create")}</button>
          </form>
          <div className="mt-3 flex gap-3">
            <button className="btn btn-ghost" type="button" onClick={() => void load().catch(() => setError(tt("loadFailedShort")))}>
              {tt("refreshList")}
            </button>
          </div>
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{tt("bulkImportProducts")}</div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
            <input className="input" placeholder={tt("clientId")} value={clientId} onChange={(e) => setClientId(e.target.value)} />
            <input className="input" type="file" accept=".csv,text/csv" onChange={(e) => setImportFile(e.target.files?.[0] ?? null)} />
            <button
              className="btn btn-primary"
              type="button"
              onClick={async () => {
                setError(null);
                setImportResult(null);
                if (!clientId) {
                  setError(tt("clientIdRequired"));
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
                    `/api/v1/products/import-csv?client_id=${encodeURIComponent(clientId)}`,
                    { method: "POST", body: fd },
                  );
                  setImportResult(res);
                  await load();
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
          <div className="text-xs uppercase tracking-widest text-muted">
            {tt("products")}
          </div>
          <div className="mt-3 overflow-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2 text-left">{tt("sku")}</th>
                  <th className="py-2 text-left">{tt("name")}</th>
                  <th className="py-2 text-left">{tt("category")}</th>
                  <th className="py-2 text-left">{tt("barcode")}</th>
                  <th className="py-2 text-left">{tt("client")}</th>
                  <th className="py-2 text-left">{tt("id")}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((p) => (
                  <tr key={p.id} className="border-b border-border">
                    <td className="py-2">{p.sku}</td>
                    <td className="py-2">{p.name}</td>
                    <td className="py-2">{p.category ?? "—"}</td>
                    <td className="py-2 font-mono text-xs">{p.barcode ?? "—"}</td>
                    <td className="py-2 font-mono text-xs">{p.client_id}</td>
                    <td className="py-2 font-mono text-xs">{p.id}</td>
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


