 "use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

type Summary = { date: string; inbound_today: number; outbound_today: number; discrepancies_pending: number };
type SummaryV2 = Summary & {
  occupied_positions: number;
  expiring_30: number;
  expiring_60: number;
  expiring_90: number;
  trend_14d: Array<{ date: string; inbound: number; outbound: number }>;
  top_clients: Array<{ client_id: string; name: string; outbound_count: number }>;
};

export default function AdminDashboardPage() {
  const nav = useTranslations("nav");
  const t = useTranslations("pages.adminDashboard");
  useRequireAuth();
  const [data, setData] = useState<SummaryV2 | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setError(null);
      try {
        const s = await api<SummaryV2>("/api/v1/dashboard/summary");
        setData(s);
      } catch {
        setError(t("loadFailed"));
      }
    })();
  }, []);

  return (
    <AppShell nav="admin" title={`${nav("admin")} / ${nav("dashboard")}`}>
      {error ? <div className="card p-5 text-sm">{error}</div> : null}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("todayInbound")}
          </div>
          <div className="mt-2 text-2xl font-semibold">{data ? data.inbound_today : "—"}</div>
        </div>
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("todayOutbound")}
          </div>
          <div className="mt-2 text-2xl font-semibold">{data ? data.outbound_today : "—"}</div>
        </div>
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("discrepanciesPending")}
          </div>
          <div className="mt-2 text-2xl font-semibold">{data ? data.discrepancies_pending : "—"}</div>
        </div>
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("occupiedPositions")}
          </div>
          <div className="mt-2 text-2xl font-semibold">{data ? data.occupied_positions : "—"}</div>
        </div>
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("expiring")}
          </div>
          <div className="mt-2 text-2xl font-semibold">
            {data ? `${data.expiring_30} / ${data.expiring_60} / ${data.expiring_90}` : "—"}
          </div>
        </div>
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("topClients")}</div>
          <div className="mt-3 grid gap-2 text-sm">
            {data
              ? data.top_clients.map((c) => (
                  <div key={c.client_id} className="flex items-center justify-between border-b border-border pb-1">
                    <div className="truncate">{c.name || c.client_id}</div>
                    <div className="font-mono text-xs">{c.outbound_count}</div>
                  </div>
                ))
              : "—"}
          </div>
        </div>
      </div>

      <div className="card mt-4 p-5">
        <div className="text-xs uppercase tracking-widest text-muted">{t("trendTitle")}</div>
        <div className="mt-3 overflow-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="py-2 text-left">{t("date")}</th>
                <th className="py-2 text-right">{t("inbound")}</th>
                <th className="py-2 text-right">{t("outbound")}</th>
              </tr>
            </thead>
            <tbody>
              {data
                ? data.trend_14d.map((r) => (
                    <tr key={r.date} className="border-b border-border">
                      <td className="py-2">{r.date}</td>
                      <td className="py-2 text-right">{r.inbound}</td>
                      <td className="py-2 text-right">{r.outbound}</td>
                    </tr>
                  ))
                : null}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}




