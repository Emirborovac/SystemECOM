"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api, apiBaseUrl } from "@/lib/api/http";

type Invoice = {
  id: string;
  client_id: string;
  period_start: string;
  period_end: string;
  status: string;
  currency: string;
  total: number;
  pdf_file_id: string | null;
};

type InvoiceLine = {
  id: string;
  invoice_id: string;
  description_key: string;
  quantity: number;
  unit_price: number;
  total_price: number;
};

export default function AdminInvoicesPage() {
  useRequireAuth();
  const locale = useLocale();
  const t = useTranslations("pages.adminInvoices");
  const c = useTranslations("common");
  const [items, setItems] = useState<Invoice[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lines, setLines] = useState<InvoiceLine[] | null>(null);
  const [linesForId, setLinesForId] = useState<string | null>(null);

  const [clientId, setClientId] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  async function load() {
    const data = await api<Invoice[]>("/api/v1/invoices");
    setItems(data);
  }

  useEffect(() => {
    void load().catch(() => setError(t("loadFailed")));
  }, []);

  return (
    <AppShell nav="admin" title={t("title")}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("generateInvoice")}</div>
          <form
            className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-4"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                await api<Invoice>("/api/v1/invoices/generate", {
                  method: "POST",
                  body: { client_id: clientId, period_start: start, period_end: end, language: locale }
                });
                await load();
              } catch {
                setError(t("generateFailed"));
              }
            }}
          >
            <input className="input" placeholder={t("clientId")} value={clientId} onChange={(e) => setClientId(e.target.value)} />
            <input className="input" placeholder={t("startDate")} value={start} onChange={(e) => setStart(e.target.value)} />
            <input className="input" placeholder={t("endDate")} value={end} onChange={(e) => setEnd(e.target.value)} />
            <button className="btn btn-primary" type="submit">{t("generate")}</button>
          </form>
          <div className="mt-3">
            <button className="btn btn-ghost" type="button" onClick={() => void load().catch(() => setError(c("refresh")))}>
              {c("refresh")}
            </button>
          </div>
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("invoices")}</div>
          {lines ? (
            <div className="mt-3 border border-border bg-surface p-3 text-sm shadow-brutal">
              <div className="text-xs uppercase tracking-widest text-muted">{t("linesFor")} {linesForId}</div>
              <div className="mt-2 overflow-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="py-2 text-left">{t("key")}</th>
                      <th className="py-2 text-right">{t("qty")}</th>
                      <th className="py-2 text-right">{t("unit")}</th>
                      <th className="py-2 text-right">{t("total")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lines.map((l) => (
                      <tr key={l.id} className="border-b border-border">
                        <td className="py-2 font-mono text-xs">{l.description_key}</td>
                        <td className="py-2 text-right">{l.quantity}</td>
                        <td className="py-2 text-right">{l.unit_price.toFixed(2)}</td>
                        <td className="py-2 text-right">{l.total_price.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-2 flex gap-2">
                <button className="btn btn-ghost" type="button" onClick={() => { setLines(null); setLinesForId(null); }}>
                  {t("close")}
                </button>
              </div>
            </div>
          ) : null}
          <div className="mt-3 overflow-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2 text-left">{t("status")}</th>
                  <th className="py-2 text-left">{t("client")}</th>
                  <th className="py-2 text-left">{t("period")}</th>
                  <th className="py-2 text-right">{t("total")}</th>
                  <th className="py-2 text-left"></th>
                </tr>
              </thead>
              <tbody>
                {items.map((i) => (
                  <tr key={i.id} className="border-b border-border">
                    <td className="py-2">{i.status}</td>
                    <td className="py-2 font-mono text-xs">{i.client_id}</td>
                    <td className="py-2">{i.period_start} → {i.period_end}</td>
                    <td className="py-2 text-right">{i.total.toFixed(2)} {i.currency}</td>
                    <td className="py-2 flex gap-2">
                      {i.pdf_file_id ? (
                        <a className="btn btn-primary" href={`${apiBaseUrl()}/api/v1/files/${i.pdf_file_id}/download`}>
                          {t("pdf")}
                        </a>
                      ) : null}
                      <button
                        className="btn btn-ghost"
                        type="button"
                        onClick={() => void api(`/api/v1/invoices/${i.id}/issue`, { method: "POST" }).then(load).catch(() => setError(t("issueFailed")))}
                        disabled={i.status === "PAID"}
                      >
                        {t("issue")}
                      </button>
                      <button
                        className="btn btn-ghost"
                        type="button"
                        onClick={() =>
                          void api<InvoiceLine[]>(`/api/v1/invoices/${i.id}/lines`)
                            .then((d) => { setLines(d); setLinesForId(i.id); })
                            .catch(() => setError(t("loadLinesFailed")))
                        }
                      >
                        {t("lines")}
                      </button>
                      <button
                        className="btn btn-ghost"
                        type="button"
                        onClick={() => void api(`/api/v1/invoices/${i.id}/mark-paid`, { method: "POST" }).then(load).catch(() => setError(t("markPaidFailed")))}
                      >
                        {t("markPaid")}
                      </button>
                    </td>
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



