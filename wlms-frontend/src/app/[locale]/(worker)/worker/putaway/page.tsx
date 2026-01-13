"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";
import { ScannerInput } from "@/components/scanner/ScannerInput";
import { SupervisorOverrideModal } from "@/components/worker/SupervisorOverrideModal";

type Task = {
  client_id: string;
  warehouse_id: string;
  product_id: string;
  batch_id: string | null;
  from_location_id: string;
  on_hand_qty: number;
  suggested_to_location_id?: string | null;
  suggested_to_location_code?: string | null;
};

export default function WorkerPutawayPage() {
  useRequireAuth();
  const t = useTranslations("pages.workerPutaway");
  const c = useTranslations("common");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [selectedIndex, setSelectedIndex] = useState(0);
  const selected = tasks[selectedIndex];

  const [productId, setProductId] = useState("");
  const [fromLocationId, setFromLocationId] = useState("");
  const [toLocationId, setToLocationId] = useState("");
  const [qty, setQty] = useState(1);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [overrideGranted, setOverrideGranted] = useState(false);

  async function load() {
    const data = await api<Task[]>("/api/v1/putaway/tasks");
    setTasks(data);
  }

  useEffect(() => {
    void load().catch(() => setError(t("loadFailed")));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setProductId(selected.product_id);
    setFromLocationId(selected.from_location_id);
    setToLocationId(selected.suggested_to_location_id ?? "");
    setQty(1);
    setOverrideGranted(false);
  }, [selectedIndex, selected?.product_id, selected?.from_location_id]);

  return (
    <AppShell nav="worker" title={t("title")}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div className="text-xs uppercase tracking-widest text-muted">{t("selectTask")}</div>
            <button className="btn btn-ghost" type="button" onClick={() => void load().catch(() => setError(t("reloadFailed")))}>
              {c("refresh")}
            </button>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <select
              className="input"
              value={String(selectedIndex)}
              onChange={(e) => setSelectedIndex(Number(e.target.value))}
              disabled={tasks.length === 0}
            >
              {tasks.map((t, idx) => (
                <option key={`${t.product_id}-${t.from_location_id}-${idx}`} value={idx}>
                  {idx + 1}. {t.product_id.slice(0, 8)}… @ {t.from_location_id.slice(0, 8)}… ({t.on_hand_qty})
                </option>
              ))}
            </select>
            <div className="text-sm text-muted">
              {t("expectedHint")}
            </div>
          </div>
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("confirmMove")}</div>
          <form
            className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              if (!selected) {
                setError(t("noTask"));
                return;
              }
              if (!overrideGranted) {
                if (productId.trim() !== selected.product_id.trim()) {
                  setError(t("wrongProduct"));
                  setOverrideOpen(true);
                  return;
                }
                if (fromLocationId.trim() !== selected.from_location_id.trim()) {
                  setError(t("wrongFromLocation"));
                  setOverrideOpen(true);
                  return;
                }
              }
              if (!toLocationId.trim()) {
                setError(t("destinationRequired"));
                return;
              }
              try {
                await api("/api/v1/putaway/confirm", {
                  method: "POST",
                  body: {
                    product_id: selected.product_id,
                    batch_id: selected.batch_id,
                    qty,
                    from_location_id: selected.from_location_id,
                    to_location_id: toLocationId
                  }
                });
                await load();
              } catch {
                setError(t("confirmFailed"));
              }
            }}
          >
            <ScannerInput
              label={t("productScan")}
              value={productId}
              onChange={setProductId}
              expectedValue={selected?.product_id}
              placeholder={t("uuid")}
            />
            <ScannerInput
              label={t("fromLocationScan")}
              value={fromLocationId}
              onChange={setFromLocationId}
              expectedValue={selected?.from_location_id}
              placeholder={t("uuid")}
            />
            <ScannerInput
              label={t("toLocationScan")}
              value={toLocationId}
              onChange={setToLocationId}
              placeholder={selected?.suggested_to_location_code ? `${t("uuid")} (${selected.suggested_to_location_code})` : t("uuid")}
            />
            <input className="input" type="number" min={1} value={qty} onChange={(e) => setQty(Number(e.target.value))} />
            <div className="flex items-center gap-3 md:col-span-2">
              <button className="btn btn-primary" type="submit">{t("confirmPutaway")}</button>
              <button className="btn btn-ghost" type="button" onClick={() => setOverrideOpen(true)}>
                {t("supervisorOverride")}
              </button>
              {overrideGranted ? <div className="text-xs uppercase tracking-widest text-muted">{t("overrideGranted")}</div> : null}
            </div>
          </form>
          {selected ? (
            <div className="mt-3 text-xs text-muted">
              {t("taskQtyAvailable")}: {selected.on_hand_qty} (batch: {selected.batch_id ?? "—"})
            </div>
          ) : null}
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>
      </div>

      <SupervisorOverrideModal
        open={overrideOpen}
        onClose={() => setOverrideOpen(false)}
        onSuccess={() => {
          setOverrideGranted(true);
          if (selected) {
            setProductId(selected.product_id);
            setFromLocationId(selected.from_location_id);
          }
        }}
      />
    </AppShell>
  );
}


