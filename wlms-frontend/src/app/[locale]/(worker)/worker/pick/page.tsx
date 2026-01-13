"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";
import { ScannerInput } from "@/components/scanner/ScannerInput";
import { SupervisorOverrideModal } from "@/components/worker/SupervisorOverrideModal";

type Task = { id: string; outbound_id: string; status: string };
type Line = { id: number; product_id: string; batch_id: string | null; from_location_id: string; qty_to_pick: number; qty_picked: number };

export default function WorkerPickPage() {
  useRequireAuth();
  const t = useTranslations("pages.workerPick");
  const c = useTranslations("common");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [lines, setLines] = useState<Line[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [taskId, setTaskId] = useState("");
  const [lineId, setLineId] = useState<number | null>(null);

  const selectedLine = useMemo(() => lines.find((l) => l.id === lineId) ?? null, [lines, lineId]);

  const [scannedProductId, setScannedProductId] = useState("");
  const [scannedFromLocationId, setScannedFromLocationId] = useState("");
  const [toLocationId, setToLocationId] = useState("");
  const [qty, setQty] = useState(1);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [overrideGranted, setOverrideGranted] = useState(false);

  async function loadTasks() {
    const data = await api<Task[]>("/api/v1/picking/tasks");
    setTasks(data);
  }

  async function loadLines(tid: string) {
    const data = await api<Line[]>(`/api/v1/picking/tasks/${tid}/lines`);
    setLines(data);
    setLineId(data[0]?.id ?? null);
  }

  useEffect(() => {
    void loadTasks().catch(() => setError(t("loadTasksFailed")));
  }, []);

  useEffect(() => {
    if (!selectedLine) return;
    setScannedProductId(selectedLine.product_id);
    setScannedFromLocationId(selectedLine.from_location_id);
    setQty(1);
    setOverrideGranted(false);
  }, [selectedLine?.id]);

  return (
    <AppShell nav="worker" title={t("title")}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("selectTask")}</div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
            <ScannerInput label={t("taskId")} value={taskId} onChange={setTaskId} placeholder={t("uuid")} />
            <button
              className="btn btn-primary"
              type="button"
              onClick={() => void api(`/api/v1/picking/tasks/${taskId}/start`, { method: "POST" }).then(loadTasks).catch(() => setError(t("startFailed")))}
            >
              {t("start")}
            </button>
            <button
              className="btn btn-ghost"
              type="button"
              onClick={() => void loadLines(taskId).catch(() => setError(t("loadLinesFailed")))}
            >
              {t("loadLines")}
            </button>
          </div>
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("pickLine")}</div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <select
              className="input"
              value={lineId ?? ""}
              onChange={(e) => setLineId(Number(e.target.value))}
              disabled={lines.length === 0}
            >
              {lines.map((l) => (
                <option key={l.id} value={l.id}>
                  {t("lineLabel")} {l.id}: {l.product_id.slice(0, 8)}… @ {l.from_location_id.slice(0, 8)}… ({l.qty_picked}/{l.qty_to_pick})
                </option>
              ))}
            </select>
            <div className="text-sm text-muted">{t("wrongScanHint")}</div>
          </div>

          <form
            className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              if (!selectedLine) {
                setError(t("noLineSelected"));
                return;
              }
              if (!overrideGranted) {
                if (scannedProductId.trim() !== selectedLine.product_id.trim()) {
                  setError(t("wrongProduct"));
                  setOverrideOpen(true);
                  return;
                }
                if (scannedFromLocationId.trim() !== selectedLine.from_location_id.trim()) {
                  setError(t("wrongLocation"));
                  setOverrideOpen(true);
                  return;
                }
              }
              try {
                await api(`/api/v1/picking/tasks/${taskId}/scan`, {
                  method: "POST",
                  body: {
                    product_id: selectedLine.product_id,
                    batch_id: selectedLine.batch_id,
                    qty,
                    from_location_id: selectedLine.from_location_id,
                    to_location_id: toLocationId
                  }
                });
                await loadLines(taskId);
              } catch {
                setError(t("scanFailed"));
              }
            }}
          >
            <ScannerInput
              label={t("productScan")}
              value={scannedProductId}
              onChange={setScannedProductId}
              expectedValue={selectedLine?.product_id ?? undefined}
              placeholder={t("uuid")}
            />
            <ScannerInput
              label={t("fromLocationScan")}
              value={scannedFromLocationId}
              onChange={setScannedFromLocationId}
              expectedValue={selectedLine?.from_location_id ?? undefined}
              placeholder={t("uuid")}
            />
            <ScannerInput label={t("toPackingLocationScan")} value={toLocationId} onChange={setToLocationId} placeholder={t("uuid")} />
            <input className="input" type="number" min={1} value={qty} onChange={(e) => setQty(Number(e.target.value))} />
            <div className="flex items-center gap-3 md:col-span-2">
              <button className="btn btn-primary" type="submit">{t("confirmPick")}</button>
              <button className="btn btn-ghost" type="button" onClick={() => setOverrideOpen(true)}>
                {t("supervisorOverride")}
              </button>
              {overrideGranted ? <div className="text-xs uppercase tracking-widest text-muted">{t("overrideGranted")}</div> : null}
            </div>
          </form>

          <div className="mt-3 flex gap-3">
            <button
              className="btn btn-ghost"
              type="button"
              onClick={() => void api(`/api/v1/picking/tasks/${taskId}/complete`, { method: "POST" }).then(loadTasks).catch(() => setError(t("completeFailed")))}
            >
              {t("completeTask")}
            </button>
          </div>
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("tasks")}</div>
          <div className="mt-3 overflow-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2 text-left">{t("status")}</th>
                  <th className="py-2 text-left">{t("outbound")}</th>
                  <th className="py-2 text-left">{t("taskId")}</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => (
                  <tr key={t.id} className="border-b border-border">
                    <td className="py-2">{t.status}</td>
                    <td className="py-2 font-mono text-xs">{t.outbound_id}</td>
                    <td className="py-2 font-mono text-xs">{t.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <SupervisorOverrideModal
        open={overrideOpen}
        onClose={() => setOverrideOpen(false)}
        onSuccess={() => {
          setOverrideGranted(true);
          if (selectedLine) {
            setScannedProductId(selectedLine.product_id);
            setScannedFromLocationId(selectedLine.from_location_id);
          }
        }}
      />
    </AppShell>
  );
}


