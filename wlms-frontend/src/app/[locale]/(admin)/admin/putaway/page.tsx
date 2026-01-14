"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";

type Task = {
  client_id: string;
  warehouse_id: string;
  product_id: string;
  batch_id: string | null;
  from_location_id: string;
  on_hand_qty: number;
};

export default function AdminPutawayPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.adminPutaway");
  const [items, setItems] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [toLocationId, setToLocationId] = useState("");
  const [qty, setQty] = useState(1);

  async function load() {
    const data = await api<Task[]>("/api/v1/putaway/tasks");
    setItems(data);
  }

  useEffect(() => {
    void load().catch(() => setError(t("loadFailed")));
  }, []);

  return (
    <AppShell nav="admin" title={`${nav("admin")} / ${nav("putaway")}`}>
      <div className="grid gap-4">
        <div className="card p-5">
          <div className="text-xs uppercase tracking-widest text-muted">
            {t("confirmTitle")}
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <input
              className="input"
              placeholder={t("toLocationStorage")}
              value={toLocationId}
              onChange={(e) => setToLocationId(e.target.value)}
            />
            <input
              className="input"
              type="number"
              min={1}
              value={qty}
              onChange={(e) => setQty(Number(e.target.value))}
            />
          </div>
          <div className="mt-3 text-sm text-muted">
            {t("hint")}
          </div>
          {error ? <div className="mt-3 text-sm">{error}</div> : null}
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div className="text-xs uppercase tracking-widest text-muted">
              {t("tasksTitle")}
            </div>
            <button
              className="btn btn-ghost"
              type="button"
              onClick={() => void load().catch(() => setError(t("loadFailed")))}
            >
              Refresh
            </button>
          </div>
          <div className="mt-3 overflow-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2 text-left">{t("qty")}</th>
                  <th className="py-2 text-left">{t("fromLocation")}</th>
                  <th className="py-2 text-left">{t("product")}</th>
                  <th className="py-2 text-left">{t("batch")}</th>
                  <th className="py-2 text-left"></th>
                </tr>
              </thead>
              <tbody>
                {items.map((task, idx) => (
                  <tr key={`${task.from_location_id}-${task.product_id}-${idx}`} className="border-b border-border">
                    <td className="py-2">{task.on_hand_qty}</td>
                    <td className="py-2 font-mono text-xs">{task.from_location_id}</td>
                    <td className="py-2 font-mono text-xs">{task.product_id}</td>
                    <td className="py-2 font-mono text-xs">{task.batch_id ?? "—"}</td>
                    <td className="py-2">
                      <button
                        className="btn btn-primary"
                        type="button"
                        onClick={async () => {
                          setError(null);
                          if (!toLocationId) {
                            setError(t("enterDestination"));
                            return;
                          }
                          try {
                            await api("/api/v1/putaway/confirm", {
                              method: "POST",
                              body: {
                                product_id: task.product_id,
                                batch_id: task.batch_id,
                                qty,
                                from_location_id: task.from_location_id,
                                to_location_id: toLocationId
                              }
                            });
                            await load();
                          } catch {
                            setError(t("moveFailed"));
                          }
                        }}
                      >
                        {t("move")}
                      </button>
                    </td>
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


