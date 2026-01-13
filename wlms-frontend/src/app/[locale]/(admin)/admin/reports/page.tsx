"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { apiBaseUrl } from "@/lib/api/http";

export default function AdminReportsPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.adminReports");
  const [format, setFormat] = useState("csv");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  const base = `${apiBaseUrl()}/api/v1/reports`;

  return (
    <AppShell nav="admin" title={`${nav("admin")} / ${nav("reports")}`}>
      <div className="card p-5">
        <div className="text-xs uppercase tracking-widest text-muted">{t("downloadReports")}</div>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-4">
          <select className="input" value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="csv">{t("csv")}</option>
            <option value="json">{t("json")}</option>
          </select>
          <input className="input" placeholder={t("start")} value={start} onChange={(e) => setStart(e.target.value)} />
          <input className="input" placeholder={t("end")} value={end} onChange={(e) => setEnd(e.target.value)} />
          <div className="text-sm text-muted">{t("rangeHint")}</div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          <a className="btn btn-primary" href={`${base}/inventory-snapshot?format=${format}`}>
            {t("inventorySnapshot")}
          </a>
          <a className="btn btn-primary" href={`${base}/expiry?format=${format}`}>
            {t("expiry")}
          </a>
          <a className="btn btn-primary" href={`${base}/movements?format=${format}`}>
            {t("movements")}
          </a>
          <a className="btn btn-primary" href={`${base}/discrepancies?format=${format}`}>
            {t("discrepancies")}
          </a>
          <a className="btn btn-primary" href={`${base}/inventory-reconcile?format=${format}`}>
            {t("inventoryReconcile")}
          </a>
          <a className="btn btn-primary" href={`${base}/volumes?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}&format=${format}`}>
            {t("volumes")}
          </a>
          <a className="btn btn-primary" href={`${base}/billing-events?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}&format=${format}`}>
            {t("billingEvents")}
          </a>
        </div>
      </div>
    </AppShell>
  );
}



