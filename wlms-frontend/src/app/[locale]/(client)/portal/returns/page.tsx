"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

type ReturnItem = { id: string; status: string; warehouse_id: string };

export default function ClientReturnsPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.clientReturns");
  const [items, setItems] = useState<ReturnItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setError(null);
      try {
        const data = await api<ReturnItem[]>("/api/v1/returns");
        setItems(data);
      } catch {
        setError(t("loadFailed"));
      }
    })();
  }, []);

  return (
    <AppShell nav="client" title={`${nav("client")} / ${nav("returns")}`}>
      <div className="card p-5">
        <div className="text-xs uppercase tracking-widest text-muted">{t("title")}</div>
        {error ? <div className="mt-3 text-sm">{error}</div> : null}
        <div className="mt-3 overflow-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="py-2 text-left">{t("status")}</th>
                <th className="py-2 text-left">{t("warehouse")}</th>
                <th className="py-2 text-left">{t("id")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id} className="border-b border-border">
                  <td className="py-2">{r.status}</td>
                  <td className="py-2 font-mono text-xs">{r.warehouse_id}</td>
                  <td className="py-2 font-mono text-xs">{r.id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}


