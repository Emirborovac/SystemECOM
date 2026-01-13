"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

type Client = { id: string; name: string; billing_currency: string; preferred_language: string };
type PriceList = { id: string; client_id: string; effective_from: string; rules_json: Record<string, unknown> };

export default function AdminSettingsPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.adminSettingsPage");
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const [effectiveFrom, setEffectiveFrom] = useState(new Date().toISOString().slice(0, 10));
  const [rulesJsonText, setRulesJsonText] = useState(
    JSON.stringify(
      { currency: "EUR", storage: { type: "PALLET_POSITION_DAY", unit_price: 8.5 }, inbound: { per_line: 1.0 }, dispatch: { per_order: 3.5 } },
      null,
      2
    )
  );
  const [currentPriceList, setCurrentPriceList] = useState<PriceList | null>(null);

  async function loadClients() {
    const data = await api<Client[]>("/api/v1/clients");
    setClients(data);
    if (!clientId && data[0]?.id) setClientId(data[0].id);
  }

  async function loadPriceList(cid: string) {
    setCurrentPriceList(null);
    try {
      const pl = await api<PriceList>(`/api/v1/clients/${cid}/price-list`);
      setCurrentPriceList(pl);
      setEffectiveFrom(pl.effective_from);
      setRulesJsonText(JSON.stringify(pl.rules_json, null, 2));
    } catch {
      // No price list yet is acceptable; keep editor defaults
    }
  }

  useEffect(() => {
    void loadClients().catch(() => setError(t("loadClientsFailed")));
  }, []);

  useEffect(() => {
    if (!clientId) return;
    void loadPriceList(clientId).catch(() => {});
  }, [clientId]);

  return (
    <AppShell nav="admin" title={`${nav("admin")} / ${nav("settings")}`}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("selectClient")}</div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <select className="input" value={clientId} onChange={(e) => setClientId(e.target.value)}>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.preferred_language}/{c.billing_currency})
                </option>
              ))}
            </select>
            <button className="btn btn-ghost" type="button" onClick={() => void loadPriceList(clientId).catch(() => setError(t("loadPriceListFailed")))}>
              {t("refreshPriceList")}
            </button>
          </div>
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("priceListTitle")}</div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <input className="input" placeholder={t("effectiveFrom")} value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
            <div className="text-sm text-muted">{t("current")}: {currentPriceList ? currentPriceList.id : "—"}</div>
          </div>
          <textarea className="input mt-3 h-64 font-mono text-xs" value={rulesJsonText} onChange={(e) => setRulesJsonText(e.target.value)} />
          <div className="mt-3 flex gap-3">
            <button
              className="btn btn-primary"
              type="button"
              onClick={async () => {
                setError(null);
                setOk(null);
                try {
                  const rules = JSON.parse(rulesJsonText) as Record<string, unknown>;
                  await api<PriceList>(`/api/v1/clients/${clientId}/price-list`, {
                    method: "PUT",
                    body: { effective_from: effectiveFrom, rules_json: rules }
                  });
                  setOk(t("saved"));
                  await loadPriceList(clientId);
                } catch (e: any) {
                  setError(e?.message || t("saveFailed"));
                }
              }}
            >
              {t("savePriceList")}
            </button>
            <button className="btn btn-ghost" type="button" onClick={() => setRulesJsonText(JSON.stringify(currentPriceList?.rules_json ?? {}, null, 2))}>
              {t("resetEditor")}
            </button>
          </div>
          {ok ? <div className="mt-3 text-sm">{ok}</div> : null}
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>
      </div>
    </AppShell>
  );
}


