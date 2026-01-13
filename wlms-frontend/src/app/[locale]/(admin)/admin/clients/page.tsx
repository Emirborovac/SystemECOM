"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

type Client = {
  id: string;
  tenant_id: number;
  name: string;
  address: string | null;
  tax_id: string | null;
  billing_currency: string;
  vat_rate: number;
  preferred_language: string;
};

export default function AdminClientsPage() {
  useRequireAuth();
  const t = useTranslations("pages.adminClients");
  const tt = useTranslations("pages.adminClientsTable");
  const c = useTranslations("common");
  const [items, setItems] = useState<Client[]>([]);
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("EUR");
  const [vatRate, setVatRate] = useState(0.17);
  const [preferredLanguage, setPreferredLanguage] = useState("en");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      const data = await api<Client[]>("/api/v1/clients");
      setItems(data);
    } catch (e) {
      setError(tt("loadFailed"));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <AppShell nav="admin" title={t("title")}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("create")}
          </div>
          <form
            className="mt-3 flex flex-col gap-3 sm:flex-row"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                await api<Client>("/api/v1/clients", {
                  method: "POST",
                  body: { name, billing_currency: currency, vat_rate: vatRate, preferred_language: preferredLanguage }
                });
                setName("");
                await load();
              } catch {
                setError(tt("createFailed"));
              }
            }}
          >
            <input
              className="input flex-1"
              placeholder={t("namePlaceholder")}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <select className="input" value={preferredLanguage} onChange={(e) => setPreferredLanguage(e.target.value)}>
              <option value="en">en</option>
              <option value="bs">bs</option>
              <option value="de">de</option>
            </select>
            <select className="input" value={currency} onChange={(e) => setCurrency(e.target.value)}>
              <option value="BAM">BAM</option>
              <option value="EUR">EUR</option>
            </select>
            <input className="input" type="number" step="0.01" min={0} max={1} value={vatRate} onChange={(e) => setVatRate(Number(e.target.value))} />
            <button className="btn btn-primary" type="submit">
              {c("create")}
            </button>
          </form>
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("list")}
          </div>
          <div className="mt-3 overflow-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2 text-left">{tt("name")}</th>
                  <th className="py-2 text-left">{tt("language")}</th>
                  <th className="py-2 text-left">{tt("currency")}</th>
                  <th className="py-2 text-left">{tt("vatRate")}</th>
                  <th className="py-2 text-left">{tt("id")}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((c) => (
                  <tr key={c.id} className="border-b border-border">
                    <td className="py-2">{c.name}</td>
                    <td className="py-2">{c.preferred_language}</td>
                    <td className="py-2">{c.billing_currency}</td>
                    <td className="py-2">{c.vat_rate}</td>
                    <td className="py-2 font-mono text-xs">{c.id}</td>
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


