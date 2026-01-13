"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

type Outbound = {
  id: string;
  client_id: string;
  warehouse_id: string;
  order_number: string;
  status: string;
};

export default function AdminOutboundPage() {
  useRequireAuth();
  const t = useTranslations("pages.adminOutbound");
  const c = useTranslations("common");
  const [items, setItems] = useState<Outbound[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [outboundId, setOutboundId] = useState("");
  const [selectedId, setSelectedId] = useState("");

  async function load() {
    const data = await api<Outbound[]>("/api/v1/outbound");
    setItems(data);
    if (!selectedId && data[0]?.id) {
      setSelectedId(data[0].id);
      setOutboundId(data[0].id);
    }
  }

  useEffect(() => {
    void load().catch(() => setError(t("loadFailed")));
  }, []);

  return (
    <AppShell nav="admin" title={t("title")}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("approveGenerate")}
          </div>
          <form
            className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                await api(`/api/v1/outbound/${outboundId}/approve`, { method: "POST" });
                await api(`/api/v1/outbound/${outboundId}/generate-picks`, { method: "POST" });
                await load();
              } catch {
                setError(t("approveFailed"));
              }
            }}
          >
            <select
              className="input"
              value={selectedId}
              onChange={(e) => {
                setSelectedId(e.target.value);
                setOutboundId(e.target.value);
              }}
            >
              <option value="">{t("outbound")}</option>
              {items.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.order_number} ({o.status})
                </option>
              ))}
            </select>
            <input className="input" placeholder={t("outboundIdManual")} value={outboundId} onChange={(e) => setOutboundId(e.target.value)} />
            <button className="btn btn-primary" type="submit">{t("approveGenerateBtn")}</button>
            <button className="btn btn-ghost" type="button" onClick={() => void load().catch(() => setError(t("reloadFailed")))}>
              {c("refresh")}
            </button>
          </form>
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("orders")}</div>
          <div className="mt-3 overflow-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2 text-left">{t("orderNo")}</th>
                  <th className="py-2 text-left">{t("status")}</th>
                  <th className="py-2 text-left">{t("client")}</th>
                  <th className="py-2 text-left">{t("warehouse")}</th>
                  <th className="py-2 text-left">{t("id")}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((o) => (
                  <tr key={o.id} className="border-b border-border">
                    <td className="py-2">{o.order_number}</td>
                    <td className="py-2">{o.status}</td>
                    <td className="py-2 font-mono text-xs">{o.client_id}</td>
                    <td className="py-2 font-mono text-xs">{o.warehouse_id}</td>
                    <td className="py-2 font-mono text-xs">{o.id}</td>
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



