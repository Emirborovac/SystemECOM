"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";
import { ScannerInput } from "@/components/scanner/ScannerInput";

export default function WorkerReturnsPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.workerReturns");
  const [returnId, setReturnId] = useState("");
  const [productId, setProductId] = useState("");
  const [qty, setQty] = useState(1);
  const [disposition, setDisposition] = useState("RESTOCK");
  const [toLocationId, setToLocationId] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <AppShell nav="worker" title={`${nav("worker")} / ${nav("returns")}`}>
      <div className="card p-5">
        <div className="text-xs uppercase tracking-widest text-muted">{t("scanReturnLine")}</div>
        <form
          className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            try {
              await api(`/api/v1/returns/${returnId}/scan-line`, {
                method: "POST",
                body: {
                  product_id: productId,
                  qty,
                  disposition,
                  to_location_id: toLocationId || null
                }
              });
            } catch {
              setError(t("scanFailed"));
            }
          }}
        >
          <ScannerInput label={t("returnId")} value={returnId} onChange={setReturnId} placeholder={t("uuid")} />
          <ScannerInput label={t("productId")} value={productId} onChange={setProductId} placeholder={t("uuid")} />
          <input className="input" type="number" min={1} value={qty} onChange={(e) => setQty(Number(e.target.value))} />
          <select className="input" value={disposition} onChange={(e) => setDisposition(e.target.value)}>
            <option value="RESTOCK">{t("restock")}</option>
            <option value="QUARANTINE">{t("quarantine")}</option>
            <option value="SCRAP">{t("scrap")}</option>
          </select>
          <ScannerInput label={t("toLocationId")} value={toLocationId} onChange={setToLocationId} placeholder={t("uuid")} />
          <button className="btn btn-primary md:col-span-2" type="submit">{t("addLine")}</button>
        </form>
        <div className="mt-3 flex gap-3">
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => void api(`/api/v1/returns/${returnId}/complete`, { method: "POST" }).catch(() => setError(t("completeFailed")))}
          >
            {t("completeReturn")}
          </button>
        </div>
        {error ? <div className="mt-3 text-sm">{error}</div> : null}
      </div>
    </AppShell>
  );
}


