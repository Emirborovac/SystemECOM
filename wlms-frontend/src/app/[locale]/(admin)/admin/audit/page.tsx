"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

type AuditRow = { id: string; created_at: string; action: string; entity_type: string; entity_id: string; actor_user_id: string | null };

export default function AdminAuditPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.adminAudit");
  const [items, setItems] = useState<AuditRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const data = await api<AuditRow[]>("/api/v1/audit/logs");
    setItems(data);
  }

  useEffect(() => {
    void load().catch(() => setError(t("loadFailed")));
  }, []);

  return (
    <AppShell nav="admin" title={`${nav("admin")} / ${nav("audit")}`}>
      <div className="card p-5">
        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-widest text-muted">{t("title")}</div>
          <button className="btn btn-ghost" type="button" onClick={() => void load().catch(() => setError(t("reloadFailed")))}>
            Refresh
          </button>
        </div>
        {error ? <div className="mt-3 text-sm">{error}</div> : null}
        <div className="mt-3 overflow-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="py-2 text-left">{t("time")}</th>
                <th className="py-2 text-left">{t("action")}</th>
                <th className="py-2 text-left">{t("entity")}</th>
                <th className="py-2 text-left">{t("actor")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((l) => (
                <tr key={l.id} className="border-b border-border">
                  <td className="py-2">{l.created_at}</td>
                  <td className="py-2">{l.action}</td>
                  <td className="py-2 font-mono text-xs">{l.entity_type}:{l.entity_id}</td>
                  <td className="py-2 font-mono text-xs">{l.actor_user_id ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}



