"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/layout/AppShell";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { api } from "@/lib/api/http";
import { useToast } from "@/components/feedback/ToastProvider";

type Balance = {
  id: string;
  tenant_id: number;
  client_id: string;
  warehouse_id: string;
  product_id: string;
  batch_id: string | null;
  location_id: string;
  on_hand_qty: number;
  reserved_qty: number;
  available_qty: number;
};

export default function ClientInventoryPage() {
  useRequireAuth();
  const nav = useTranslations("nav");
  const t = useTranslations("pages.clientInventory");
  const [items, setItems] = useState<Balance[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { push } = useToast();

  const [warehouseId, setWarehouseId] = useState("");
  const [productCategory, setProductCategory] = useState("");
  const [expiryAfter, setExpiryAfter] = useState("");
  const [expiryBefore, setExpiryBefore] = useState("");

  const [page, setPage] = useState(1);
  const pageSize = 50;

  const [detailsProductId, setDetailsProductId] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setError(null);
      try {
        const qs = new URLSearchParams();
        if (warehouseId) qs.set("warehouse_id", warehouseId);
        if (productCategory) qs.set("product_category", productCategory);
        if (expiryAfter) qs.set("expiry_after", expiryAfter);
        if (expiryBefore) qs.set("expiry_before", expiryBefore);
        const data = await api<Balance[]>(`/api/v1/inventory/balances${qs.toString() ? `?${qs.toString()}` : ""}`);
        setItems(data);
        setPage(1);
      } catch {
        setError(t("loadFailed"));
        push({ title: t("loadFailed"), variant: "error" });
      }
    })();
  }, [warehouseId, productCategory, expiryAfter, expiryBefore]);

  const grouped = groupByProduct(items);
  const pageCount = Math.max(1, Math.ceil(grouped.length / pageSize));
  const current = grouped.slice((page - 1) * pageSize, page * pageSize);

  return (
    <AppShell nav="client" title={`${nav("client")} / ${nav("inventory")}`}>
      <div className="card p-5">
        <div className="text-xs uppercase tracking-widest text-muted">
          {t("title")}
        </div>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-4">
          <input className="input" placeholder={t("warehouseId")} value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)} />
          <input className="input" placeholder={t("productCategory")} value={productCategory} onChange={(e) => setProductCategory(e.target.value)} />
          <input className="input" placeholder={t("expiryAfter")} value={expiryAfter} onChange={(e) => setExpiryAfter(e.target.value)} />
          <input className="input" placeholder={t("expiryBefore")} value={expiryBefore} onChange={(e) => setExpiryBefore(e.target.value)} />
        </div>
        {error ? <div className="mt-3 text-sm">{error}</div> : null}
        <div className="mt-3 overflow-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="py-2 text-left">{t("product")}</th>
                <th className="py-2 text-left">{t("locations")}</th>
                <th className="py-2 text-right">{t("onHand")}</th>
                <th className="py-2 text-right">{t("reserved")}</th>
                <th className="py-2 text-right">{t("available")}</th>
              </tr>
            </thead>
            <tbody>
              {current.map((g) => (
                <tr
                  key={g.product_id}
                  className="border-b border-border cursor-pointer hover:bg-[color:var(--muted)]"
                  onClick={() => setDetailsProductId(g.product_id)}
                >
                  <td className="py-2 font-mono text-xs">{g.product_id}</td>
                  <td className="py-2">{g.locations_count}</td>
                  <td className="py-2 text-right">{g.on_hand_qty}</td>
                  <td className="py-2 text-right">{g.reserved_qty}</td>
                  <td className="py-2 text-right">{g.available_qty}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex items-center justify-between text-sm">
          <div className="text-muted">
            {t("results")}: {grouped.length}
          </div>
          <div className="flex items-center gap-2">
            <button className="btn btn-ghost" type="button" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
              {t("prev")}
            </button>
            <div className="text-muted">
              {page}/{pageCount}
            </div>
            <button
              className="btn btn-ghost"
              type="button"
              disabled={page >= pageCount}
              onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
            >
              {t("next")}
            </button>
          </div>
        </div>
      </div>

      {detailsProductId ? (
        <div className="card mt-4 p-5">
          <div className="flex items-center justify-between">
            <div className="text-xs uppercase tracking-widest text-muted">{t("perLocationBreakdown")}</div>
            <button className="btn btn-ghost" type="button" onClick={() => setDetailsProductId(null)}>
              {t("close")}
            </button>
          </div>
          <div className="mt-3 text-xs text-muted font-mono">{detailsProductId}</div>
          <div className="mt-3 overflow-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2 text-left">{t("location")}</th>
                  <th className="py-2 text-right">{t("onHand")}</th>
                  <th className="py-2 text-right">{t("reserved")}</th>
                  <th className="py-2 text-right">{t("available")}</th>
                </tr>
              </thead>
              <tbody>
                {items
                  .filter((x) => x.product_id === detailsProductId)
                  .map((b) => (
                    <tr key={b.id} className="border-b border-border">
                      <td className="py-2 font-mono text-xs">{b.location_id}</td>
                      <td className="py-2 text-right">{b.on_hand_qty}</td>
                      <td className="py-2 text-right">{b.reserved_qty}</td>
                      <td className="py-2 text-right">{b.available_qty}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}

function groupByProduct(items: Balance[]) {
  const m = new Map<
    string,
    { product_id: string; locations_count: number; on_hand_qty: number; reserved_qty: number; available_qty: number }
  >();
  for (const b of items) {
    const cur = m.get(b.product_id) || { product_id: b.product_id, locations_count: 0, on_hand_qty: 0, reserved_qty: 0, available_qty: 0 };
    cur.locations_count += 1;
    cur.on_hand_qty += b.on_hand_qty;
    cur.reserved_qty += b.reserved_qty;
    cur.available_qty += b.available_qty;
    m.set(b.product_id, cur);
  }
  return Array.from(m.values()).sort((a, b) => (a.product_id < b.product_id ? -1 : 1));
}


