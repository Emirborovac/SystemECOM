"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";
import { ScannerInput } from "@/components/scanner/ScannerInput";

type Inbound = { id: string; reference_number: string; status: string; client_id: string; warehouse_id: string };

export default function WorkerReceivePage() {
  useRequireAuth();
  const t = useTranslations("pages.workerReceive");
  const c = useTranslations("common");
  const [items, setItems] = useState<Inbound[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [inboundId, setInboundId] = useState("");
  const [barcode, setBarcode] = useState("");
  const [qty, setQty] = useState(1);
  const [stagingLocationId, setStagingLocationId] = useState("");

  async function load() {
    const data = await api<Inbound[]>("/api/v1/inbound");
    setItems(data);
  }

  useEffect(() => {
    void load().catch(() => setError(t("loadFailed")));
  }, []);

  return (
    <AppShell nav="worker" title={t("title")}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("startReceiving")}</div>
          <form
            className="mt-3 flex flex-col gap-3 sm:flex-row"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                await api(`/api/v1/inbound/${inboundId}/start-receiving`, { method: "POST" });
                await load();
              } catch {
                setError(t("startFailed"));
              }
            }}
          >
            <input className="input flex-1" placeholder={t("inboundId")} value={inboundId} onChange={(e) => setInboundId(e.target.value)} />
            <button className="btn btn-primary" type="submit">{t("start")}</button>
          </form>
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("scanIntoStaging")}</div>
          <form
            className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                await api(`/api/v1/inbound/${inboundId}/scan-line`, {
                  method: "POST",
                  body: {
                    barcode,
                    qty,
                    batch_number: null,
                    expiry_date: null,
                    location_staging_id: stagingLocationId
                  }
                });
                await load();
              } catch {
                setError(t("scanFailed"));
              }
            }}
          >
            <ScannerInput label={t("productBarcode")} value={barcode} onChange={setBarcode} placeholder={t("scanEnterBarcode")} />
            <ScannerInput
              label={t("stagingLocation")}
              value={stagingLocationId}
              onChange={setStagingLocationId}
              placeholder={t("uuid")}
            />
            <input className="input" type="number" min={1} value={qty} onChange={(e) => setQty(Number(e.target.value))} />
            <button className="btn btn-primary" type="submit">{t("confirmScan")}</button>
          </form>
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div className="text-xs uppercase tracking-widest text-muted">{t("inboundList")}</div>
            <button className="btn btn-ghost" type="button" onClick={() => void load().catch(() => setError(t("reloadFailed")))}>
              {c("refresh")}
            </button>
          </div>
          <div className="mt-3 overflow-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2 text-left">{t("ref")}</th>
                  <th className="py-2 text-left">{t("status")}</th>
                  <th className="py-2 text-left">{t("warehouse")}</th>
                  <th className="py-2 text-left">{t("id")}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((i) => (
                  <tr key={i.id} className="border-b border-border">
                    <td className="py-2">{i.reference_number}</td>
                    <td className="py-2">{i.status}</td>
                    <td className="py-2 font-mono text-xs">{i.warehouse_id}</td>
                    <td className="py-2 font-mono text-xs">{i.id}</td>
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


