"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";
import { ScannerInput } from "@/components/scanner/ScannerInput";

export default function WorkerDiscrepancyPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.workerDiscrepancy");
  const [productId, setProductId] = useState("");
  const [batchId, setBatchId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [countedQty, setCountedQty] = useState(0);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  return (
    <AppShell nav="worker" title={`${nav("worker")} / ${nav("discrepancies")}`}>
      <div className="card p-5">
        <div className="text-xs uppercase tracking-widest text-muted">{t("createDiscrepancy")}</div>
        <form
          className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            setDone(false);
            try {
              await api("/api/v1/discrepancies", {
                method: "POST",
                body: {
                  product_id: productId,
                  batch_id: batchId || null,
                  location_id: locationId,
                  counted_qty: countedQty,
                  reason
                }
              });
              setDone(true);
            } catch {
              setError(t("createFailed"));
            }
          }}
        >
          <ScannerInput label={t("locationId")} value={locationId} onChange={setLocationId} placeholder={t("uuid")} />
          <ScannerInput label={t("productId")} value={productId} onChange={setProductId} placeholder={t("uuid")} />
          <ScannerInput label={t("batchIdOptional")} value={batchId} onChange={setBatchId} placeholder={t("uuid")} />
          <input className="input" type="number" min={0} value={countedQty} onChange={(e) => setCountedQty(Number(e.target.value))} />
          <input className="input md:col-span-2" placeholder={t("reason")} value={reason} onChange={(e) => setReason(e.target.value)} />
          <button className="btn btn-primary md:col-span-2" type="submit">{t("submit")}</button>
        </form>
        {done ? <div className="mt-3 text-sm">{t("submitted")}</div> : null}
        {error ? <div className="mt-3 text-sm">{error}</div> : null}
      </div>
    </AppShell>
  );
}


