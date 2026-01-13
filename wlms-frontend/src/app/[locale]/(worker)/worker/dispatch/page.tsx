"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";
import { ScannerInput } from "@/components/scanner/ScannerInput";

export default function WorkerDispatchPage() {
  useRequireAuth();
  const t = useTranslations("pages.workerDispatch");
  const [outboundId, setOutboundId] = useState("");
  const [packingLocationId, setPackingLocationId] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <AppShell nav="worker" title={t("title")}>
      <div className="card p-5">
        <div className="text-xs uppercase tracking-widest text-muted">{t("confirmDispatch")}</div>
        <form
          className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2"
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
          <ScannerInput label={t("outboundId")} value={outboundId} onChange={setOutboundId} placeholder={t("uuid")} />
          <ScannerInput label={t("packingLocationId")} value={packingLocationId} onChange={setPackingLocationId} placeholder={t("uuid")} />
          <button className="btn btn-primary md:col-span-2" type="submit">{t("confirmDispatch")}</button>
        </form>
        {error ? <div className="mt-3 text-sm">{error}</div> : null}
      </div>
    </AppShell>
  );
}


