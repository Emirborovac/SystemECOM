"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

type ReturnItem = { id: string; client_id: string; warehouse_id: string; status: string };

export default function AdminReturnsPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.adminReturns");
  const [items, setItems] = useState<ReturnItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [returnId, setReturnId] = useState("");
  const [productId, setProductId] = useState("");
  const [qty, setQty] = useState(1);
  const [disposition, setDisposition] = useState("RESTOCK");
  const [toLocationId, setToLocationId] = useState("");

  async function load() {
    const data = await api<ReturnItem[]>("/api/v1/returns");
    setItems(data);
  }

  useEffect(() => {
    void load().catch(() => setError(t("reloadFailed")));
  }, []);

  return (
    <AppShell nav="admin" title={`${nav("admin")} / ${nav("returns")}`}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("scanReturnLine")}</div>
          <form
            className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-5"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                await api(`/api/v1/returns/${returnId}/scan-line`, {
                  method: "POST",
                  body: {
                    product_id: productId,
                    qty,
                    disposition,
                    to_location_id: toLocationId || null
                  }
                });
                await load();
              } catch {
                setError(t("scanFailed"));
              }
            }}
          >
            <input className="input" placeholder={t("returnId")} value={returnId} onChange={(e) => setReturnId(e.target.value)} />
            <input className="input" placeholder={t("productId")} value={productId} onChange={(e) => setProductId(e.target.value)} />
            <input className="input" type="number" min={1} value={qty} onChange={(e) => setQty(Number(e.target.value))} />
            <select className="input" value={disposition} onChange={(e) => setDisposition(e.target.value)}>
              <option value="RESTOCK">{t("restock")}</option>
              <option value="QUARANTINE">{t("quarantine")}</option>
              <option value="SCRAP">{t("scrap")}</option>
            </select>
            <input className="input" placeholder={t("toLocationIdRequired")} value={toLocationId} onChange={(e) => setToLocationId(e.target.value)} />
            <button className="btn btn-primary md:col-span-5" type="submit">{t("addLine")}</button>
          </form>
          <div className="mt-3 flex gap-3">
            <button className="btn btn-ghost" type="button" onClick={() => void api(`/api/v1/returns/${returnId}/complete`, { method: "POST" }).then(load).catch(() => setError(t("completeFailed")))}>
              {t("completeReturn")}
            </button>
            <button className="btn btn-ghost" type="button" onClick={() => void load().catch(() => setError(t("reloadFailed")))}>
              Refresh
            </button>
          </div>
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("listTitle")}</div>
          <div className="mt-3 overflow-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2 text-left">{t("status")}</th>
                  <th className="py-2 text-left">{t("client")}</th>
                  <th className="py-2 text-left">{t("warehouse")}</th>
                  <th className="py-2 text-left">{t("id")}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.id} className="border-b border-border">
                    <td className="py-2">{r.status}</td>
                    <td className="py-2 font-mono text-xs">{r.client_id}</td>
                    <td className="py-2 font-mono text-xs">{r.warehouse_id}</td>
                    <td className="py-2 font-mono text-xs">{r.id}</td>
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



