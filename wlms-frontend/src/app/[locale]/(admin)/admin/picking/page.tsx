"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

type Task = { id: string; outbound_id: string; status: string };
type TaskLine = { id: number; product_id: string; batch_id: string | null; from_location_id: string; qty_to_pick: number; qty_picked: number };
type Outbound = { id: string; warehouse_id: string };
type Zone = { id: number; warehouse_id: string; zone_type: string };
type Location = { id: string; warehouse_id: string; zone_id: number; code: string; barcode_value: string };

export default function AdminPickingPage() {
  useRequireAuth();
  const t = useTranslations("pages.adminPicking");
  const c = useTranslations("common");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [taskLines, setTaskLines] = useState<TaskLine[]>([]);
  const [packingLocations, setPackingLocations] = useState<Location[]>([]);

  const [taskId, setTaskId] = useState("");
  const [productId, setProductId] = useState("");
  const [fromLocationId, setFromLocationId] = useState("");
  const [toLocationId, setToLocationId] = useState("");
  const [qty, setQty] = useState(1);

  async function load() {
    const data = await api<Task[]>("/api/v1/picking/tasks");
    setTasks(data);
    if (!taskId && data[0]?.id) setTaskId(data[0].id);
  }

  async function loadLinesAndPacking(tid: string) {
    if (!tid) return;
    const lines = await api<TaskLine[]>(`/api/v1/picking/tasks/${tid}/lines`);
    setTaskLines(lines);

    // derive warehouse from outbound, then filter PACKING locations
    const task = tasks.find((t) => t.id === tid);
    const outboundId = task?.outbound_id;
    if (!outboundId) return;
    const outbound = await api<Outbound>(`/api/v1/outbound/${outboundId}`);
    const [zones, locs] = await Promise.all([
      api<Zone[]>(`/api/v1/warehouses/${outbound.warehouse_id}/zones`),
      api<Location[]>(`/api/v1/warehouses/${outbound.warehouse_id}/locations`)
    ]);
    const zoneTypeById = new Map<number, string>(zones.map((z) => [z.id, z.zone_type]));
    const packing = locs.filter((l) => zoneTypeById.get(l.zone_id) === "PACKING");
    setPackingLocations(packing);
    if (!toLocationId && packing[0]?.id) setToLocationId(packing[0].id);
  }

  useEffect(() => {
    void load().catch(() => setError(t("reloadFailed")));
  }, []);

  useEffect(() => {
    void loadLinesAndPacking(taskId).catch(() => {});
  }, [taskId]);

  return (
    <AppShell nav="admin" title={t("title")}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("startTask")}</div>
          <form
            className="mt-3 flex flex-col gap-3 sm:flex-row"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                await api(`/api/v1/picking/tasks/${taskId}/start`, { method: "POST" });
                await load();
              } catch {
                setError(t("startFailed"));
              }
            }}
          >
            <select className="input flex-1" value={taskId} onChange={(e) => setTaskId(e.target.value)}>
              <option value="">{t("task")}</option>
              {tasks.map((t0) => (
                <option key={t0.id} value={t0.id}>
                  {t0.status} / {t0.outbound_id}
                </option>
              ))}
            </select>
            <button className="btn btn-primary" type="submit">{t("start")}</button>
          </form>
        </div>

        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">{t("scanPick")}</div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <select
              className="input"
              value={fromLocationId && productId ? `${productId}|${fromLocationId}` : ""}
              onChange={(e) => {
                const v = e.target.value;
                if (!v) return;
                const [pid, from] = v.split("|");
                const line = taskLines.find((l) => l.product_id === pid && l.from_location_id === from);
                setProductId(pid);
                setFromLocationId(from);
                if (line) setQty(Math.max(1, line.qty_to_pick - line.qty_picked));
              }}
            >
              <option value="">{t("pickLineAutofill")}</option>
              {taskLines.map((l) => (
                <option key={l.id} value={`${l.product_id}|${l.from_location_id}`}>
                  {l.product_id} @ {l.from_location_id} ({l.qty_picked}/{l.qty_to_pick})
                </option>
              ))}
            </select>
            <select className="input" value={toLocationId} onChange={(e) => setToLocationId(e.target.value)}>
              <option value="">{t("packingLocation")}</option>
              {packingLocations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.code} ({l.barcode_value})
                </option>
              ))}
            </select>
          </div>
          <form
            className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-5"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              try {
                await api(`/api/v1/picking/tasks/${taskId}/scan`, {
                  method: "POST",
                  body: {
                    product_id: productId,
                    qty,
                    from_location_id: fromLocationId,
                    to_location_id: toLocationId
                  }
                });
                await load();
                await loadLinesAndPacking(taskId);
              } catch {
                setError(t("scanFailed"));
              }
            }}
          >
            <input className="input" placeholder={t("taskId")} value={taskId} onChange={(e) => setTaskId(e.target.value)} />
            <input className="input" placeholder={t("productId")} value={productId} onChange={(e) => setProductId(e.target.value)} />
            <input className="input" placeholder={t("fromLocationId")} value={fromLocationId} onChange={(e) => setFromLocationId(e.target.value)} />
            <input className="input" placeholder={t("toPackingLocationId")} value={toLocationId} onChange={(e) => setToLocationId(e.target.value)} />
            <input className="input" type="number" min={1} value={qty} onChange={(e) => setQty(Number(e.target.value))} />
            <button className="btn btn-primary md:col-span-5" type="submit">{t("pick")}</button>
          </form>
          <div className="mt-3 flex gap-3">
            <button className="btn btn-ghost" type="button" onClick={() => void api(`/api/v1/picking/tasks/${taskId}/complete`, { method: "POST" }).then(load).catch(() => setError(t("completeFailed")))}>
              {t("completeTask")}
            </button>
            <button className="btn btn-ghost" type="button" onClick={() => void load().catch(() => setError(t("reloadFailed")))}>
              {c("refresh")}
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
    </AppShell>
  );
}



