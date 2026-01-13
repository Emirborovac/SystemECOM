"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

export default function AdminDispatchPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.adminDispatch");
  const [outboundId, setOutboundId] = useState("");
  const [packingLocationId, setPackingLocationId] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <AppShell nav="admin" title={`${nav("admin")} / ${nav("dispatch")}`}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("pack")}</div>
          <form
            className="mt-3 flex flex-col gap-3 sm:flex-row"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                await api(`/api/v1/packing/${outboundId}/confirm`, { method: "POST", body: {} });
              } catch {
                setError(t("packingFailed"));
              }
            }}
          >
            <input className="input flex-1" placeholder={t("outboundId")} value={outboundId} onChange={(e) => setOutboundId(e.target.value)} />
            <button className="btn btn-primary" type="submit">{t("confirmPacking")}</button>
          </form>
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("dispatch")}</div>
          <form
            className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                await api(`/api/v1/dispatch/${outboundId}/confirm`, {
                  method: "POST",
                  body: { packing_location_id: packingLocationId }
                });
              } catch {
                setError(t("dispatchFailed"));
              }
            }}
          >
            <input className="input" placeholder={t("outboundId")} value={outboundId} onChange={(e) => setOutboundId(e.target.value)} />
            <input className="input" placeholder={t("packingLocationId")} value={packingLocationId} onChange={(e) => setPackingLocationId(e.target.value)} />
            <button className="btn btn-primary" type="submit">{t("confirmDispatch")}</button>
          </form>
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>
      </div>
    </AppShell>
  );
}



