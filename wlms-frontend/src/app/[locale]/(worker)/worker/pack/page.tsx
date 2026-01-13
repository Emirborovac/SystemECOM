"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";
import { ScannerInput } from "@/components/scanner/ScannerInput";

export default function WorkerPackPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.workerPack");
  const [outboundId, setOutboundId] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <AppShell nav="worker" title={t("title")}>
      <div className="card p-5">
        <div className="text-xs uppercase tracking-widest text-muted">{t("confirmPacking")}</div>
        <form
          className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2"
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
          <ScannerInput label={t("outboundId")} value={outboundId} onChange={setOutboundId} placeholder={t("uuid")} />
          <button className="btn btn-primary" type="submit">{t("confirmPack")}</button>
        </form>
        {error ? <div className="mt-3 text-sm">{error}</div> : null}
      </div>
    </AppShell>
  );
}


