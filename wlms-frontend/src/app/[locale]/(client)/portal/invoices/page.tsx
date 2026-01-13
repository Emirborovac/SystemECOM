"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api, apiBaseUrl } from "@/lib/api/http";

type Invoice = { id: string; period_start: string; period_end: string; status: string; currency: string; total: number; pdf_file_id: string | null };

export default function ClientInvoicesPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.clientInvoices");
  const c = useTranslations("common");
  const [items, setItems] = useState<Invoice[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setError(null);
      try {
        const data = await api<Invoice[]>("/api/v1/invoices");
        setItems(data);
      } catch {
        setError(t("loadFailed"));
      }
    })();
  }, []);

  return (
    <AppShell nav="client" title={`${nav("client")} / ${nav("invoices")}`}>
      <div className="card p-5">
        <div className="text-xs uppercase tracking-widest text-muted">{t("title")}</div>
        {error ? <div className="mt-3 text-sm">{error}</div> : null}
        <div className="mt-3 overflow-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="py-2 text-left">{t("status")}</th>
                <th className="py-2 text-left">{t("period")}</th>
                <th className="py-2 text-right">{t("total")}</th>
                <th className="py-2 text-left"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((i) => (
                <tr key={i.id} className="border-b border-border">
                  <td className="py-2">{i.status}</td>
                  <td className="py-2">{i.period_start} → {i.period_end}</td>
                  <td className="py-2 text-right">{i.total.toFixed(2)} {i.currency}</td>
                  <td className="py-2">
                    {i.pdf_file_id ? (
                      <a className="btn btn-primary" href={`${apiBaseUrl()}/api/v1/files/${i.pdf_file_id}/download`}>
                        {t("pdf")}
                      </a>
                    ) : null}
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



