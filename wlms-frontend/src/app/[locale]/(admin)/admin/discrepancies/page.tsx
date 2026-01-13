"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

type Discrepancy = { id: string; status: string; delta_qty: number; product_id: string; location_id: string };

export default function AdminDiscrepanciesPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.adminDiscrepancies");
  const [items, setItems] = useState<Discrepancy[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const data = await api<Discrepancy[]>("/api/v1/discrepancies");
    setItems(data);
  }

  useEffect(() => {
    void load().catch(() => setError(t("loadFailed")));
  }, []);

  return (
    <AppShell nav="admin" title={`${nav("admin")} / ${nav("discrepancies")}`}>
      <div className="card p-5">
        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-widest text-muted">{t("title")}</div>
          <button className="btn btn-ghost" type="button" onClick={() => void load().catch(() => setError(t("loadFailed")))}>
            Refresh
          </button>
        </div>
        {error ? <div className="mt-3 text-sm">{error}</div> : null}
        <div className="mt-3 overflow-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="py-2 text-left">{t("status")}</th>
                <th className="py-2 text-left">{t("delta")}</th>
                <th className="py-2 text-left">{t("product")}</th>
                <th className="py-2 text-left">{t("location")}</th>
                <th className="py-2 text-left"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((d) => (
                <tr key={d.id} className="border-b border-border">
                  <td className="py-2">{d.status}</td>
                  <td className="py-2">{d.delta_qty}</td>
                  <td className="py-2 font-mono text-xs">{d.product_id}</td>
                  <td className="py-2 font-mono text-xs">{d.location_id}</td>
                  <td className="py-2 flex gap-2">
                    <button
                      className="btn btn-primary"
                      type="button"
                      onClick={() => void api(`/api/v1/discrepancies/${d.id}/approve`, { method: "POST" }).then(load).catch(() => setError(t("approveFailed")))}
                      disabled={d.status !== "PENDING"}
                    >
                      {t("approve")}
                    </button>
                    <button
                      className="btn btn-ghost"
                      type="button"
                      onClick={() => void api(`/api/v1/discrepancies/${d.id}/reject`, { method: "POST" }).then(load).catch(() => setError(t("rejectFailed")))}
                      disabled={d.status !== "PENDING"}
                    >
                      {t("reject")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}



