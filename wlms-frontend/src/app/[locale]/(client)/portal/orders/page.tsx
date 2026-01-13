"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

type Outbound = { id: string; order_number: string; status: string; warehouse_id: string };

export default function ClientOrdersPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.clientOrders");
  const [items, setItems] = useState<Outbound[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setError(null);
      try {
        const data = await api<Outbound[]>("/api/v1/outbound");
        setItems(data);
      } catch {
        setError(t("loadFailed"));
      }
    })();
  }, []);

  return (
    <AppShell nav="client" title={`${nav("client")} / ${nav("orders")}`}>
      <div className="card p-5">
        <div className="text-xs uppercase tracking-widest text-muted">{t("title")}</div>
        {error ? <div className="mt-3 text-sm">{error}</div> : null}
        <div className="mt-3 overflow-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="py-2 text-left">{t("orderNo")}</th>
                <th className="py-2 text-left">{t("status")}</th>
                <th className="py-2 text-left">{t("warehouse")}</th>
                <th className="py-2 text-left">{t("id")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((o) => (
                <tr key={o.id} className="border-b border-border">
                  <td className="py-2">{o.order_number}</td>
                  <td className="py-2">{o.status}</td>
                  <td className="py-2 font-mono text-xs">{o.warehouse_id}</td>
                  <td className="py-2 font-mono text-xs">{o.id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}



